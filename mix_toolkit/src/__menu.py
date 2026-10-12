#!/usr/bin/env python
# -*- coding: utf8 -*-
# title       : Kmoke菜单模块
# description : 提供菜单项的定义和管理功能
# author      : 'ShenMeng'

import uuid
import copy

class MenuType:
    """
    菜单类型枚举
    
    定义了三种基本的菜单类型：
    - Action: 可执行动作
    - Separator: 分隔符
    - Menu: 子菜单
    """
    Action = 'action'      # 动作菜单项
    Separator = 'separator'  # 分隔符
    Menu = 'menu'         # 子菜单项


class MenuItem(object):
    """
    菜单项类
    
    用于创建和管理单个菜单项，支持不同类型的菜单项（动作、分隔符、子菜单）
    每个菜单项都有唯一的UUID标识
    """
    
    def __init__(self, menu_name=None, menu_label=None, menu_type=None, 
                 menu_command=None, menu_uuid=None, 
                 menu_group='Custom', extra_fields={}):
        """
        初始化菜单项
        
        Args:
            menu_name (str, optional): 菜单所属的脚本或插件名称
            menu_label (str, optional): 菜单在界面上显示的文本
            menu_type (str, optional): 菜单类型，参考MenuType类
            menu_command (callable, optional): 菜单执行的命令或函数
            extra_fields (bool, optional): 是否为序列菜单项
            menu_uuid (str, optional): 菜单项的唯一标识符
            other (any, optional): 附加的自定义数据
            menu_group (str, optional): 菜单所属分组，默认为'Custom'
        """
        self.__name = menu_name
        self.__label = menu_label
        self.__type = menu_type
        self.__command = menu_command
        self.__uuid = menu_uuid if menu_uuid else 'a' + uuid.uuid4().hex  # 确保UUID以字母开头
        self.__extra_fields = extra_fields
        self.__group = menu_group

    @property
    def name(self):
        """获取菜单项的名称"""
        return self.__name

    @property
    def label(self):
        """获取菜单项的显示文本"""
        return self.__label

    @property
    def type(self):
        """获取菜单项的类型"""
        return self.__type
    @property
    def extra_fields(self):
        """获取菜单项的类型"""
        return copy.deepcopy(self.__extra_fields)

    @property
    def command(self):
        """获取菜单项关联的命令"""
        return self.__command
    
    @property
    def group(self):
        """获取菜单项所属的分组"""
        return self.__group

    @property
    def uuid(self):
        """获取菜单项的唯一标识符"""
        return self.__uuid

    def update(self, label, command):
        """
        更新菜单项的显示文本和命令
        
        Args:
            label (str): 新的显示文本
            command (callable): 新的命令或函数
        """
        if label and command:
            self.__label = label
            self.__command = command
