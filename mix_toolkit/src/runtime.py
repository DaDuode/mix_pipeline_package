# -*- coding: utf-8 -*-
"""Read-only access to the active task, Serve configuration and diagnostics."""
import json
import os
import platform
import re
import sys

import yaml
from mix_api.serve import ServeClient

from .__context import Context


def _app_code(environ):
    return (environ.get('MSC_DCC_APP_CODE') or environ.get('DCC_APP_CODE') or 'MIX').upper()


def _context(environ, use_engine):
    # Inspect an existing engine; never import api or start an engine for a query.
    api = sys.modules.get(__package__ + '.api') if use_engine else None
    engine = getattr(api, 'ENGINE_INSTANCE', None)
    if engine is not None and engine.context is not None:
        return Context(engine.context.to_dict()), 'engine', engine
    value = environ.get(_app_code(environ) + '_CONTEXT_JSON', '')
    if value:
        try:
            data = json.loads(value)
        except (ValueError, TypeError) as exc:
            raise ValueError('Launch context is not valid JSON') from exc
        if not isinstance(data, dict):
            raise ValueError('Launch context must be an object')
        return Context(data), 'environment', engine
    return Context(), 'missing', engine


def get_runtime_context(environ=None):
    """Return an independent copy of the current engine/launch task context."""
    return _context(os.environ if environ is None else environ, environ is None)[0]


def get_serve_client(environ=None, **kwargs):
    """Create a client without connecting or verifying a legacy application."""
    return ServeClient.from_environment(environ=environ, **kwargs)


def get_runtime_configuration(client=None, context=None, environ=None):
    """Resolve this task's strict project/step/software configuration on demand."""
    env = os.environ if environ is None else environ
    ctx = context if context is not None else get_runtime_context(environ)
    data = ctx.to_dict() if isinstance(ctx, Context) else ctx
    if not isinstance(data, dict):
        raise TypeError('context must be a Context or dictionary')
    prefix = _app_code(env) + '_'
    software = data.get('Software') or {}
    params = {
        'project_code': (data.get('Project') or {}).get('code') or env.get(prefix + 'PROJECT_CODE'),
        'step_code': (data.get('Step') or {}).get('code') or env.get(prefix + 'STEP_CODE'),
        'software_code': software.get('code') or env.get(prefix + 'SOFTWARE_CODE'),
        'software_version': software.get('version') or env.get(prefix + 'SOFTWARE_VERSION'),
        'strict_project': True,
    }
    owned = client is None
    client = client if client is not None else get_serve_client(env)
    try:
        result = client.resolve_software_template(**params)
    finally:
        if owned:
            client.close()
    if result is None:
        raise ValueError('No software configuration matches the current project and step')
    if not isinstance(result, dict):
        raise ValueError('Resolved software configuration must be an object')
    return result


def get_path_resolver(configuration=None, **kwargs):
    """Load the resolved storage YAML for path queries without writing files."""
    from .__path_resolver import PathTemplateResolver
    config = configuration if configuration is not None else get_runtime_configuration(**kwargs)
    storage = config.get('storage_template') or {}
    content = storage.get('content')
    if not content:
        raise ValueError('The project has no storage template content')
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise ValueError('Storage template contains invalid YAML') from exc
    if not isinstance(data, dict) or not data:
        raise ValueError('Storage template content must be a nonempty YAML mapping')
    return PathTemplateResolver(config_data=data)


