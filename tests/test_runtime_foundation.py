# -*- coding: utf-8 -*-
"""No-scene regression tests, runnable with shipped Python 3.7 or mayapy."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT.parent / 'mix_studio_client/public/python/libs'))
for package in ['mix_api', 'mix_toolkit']:
    source = ROOT / package / 'src/__init__.py'
    spec = importlib.util.spec_from_file_location(package, str(source), submodule_search_locations=[str(source.parent)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[package] = module
    spec.loader.exec_module(module)

from mix_api import ServeClient, ServeAPIError
from mix_toolkit import Context, diagnose, get_runtime_context, get_runtime_configuration, get_path_resolver


class Response:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status_code = status

    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


class Session:
    def __init__(self, response):
        self.response = response
        self.calls = []
        self.closed = False

    def get(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response

    def close(self):
        self.closed = True


class ServeClientTests(unittest.TestCase):
    def test_construction_is_offline_and_query_needs_no_application_key(self):
        session = Session(Response({'code': 200, 'data': []}))
        client = ServeClient('http://localhost:8765/', session=session)
        self.assertEqual(session.calls, [])
        self.assertEqual(client.get_softwares(), [])
        args, kwargs = session.calls[0]
        self.assertEqual(args[0], 'http://localhost:8765/api/client/softwares')
        self.assertNotIn('X-API-Key', kwargs['headers'])
        self.assertEqual(kwargs['timeout'], (3, 10))

    def test_exact_resolve_parameters_and_unmatched_template(self):
        session = Session(Response({'code': 200, 'data': None}))
        client = ServeClient('http://localhost:8765', session=session)
        self.assertIsNone(client.resolve_software_template(' proj_mxdckz ', 'Mod', 'maya', '2024'))
        self.assertEqual(session.calls[0][1]['params'], {
            'project_code': 'proj_mxdckz', 'step_code': 'Mod', 'software_code': 'maya',
            'software_version': '2024', 'strict_project': 'true',
        })
        with self.assertRaises(ValueError):
            client.resolve_software_template('', 'Mod', 'maya')

    def test_http_and_application_errors_remain_distinguishable(self):
        for response, status, code in [(Response({}, 403), 403, None),
                                       (Response({'code': 400, 'message': 'Invalid engine'}), None, 400)]:
            client = ServeClient('http://localhost', session=Session(response))
            with self.assertRaises(ServeAPIError) as raised:
                client.get_plugins()
            self.assertEqual(raised.exception.status_code, status)
            self.assertEqual(raised.exception.code, code)

    def test_invalid_responses(self):
        for payload in [ValueError('not json'), [], {'code': 200}]:
            client = ServeClient('http://localhost', session=Session(Response(payload)))
            with self.assertRaises(ServeAPIError):
                client.get_cgt_config()

    def test_transport_error_does_not_echo_credentials(self):
        import requests
        session = Session(requests.exceptions.ConnectionError('http://server?api_key=secret'))
        with self.assertRaises(ServeAPIError) as raised:
            ServeClient('http://localhost', session=session).health()
        self.assertNotIn('secret', str(raised.exception))

    def test_environment_factory_health_and_borrowed_session(self):
        session = Session(Response({'status': 'healthy'}))
        with ServeClient.from_environment({'DCC_BASE_URL': 'http://localhost', 'DCC_API_KEY': 'secret'}, session=session) as client:
            self.assertEqual(client.health(), {'status': 'healthy'})
        self.assertFalse(session.closed)
        self.assertEqual(session.calls[0][1]['headers']['X-API-Key'], 'secret')
        with self.assertRaises(ValueError):
            ServeClient.from_environment({})


class ContextTests(unittest.TestCase):
    def test_constructor_copies_input_for_attribute_and_dictionary_access(self):
        source = {'Task': {'id': 'task1'}}
        ctx = Context(source)
        source['Task']['id'] = 'outside'
        self.assertEqual(ctx.Task['id'], 'task1')
        self.assertEqual(ctx.to_dict()['Task']['id'], 'task1')

    def test_updates_and_attribute_assignment_share_the_same_data(self):
        ctx = Context({'Task': {'id': 'task1'}})
        ctx.update_key('Task', {'id': 'task2'})
        self.assertEqual(ctx.Task['id'], 'task2')
        ctx.set_entity('Entity', {'code': 'Hero'})
        self.assertEqual(ctx.Entity['code'], 'Hero')
        ctx.Task = {'id': 'task3'}
        self.assertEqual(ctx.to_dict()['Task']['id'], 'task3')
        ctx.Task['id'] = 'task4'
        self.assertEqual(ctx.to_dict()['Task']['id'], 'task4')

    def test_deepcopy_and_dictionary_outputs_are_independent(self):
        ctx = Context({'Task': {'id': 'task1'}})
        cloned = copy.deepcopy(ctx)
        cloned.Task['id'] = 'task2'
        snapshot = ctx.to_dict()
        snapshot['Task']['id'] = 'task3'
        self.assertEqual(ctx.Task['id'], 'task1')
        self.assertFalse(ctx.has_key('Missing'))
        with self.assertRaises(AttributeError):
            _ = ctx.Missing

    def test_engine_added_software_and_user_are_accessible_as_attributes(self):
        with patch.dict(os.environ, {'DCC_BASE_URL': ''}):
            from mix_toolkit.__engine import Engine
        engine = Engine()
        engine.start_without_software()
        engine.set_context(Context({'Task': {'id': 'new-task', 'code': 'Mod'}}))
        self.assertTrue(engine.context.has_key('Software'))
        self.assertEqual(engine.context.Software, {})
        self.assertTrue(engine.context.User['code'])
        self.assertEqual(engine.context.Task['id'], 'new-task')


CONTEXT = {'Project': {'id': 'p1', 'code': 'proj_mxdckz'}, 'Entity': {'id': 'a1', 'code': 'Hero', 'type': 'Asset'},
           'Step': {'id': 's1', 'code': 'Mod'}, 'Task': {'id': 't1', 'code': 'Mod'}, 'password': 'context-secret'}
ENV = {'DCC_APP_CODE': 'MAYA', 'DCC_BASE_URL': 'http://localhost:8765',
       'MAYA_SOFTWARE_CODE': 'maya', 'MAYA_SOFTWARE_VERSION': '2024',
       'MAYA_CONTEXT_JSON': json.dumps(CONTEXT), 'MAYA_CGT_PASSWORD': 'cgt-secret', 'DCC_API_KEY': 'key-secret'}
CONFIG = {'template_code': 'PROJECT', 'software_code': 'maya', 'software_version': '2024',
          'engine': {'id': 6, 'code': 'mix_maya', 'version': '1.0.0'},
          'storage_template': {'code': 'mx', 'content': 'paths:\n  project_root: "P:/MX"\n'},
          'scripts': [{'code': 'script', 'content': 'script-secret'}]}


class Client:
    def health(self):
        return {'status': 'healthy'}

    def resolve_software_template(self, **kwargs):
        self.params = kwargs
        return copy.deepcopy(CONFIG)


class RuntimeTests(unittest.TestCase):
    def test_context_comes_from_launch_environment_without_engine_creation(self):
        before = sys.modules.get('mix_toolkit.api')
        ctx = get_runtime_context(ENV)
        self.assertEqual(ctx.Task['id'], 't1')
        self.assertIs(sys.modules.get('mix_toolkit.api'), before)

    def test_active_engine_context_wins_after_a_task_switch(self):
        active = Context(dict(CONTEXT, Task={'id': 'new-task', 'code': 'Tex'}))
        engine = types.SimpleNamespace(context=active, is_start=True)
        api = types.SimpleNamespace(ENGINE_INSTANCE=engine)
        with patch.dict(sys.modules, {'mix_toolkit.api': api}), patch.dict(os.environ, ENV):
            ctx = get_runtime_context()
        self.assertEqual(ctx.Task['id'], 'new-task')
        ctx.Task['id'] = 'outside'
        self.assertEqual(active.Task['id'], 'new-task')

    def test_configuration_query_uses_the_current_task(self):
        client = Client()
        result = get_runtime_configuration(client=client, environ=ENV)
        self.assertEqual(result['template_code'], 'PROJECT')
        self.assertEqual(client.params['project_code'], 'proj_mxdckz')
        self.assertEqual(client.params['step_code'], 'Mod')
        self.assertEqual(client.params['software_version'], '2024')
        self.assertTrue(client.params['strict_project'])

    def test_path_template_loading_without_scene_or_file_operations(self):
        resolver = get_path_resolver(configuration=CONFIG)
        self.assertEqual(resolver.config_data['paths']['project_root'], 'P:/MX')
        broken = copy.deepcopy(CONFIG)
        broken['storage_template']['content'] = 'password: [secret\n'
        with self.assertRaisesRegex(ValueError, 'invalid YAML') as raised:
            get_path_resolver(configuration=broken)
        self.assertNotIn('secret', str(raised.exception))

    def test_diagnostics_do_not_dump_passwords_keys_or_scripts(self):
        report = diagnose(client=Client(), environ=ENV)
        text = json.dumps(report)
        for secret in ['cgt-secret', 'key-secret', 'context-secret', 'script-secret']:
            self.assertNotIn(secret, text)
        self.assertTrue(report['ok'])
        self.assertEqual(report['configuration']['engine']['id'], 6)
        self.assertEqual(report['server'], 'healthy')

    def test_offline_diagnostics_make_no_network_calls(self):
        with patch('requests.Session.get', side_effect=AssertionError('Unexpected network')):
            report = diagnose(check_server=False, environ=ENV)
        self.assertTrue(report['ok'])
        self.assertEqual(report['server'], 'not_checked')

    def test_broken_context_returns_a_diagnostic_instead_of_crashing(self):
        report = diagnose(check_server=False, environ=dict(ENV, MAYA_CONTEXT_JSON='invalid-secret'))
        self.assertFalse(report['ok'])
        self.assertNotIn('invalid-secret', json.dumps(report))


@unittest.skipUnless(os.environ.get('MIX_TEST_LAUNCH_FILE'), 'No live launch snapshot selected')
class LaunchSnapshotIntegrationTests(unittest.TestCase):
    def test_actual_launched_task_can_query_its_template_and_storage(self):
        snapshot = json.loads(Path(os.environ['MIX_TEST_LAUNCH_FILE']).read_text(encoding='utf-8'))
        env = {
            'DCC_APP_CODE': 'MAYA', 'DCC_BASE_URL': 'http://127.0.0.1:8765',
            'MAYA_CONTEXT_JSON': json.dumps(snapshot['context']),
            'MAYA_SOFTWARE_CODE': snapshot['software']['code'],
            'MAYA_SOFTWARE_VERSION': snapshot['software']['version'],
            'MAYA_SOFTWARE_ENGINE_CODE': snapshot['software']['engine_code'],
        }
        report = diagnose(environ=env)
        self.assertTrue(report['ok'], report['checks'])
        self.assertEqual(report['server'], 'healthy')
        self.assertEqual(report['configuration']['engine']['code'], 'mix_maya')
        self.assertEqual(report['configuration']['storage_template_code'], 'mx')
        resolver = get_path_resolver(environ=env)
        self.assertTrue(resolver.config_data.get('paths'))
        print('Launch snapshot configuration: {} / {} / {} {}'.format(
            report['context']['Project']['code'], report['context']['Step']['code'],
            report['configuration']['engine']['code'], report['configuration']['engine']['version']))


if __name__ == '__main__':
    unittest.main()
