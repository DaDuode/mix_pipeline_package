#!/usr/bin/env python
# -*- coding: utf8 -*-
# title       :
# description :
# author      :'HuangShuai'
import os
import maya.mel as mel

def get_path():
    folder_path = os.path.dirname(__file__)
    result_path = folder_path.replace('\\', '/')
    return result_path

def bakeDynamics():
    source_file = os.path.join(get_path(),'bakeDynamics.mel')
    result_file = source_file.replace('\\', '/')
    string_cmd = 'source "%s";%s;' % (result_file, "bakeDynamics")
    print string_cmd
    mel.eval(string_cmd)