def diagnose(check_server=True, client=None, environ=None):
    """Collect a JSON-compatible report without scene changes or credential dumps.

    check_server=False performs no network calls. Errors are returned as checks
    so the report remains usable when the task or server is unavailable.
    """
    env = os.environ if environ is None else environ
    prefix = _app_code(env) + '_'
    report = {
        'python': platform.python_version(), 'app_code': _app_code(env),
        'context_source': 'missing', 'context': {}, 'engine_started': False,
        'packages': {}, 'checks': [], 'server': 'not_checked',
    }

    def check(name, ok, message, level='error'):
        report['checks'].append({'name': name, 'ok': bool(ok), 'level': 'info' if ok else level, 'message': message})

    try:
        ctx, source, engine = _context(env, environ is None)
        report['context_source'] = source
        report['engine_started'] = bool(engine is not None and engine.is_start)
        fields = {'Project': ('id', 'code', 'database'), 'Entity': ('id', 'code', 'type', 'asset_type'),
                  'Step': ('id', 'code'), 'Task': ('id', 'code'), 'Software': ('code', 'version', 'engine_code')}
        data = ctx.to_dict()
        for key, allowed in fields.items():
            item = data.get(key) or {}
            if not isinstance(item, dict):
                raise ValueError('{}.context must be an object'.format(key))
            report['context'][key] = {field: item[field] for field in allowed if field in item}
        for key in ['Project', 'Entity', 'Step', 'Task']:
            item = report['context'][key]
            check('context.' + key, bool(item.get('id') and item.get('code')), '{} requires id and code'.format(key))
        for key in ['Entity', 'Step']:
            if str(report['context'][key].get('id')) == '1':
                check('context.' + key + '.identity', False, '{} uses the launcher placeholder ID 1'.format(key), 'warning')
        check('engine.started', report['engine_started'], 'The toolkit engine has started', 'warning')
    except (ValueError, TypeError, AttributeError) as exc:
        ctx = Context()
        check('context', False, str(exc))

    for name in ['mix_api', 'mix_toolkit', env.get(prefix + 'SOFTWARE_ENGINE_CODE', 'mix_maya')]:
        module = sys.modules.get(name)
        file_path = getattr(module, '__file__', None)
        version_dir = os.path.basename(os.path.dirname(os.path.dirname(file_path))) if file_path else ''
        report['packages'][name] = {'loaded': module is not None, 'path': file_path,
                                    'version': version_dir if re.match(r'^\d+\.\d+', version_dir) else None}
        check('package.' + name, module is not None, '{} {}'.format(name, 'is loaded' if module is not None else 'is not loaded'), 'warning')

    plugin_runtime = sys.modules.get(__package__ + '.plugin_runtime')
    state_getter = getattr(plugin_runtime, 'get_plugin_state', None)
    engine_code = env.get(prefix + 'SOFTWARE_ENGINE_CODE', 'mix_maya')
    if state_getter:
        state = state_getter(engine_code)
        report['plugin_initialization'] = state
        check('plugin.' + engine_code, state.get('status') == 'ready', 'Plugin attribute/config loading state: ' + state.get('status', 'unknown'), 'warning')

    if check_server:
        owned = client is None
        try:
            client = client if client is not None else get_serve_client(env)
            healthy = client.health().get('status') == 'healthy'
            report['server'] = 'healthy' if healthy else 'unhealthy'
            check('server.health', healthy, 'Serve health check')
            config = get_runtime_configuration(client=client, context=ctx, environ=env)
            engine = config.get('engine') or {}
            storage = config.get('storage_template') or {}
            report['configuration'] = {
                'template_code': config.get('template_code'), 'software_code': config.get('software_code'),
                'software_version': config.get('software_version'),
                'engine': {key: engine.get(key) for key in ('id', 'code', 'version')},
                'storage_template_code': storage.get('code'),
                'plugin_count': len(config.get('plugins') or []),
                'script_count': len(config.get('scripts') or []),
                'startup_script_count': len(config.get('startup_scripts') or []),
                'check_item_count': len(config.get('check_items') or []),
                'plugin_runtime': [
                    {'code': p.get('code'), 'version': p.get('version'),
                     'attribute_count': len(p.get('attrs') or []), 'script_count': len(p.get('scripts') or []),
                     'config_count': len(p.get('configs') or [])}
                    for p in config.get('plugin_runtime') or []
                ],
            }
            check('configuration.engine', bool(engine.get('id')), 'The software has a bound engine version')
            configured_code = engine.get('code')
            loaded = report['packages'].get(configured_code, {})
            check('configuration.engine_loaded', loaded.get('loaded'), 'The configured engine package is loaded', 'warning')
            if loaded.get('version'):
                check('configuration.engine_version', loaded['version'] == engine.get('version'), 'Loaded and configured engine versions match', 'warning')
            running_version = env.get(prefix + 'SOFTWARE_VERSION')
            if running_version:
                check('configuration.software_version', running_version == config.get('software_version'), 'Launched and configured software versions match', 'warning')
            get_path_resolver(configuration=config)
            check('configuration.storage', True, 'The project storage template can be loaded')
        except Exception as exc:
            check('server.configuration', False, str(exc))
            if report['server'] == 'not_checked':
                report['server'] = 'unavailable'
        finally:
            if owned and client is not None:
                client.close()
    report['ok'] = not any(not c['ok'] and c['level'] == 'error' for c in report['checks'])
    return report
