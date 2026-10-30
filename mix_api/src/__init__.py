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

from .mix import MixSDK
from .serve import ServeClient, ServeAPIError
from . import cgt

__all__ = ['MixSDK', 'ServeClient', 'ServeAPIError', 'cgt']
