# -*- coding: utf-8 -*-
"""Load selected plugin attributes; register ordinary scripts for explicit use."""
import copy
import hashlib
import json
import os

import yaml

from .utils import load_script

_bundles = {}
_states = {}
_scripts = {}
_modules = {}


class PluginInitializationError(RuntimeError):
    pass


class PluginNotSelectedError(PluginInitializationError):
    pass


def _bundle_for(plugin_code, refresh=False):
    from .runtime import get_runtime_context, get_runtime_configuration
    context = get_runtime_context()
    data = context.to_dict()
    prefix = (os.environ.get('MSC_DCC_APP_CODE') or os.environ.get('DCC_APP_CODE') or 'MIX').upper() + '_'
    key = (os.environ.get('DCC_BASE_URL') or os.environ.get('MSC_SERVER_URL') or os.environ.get('DCC_SERVER_URL'),
           (data.get('Project') or {}).get('code'), (data.get('Step') or {}).get('code'),
           (data.get('Task') or {}).get('id'), (data.get('Software') or {}).get('code') or os.environ.get(prefix + 'SOFTWARE_CODE'),
           (data.get('Software') or {}).get('version') or os.environ.get(prefix + 'SOFTWARE_VERSION'))
    if refresh or key not in _bundles:
        config = get_runtime_configuration(context=context)
        if 'plugin_runtime' not in config:
            raise PluginInitializationError('Serve does not provide plugin_runtime; update the backend')
        _bundles[key] = {p['code']: p for p in config['plugin_runtime']}
    if plugin_code not in _bundles[key]:
        raise PluginNotSelectedError('Plugin {} is not selected by the current project template'.format(plugin_code))
    return _bundles[key][plugin_code], 'project_template'


def _parse_config(config, configs, active=None):
    kind = (config.get('config_type') or 'json').lower()
    content = config.get('content') or ''
    if kind == 'json':
        return json.loads(content) if content else {}
    if kind in ('text', 'txt'):
        return content
    if kind not in ('yaml', 'yml'):
        raise ValueError('Unsupported plugin config type: ' + kind)
    visited = set(active or ())
    code = config['code']
    if code in visited:
        raise ValueError('Plugin config include cycle: ' + code)
    visited.add(code)

    class Loader(yaml.SafeLoader):
        pass

    def include(loader, node):
        name = loader.construct_scalar(node)
        included = next((c for c in configs if c['code'] == name), None)
        if included is None:
            raise ValueError('Plugin config include is missing: ' + name)
        return _parse_config(included, configs, visited)

    Loader.add_constructor('!include', include)
    return yaml.load(content, Loader=Loader)


def initialize_plugin(plugin_code, bundle=None, strict=False, refresh=False, legacy_app=None):
    """Return attributes, script metadata and a small initialization report.

    Attribute code executes at initialization. Ordinary script code executes
    only through run_plugin_script(). Failures leave the local adapter usable.
    """
    state = {'code': plugin_code, 'source': 'local_fallback', 'status': 'unavailable',
             'attributes': [], 'scripts': [], 'config_loaded': False, 'errors': []}
    result = {'ATTRIBUTES': {}, 'SCRIPTS': {}}
    _scripts[plugin_code] = {}
    try:
        if bundle is None:
            try:
                bundle, source = _bundle_for(plugin_code, refresh)
            except PluginNotSelectedError:
                raise
            except Exception:
                if legacy_app is None:
                    raise
                data = legacy_app._get_plugin_attrs_config(plugin_code) or {}
                bundle = dict(data, code=plugin_code, scripts=legacy_app._get_plugin_scripts(plugin_code) or [])
                source = 'legacy_service'
        else:
            source = 'provided_snapshot'
        if bundle.get('code') != plugin_code:
            raise ValueError('Plugin runtime snapshot does not match ' + plugin_code)
        state['source'] = source
        state['version_id'] = bundle.get('version_id')
        state['version'] = bundle.get('version')
        for attr in bundle.get('attrs') or []:
            if not bundle.get('has_attribute', True):
                break
            code = attr.get('code') or ''
            try:
                if not code.isidentifier() or code.startswith('_') or code in result:
                    raise ValueError('Invalid or reserved attribute name')
                module = load_script(attr, package=plugin_code)
                result['ATTRIBUTES'][code] = module
                result[code] = module
                state['attributes'].append(code)
            except Exception as exc:
                state['errors'].append({'stage': 'attribute', 'code': code, 'error': type(exc).__name__})
        if bundle.get('has_script', True):
            result['SCRIPTS'] = {s['code'].lower(): copy.deepcopy(s) for s in bundle.get('scripts') or []}
            _scripts[plugin_code] = result['SCRIPTS']
            state['scripts'] = sorted(result['SCRIPTS'])
        if bundle.get('has_config', True) and bundle.get('config'):
            try:
                result['PLUGIN_CONFIG'] = _parse_config(bundle['config'], bundle.get('configs') or [bundle['config']])
                state['config_loaded'] = True
            except Exception as exc:
                state['errors'].append({'stage': 'config', 'code': bundle['config'].get('code'), 'error': type(exc).__name__})
        state['status'] = 'degraded' if state['errors'] else 'ready'
    except Exception as exc:
        state['errors'].append({'stage': 'runtime', 'error': type(exc).__name__,
                                'message': 'Plugin runtime configuration could not be loaded'})
    _states[plugin_code] = state
    result['INITIALIZATION_REPORT'] = copy.deepcopy(state)
    if strict and state['status'] != 'ready':
        raise PluginInitializationError('Plugin {} initialization failed: {}'.format(plugin_code, state['errors']))
    return result


def get_plugin_state(plugin_code):
    return copy.deepcopy(_states.get(plugin_code, {'code': plugin_code, 'status': 'not_initialized'}))


def run_plugin_script(plugin_code, script_code, *args, **kwargs):
    """Explicitly invoke main() of a registered plugin script."""
    script = _scripts.get(plugin_code, {}).get(script_code.lower())
    if script is None:
        raise KeyError('Plugin script is not registered: {}.{}'.format(plugin_code, script_code))
    content = script.get('content') or ''
    key = (plugin_code, script_code.lower(), hashlib.sha256(content.encode('utf-8')).hexdigest())
    if key not in _modules:
        _modules[key] = load_script(script, package=plugin_code)
    main = getattr(_modules[key], 'main', None)
    if not callable(main):
        raise ValueError('Plugin script has no callable main(): ' + script_code)
    return main(*args, **kwargs)
