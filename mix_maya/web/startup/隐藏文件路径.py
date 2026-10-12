#!/usr/bin/env python
# -*- coding: utf8 -*-


import os
import maya.cmds as cmds
import maya.mel as mel

def main():
    def hide_file_path():
        file_path = cmds.file(q=1, sn=1)
        if os.path.isfile(file_path):
            file_name = os.path.basename(file_path)
            cmds.window('MayaWindow', e=1, t=file_name)
    cmds.scriptJob(e=['SceneSaved', hide_file_path])

