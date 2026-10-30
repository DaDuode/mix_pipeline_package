#!/usr/bin/env python
# -*- coding: utf8 -*-

import os
import sys


def _ensure_dcc_python_libs():
    dcc_libs = os.environ.get('DCC_PYTHON_LIBS')
    if not dcc_libs:
        cur = os.path.dirname(os.path.abspath(__file__))
        for _ in range(8):
            cand = os.path.join(cur, 'mix_studio_client', 'public', 'python', 'libs')
            if os.path.isdir(cand):
                dcc_libs = cand
                break
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            cur = parent
    if dcc_libs and os.path.isdir(dcc_libs) and dcc_libs not in sys.path:
        sys.path.append(dcc_libs)


_ensure_dcc_python_libs()

from .__menu import MenuType, MenuItem
from .__context import Context
from .__path_resolver import PathTemplateResolver
from . import logger
from .logger import error_decorator
from .runtime import diagnose, get_runtime_context, get_runtime_configuration, get_path_resolver, get_serve_client
from .plugin_runtime import get_plugin_state, run_plugin_script

__all__ = [
    'MenuType',
    'MenuItem',
    'Context',
    'PathTemplateResolver',
    'logger',
    'error_decorator',
    'diagnose',
    'get_runtime_context',
    'get_runtime_configuration',
    'get_path_resolver',
    'get_serve_client',
    'get_plugin_state',
    'run_plugin_script',
]
