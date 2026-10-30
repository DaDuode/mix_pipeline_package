#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from . import api
from . import menu

ATTRIBUTES = {}
SCRIPTS = {}
INITIALIZATION_REPORT = {'code': __name__, 'status': 'not_initialized'}
_api_extensions = {}
_runtime_attributes = {}


def initialize_runtime(refresh=False, strict=False):
    """Load plugin attributes while keeping the maintained local api/menu."""
    global ATTRIBUTES, SCRIPTS, INITIALIZATION_REPORT
    from mix_toolkit.plugin_runtime import initialize_plugin
    remote = initialize_plugin(__name__, refresh=refresh, strict=strict)
    ATTRIBUTES = remote['ATTRIBUTES']
    SCRIPTS = remote['SCRIPTS']
    INITIALIZATION_REPORT = remote['INITIALIZATION_REPORT']
    for name, value in _api_extensions.items():
        if getattr(api, name, None) is value:
            delattr(api, name)
    _api_extensions.clear()
    for name, value in _runtime_attributes.items():
        if globals().get(name) is value:
            globals().pop(name)
    _runtime_attributes.clear()
    for name, value in ATTRIBUTES.items():
        if name == 'api':
            for exported in getattr(value, '__all__', vars(value)):
                if not exported.startswith('_') and not hasattr(api, exported):
                    helper = getattr(value, exported)
                    setattr(api, exported, helper)
                    _api_extensions[exported] = helper
        elif name not in ('menu', 'initialize_runtime', 'ATTRIBUTES', 'SCRIPTS', 'INITIALIZATION_REPORT', 'PLUGIN_CONFIG'):
            globals()[name] = value
            _runtime_attributes[name] = value
    if 'PLUGIN_CONFIG' in remote:
        globals()['PLUGIN_CONFIG'] = remote['PLUGIN_CONFIG']
    else:
        globals().pop('PLUGIN_CONFIG', None)
    if INITIALIZATION_REPORT['status'] != 'ready':
        from mix_toolkit import logger
        logger.error('mix_maya plugin runtime: {}'.format(INITIALIZATION_REPORT))
    return INITIALIZATION_REPORT


initialize_runtime()
