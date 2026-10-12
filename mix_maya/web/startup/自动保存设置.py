#!/usr/bin/env python
# -*- coding: utf8 -*-
# title       :
# description :
# author      :'ShenMeng'


import maya.mel as mel


def main(*args, **kwargs):
    mel.eval("optionVar -intValue isIncrementalSaveEnabled 1;")
    mel.eval("optionVar -intValue incrementalSaveLimitBackups 1;")
    mel.eval("optionVar -intValue incrementalSaveMaxBackups 3;")
