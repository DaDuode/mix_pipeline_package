#!/usr/bin/env python
# -*- coding: utf8 -*-

import maya.cmds as cmds

cmd = """
print('mix_maya loading ................................................')
import sys
import mix_toolkit.api
import mix_maya

def start_toolkit():
    try:
        engine = mix_toolkit.api.get_current_engine()
        if hasattr(mix_maya, 'menu') and hasattr(mix_maya.menu, 'Menu'):
            engine.start(mix_maya.menu.Menu())
            print('[Mix Pipeline] Maya Engine started successfully.')
    except Exception as e:
        print('[Mix Pipeline] Error starting Maya Engine: %s' % str(e))

start_toolkit()
"""
cmds.evalDeferred(cmd)
