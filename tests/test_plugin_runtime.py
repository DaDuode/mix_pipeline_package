# -*- coding: utf-8 -*-
import copy
import importlib.util
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT.parent / 'mix_studio_client/public/python/libs'))
for name in ['mix_api', 'mix_toolkit']:
    source = ROOT / name / 'src/__init__.py'
    spec = importlib.util.spec_from_file_location(name, str(source), submodule_search_locations=[str(source.parent)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)

from mix_toolkit import plugin_runtime as runtime
from mix_toolkit.utils import load_script


def snapshot():
    return {'code': 'mix_test', 'version_id': 42, 'version': '1.0.2',
            'has_attribute': True, 'has_script': True, 'has_config': True,
            'attrs': [{'code': 'api', 'content': 'def answer(): return 42'}],
            'scripts': [{'code': 'tool', 'content': 'COUNT=0\ndef main():\n global COUNT\n COUNT+=1\n return COUNT'}],
            'config': {'code': 'main', 'config_type': 'yaml', 'content': 'options: !include options'},
            'configs': [{'code': 'options', 'config_type': 'json', 'content': '{"enabled":true}'}]}


class PluginRuntimeTests(unittest.TestCase):
    def setUp(self):
        runtime._bundles.clear()
        runtime._modules.clear()

    def test_attribute_execution_config_include_and_explicit_script(self):
        result = runtime.initialize_plugin('mix_test', bundle=snapshot(), strict=True)
        self.assertEqual(result['api'].answer(), 42)
        self.assertEqual(result['PLUGIN_CONFIG']['options'], {'enabled': True})
        self.assertEqual(runtime.get_plugin_state('mix_test')['status'], 'ready')
        self.assertEqual(runtime._modules, {})
        self.assertEqual(runtime.run_plugin_script('mix_test', 'TOOL'), 1)
        self.assertEqual(runtime.run_plugin_script('mix_test', 'tool'), 2)

    def test_disabled_features_do_not_execute_stored_content(self):
        data = snapshot()
        data.update(has_attribute=False, has_script=False, has_config=False)
        data['attrs'][0]['content'] = 'raise RuntimeError("must not execute")'
        result = runtime.initialize_plugin('mix_test', bundle=data, strict=True)
        self.assertEqual(result['ATTRIBUTES'], {})
        self.assertEqual(result['SCRIPTS'], {})
        self.assertNotIn('PLUGIN_CONFIG', result)

    def test_failed_attribute_is_reported_without_script_body_or_secret(self):
        data = snapshot()
        data['attrs'][0]['content'] = 'raise ValueError("password-secret")'
        result = runtime.initialize_plugin('mix_test', bundle=data)
        state = result['INITIALIZATION_REPORT']
        self.assertEqual(state['status'], 'degraded')
        self.assertEqual(state['errors'][0]['error'], 'ValueError')
        self.assertNotIn('password-secret', str(state))
        with self.assertRaises(runtime.PluginInitializationError):
            runtime.initialize_plugin('mix_test', bundle=data, strict=True)

    def test_yaml_include_cycles_are_reported(self):
        data = snapshot()
        data['configs'] = [dict(data['config'])]
        data['config']['content'] = '!include main'
        data['configs'][0]['content'] = '!include main'
        result = runtime.initialize_plugin('mix_test', bundle=data)
        self.assertEqual(result['INITIALIZATION_REPORT']['status'], 'degraded')
        self.assertEqual(result['INITIALIZATION_REPORT']['errors'][0]['stage'], 'config')

    def test_selected_template_supplies_attributes_without_legacy_app(self):
        data = {'plugin_runtime': [snapshot()]}
        from mix_toolkit import runtime as pipeline_runtime
        with patch.object(pipeline_runtime, 'get_runtime_configuration', return_value=data) as fetch:
            result = runtime.initialize_plugin('mix_test', strict=True)
            self.assertEqual(result['INITIALIZATION_REPORT']['source'], 'project_template')
            runtime.initialize_plugin('mix_test', strict=True)
            self.assertEqual(fetch.call_count, 1)
            runtime.initialize_plugin('mix_test', refresh=True, strict=True)
            self.assertEqual(fetch.call_count, 2)

    def test_unselected_plugin_does_not_fall_back_to_legacy(self):
        from mix_toolkit import runtime as pipeline_runtime
        app = types.SimpleNamespace(_get_plugin_attrs_config=lambda code: self.fail('Unselected plugin loaded'))
        with patch.object(pipeline_runtime, 'get_runtime_configuration', return_value={'plugin_runtime': []}):
            result = runtime.initialize_plugin('mix_test', legacy_app=app)
        self.assertEqual(result['INITIALIZATION_REPORT']['status'], 'unavailable')

    def test_attribute_relative_import_and_failed_module_cleanup(self):
        parent = types.ModuleType('mix_relative')
        parent.__path__ = []
        api = types.ModuleType('mix_relative.api')
        api.VALUE = 42
        with patch.dict(sys.modules, {'mix_relative': parent, 'mix_relative.api': api}):
            module = load_script({'code': 'attr', 'content': 'from .api import VALUE'}, package='mix_relative')
            self.assertEqual(module.VALUE, 42)
        with self.assertRaises(ValueError):
            load_script({'code': 'failed_module', 'content': 'raise ValueError()'}, is_uuid=False)
        self.assertNotIn('failed_module', sys.modules)

    def test_maya_keeps_core_api_and_cleans_up_removed_extensions(self):
        fake_cmds = types.ModuleType('maya.cmds')
        fake_maya = types.ModuleType('maya')
        fake_maya.cmds = fake_cmds
        data = snapshot()
        data.update(code='mix_maya', config=None, scripts=[])
        data['attrs'] = [{'code': 'api', 'content': 'def save(*args): return "old unsafe save"\ndef custom_helper(): return 42'}]
        source = ROOT / 'mix_maya/src/__init__.py'
        spec = importlib.util.spec_from_file_location('mix_maya', str(source), submodule_search_locations=[str(source.parent)])
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'maya': fake_maya, 'maya.cmds': fake_cmds, 'mix_maya': module}):
            with patch.object(runtime, '_bundle_for', return_value=(data, 'project_template')):
                spec.loader.exec_module(module)
            self.assertEqual(module.api.save.__module__, 'mix_maya.api')
            self.assertEqual(module.api.custom_helper(), 42)
            self.assertEqual(module.ATTRIBUTES['api'].save(), 'old unsafe save')
            data['attrs'] = []
            with patch.object(runtime, '_bundle_for', return_value=(data, 'project_template')):
                module.initialize_runtime(refresh=True)
            self.assertFalse(hasattr(module.api, 'custom_helper'))


if __name__ == '__main__':
    unittest.main()
