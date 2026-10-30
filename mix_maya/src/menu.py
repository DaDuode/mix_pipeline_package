#!/usr/bin/env python
# -*- coding: utf8 -*-
# title       : Maya 动态菜单渲染适配器
# description : 依照服务端下发的 group 与 label 动态构建 Maya 原生一级菜单与多级子菜单
# author      : 'ShenMeng', 'Mix Pipeline Team'

import os
import maya.cmds as cmds
import mix_toolkit


class Menu(object):
    """Maya 菜单控制器，支持多级 group 分组动态构建"""

    def __init__(self):
        menu_title = os.getenv('DCC_APP_CODE', 'MIX Pipeline')
        self.menu = cmds.menu(l=menu_title, to=1, p='MayaWindow')
        self._cmds = {}
        self._groups = {}

    def _get_parent_menu(self, group_name):
        """根据 group 属性获取或创建二级子菜单项"""
        if not group_name or group_name in ('Custom', 'Root', ''):
            return self.menu
        if group_name not in self._groups or not cmds.menuItem(self._groups[group_name], q=1, ex=1):
            self._groups[group_name] = cmds.menuItem(l=group_name, subMenu=True, p=self.menu)
        return self._groups[group_name]

    def register_command(self, item):
        """向菜单树注册或更新菜单项"""
        if cmds.menu(self.menu, q=1, ex=1):
            parent = self._get_parent_menu(getattr(item, 'group', None))
            if item.type == mix_toolkit.MenuType.Separator:
                cmds.menuItem(divider=True, p=parent)
            elif item.type == mix_toolkit.MenuType.Action:
                menu = self._cmds.get(item.uuid)
                if menu and cmds.menuItem(menu, q=1, ex=1):
                    cmds.menuItem(menu, e=1, c=item.command, l=item.label)
                else:
                    menu = cmds.menuItem(l=item.label, c=item.command, p=parent)
                    self._cmds[item.uuid] = menu
