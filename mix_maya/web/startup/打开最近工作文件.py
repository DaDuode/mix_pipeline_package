#!/usr/bin/env python
# -*- coding: utf8 -*-
# title       :
# description :
# author      :'ShenMeng'

import mix_toolkit.api
import os
import maya.cmds as cmds
import mix_workfile.api


def main():

    try:
        from LiveLink import initLiveLink
        from Megascans import Installer
        from DHI import DHIPluginLoader
        try:
            DHIPluginLoader.load()
        finally:   
            Installer.createMSshelf()
            initLiveLink()
    except Exception as e:
        print(e)
        try:
            from DHI import PluginLoader
            from LiveLink import initLiveLink
            from Megascans import Installer
            PluginLoader.load()
            Installer.createMSshelf()
            initLiveLink()

        except Exception as e:
            print(e)

    cmds.upAxis(axis='y', rv=1)
    engine = mix_toolkit.api.get_current_engine()
    _task_file = None
    task_file = None
    result_data = mix_workfile.api.work_file(engine.context)
    if result_data:
        if not isinstance(list(result_data.keys())[0], int):
            _data = {}
            for _name in result_data:
                _versions = list(result_data[_name].keys())
                _data.setdefault(_name, {})[max(
                    _versions)] = result_data[_name][max(_versions)]
            _task_file = _data
        else:
            versions = list(result_data.keys())
            _task_file = result_data[max(versions)]

    if _task_file:
        task_file = _task_file['path']
    if task_file and os.path.isfile(task_file):
        cmds.file(new=True, force=True)
        cmds.file(task_file, open=True, force=True, ignoreVersion=True)
        workspace = os.path.dirname(task_file)
        cmds.workspace(workspace, openWorkspace=True)
    else:

        import mix_filesave
        mix_filesave.api_init_file()
        engine.handle.api.init_scene(engine.context)
