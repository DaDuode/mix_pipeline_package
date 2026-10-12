#!/usr/bin/env python
# -*- coding: utf8 -*-
# title       :
# description :
# author      :'ShenMeng'


import maya.cmds as cmds
import mix_toolkit
import os


class Menu(object):
    def __init__(self):
        self.menu = cmds.menu(l=os.getenv('DCC_APP_CODE', 'Mix'), to=1, p='MayaWindow')
        self._cmds = {}

    def register_command(self, item):
        if cmds.menu(self.menu, q=1, ex=1):
            if item.type == mix_toolkit.MenuType.Separator:
                cmds.menuItem(divider=True, p=self.menu)
            elif item.type == mix_toolkit.MenuType.Action:
                menu = self._cmds.get(item.uuid)
                if menu:
                    if cmds.menuItem(menu, q=1, ex=1):
                        cmds.menuItem(menu, e=1, c=item.command, l=item.label)
                else:
                    menu = cmds.menuItem(
                        l=item.label, c=item.command, p=self.menu)
                    self._cmds[item.uuid] = menu
