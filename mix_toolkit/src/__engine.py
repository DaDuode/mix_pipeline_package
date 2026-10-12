#!/usr/bin/env python
# -*- coding: utf8 -*-
# title       : Kmoke引擎模块
# description : Kmoke工具包的核心引擎实现，负责软件启动、插件管理和上下文控制
# author      :'ShenMeng'


import traceback
import functools
import os
import importlib
import copy
from .__setting import SOFTWARE_ID, PROJECT_ID, PROJECT_TEMPLATE, VERSION_KEY, VARIANT_KEY, DCC_APP_CODE, TASK_ID, APP
from .utils import load_script, singleton
from .__menu import MenuType, MenuItem
from .__context import Context
from .logger import error_decorator


# @singleton
class Engine():
    """
    Kmoke引擎核心类，实现软件启动、菜单管理、插件加载等功能
    
    主要功能：
    1. 软件启动和版本控制
    2. 插件和脚本管理
    3. 上下文管理
    4. 菜单项注册和更新
    """
    def __init__(self):
        """
        初始化引擎实例，设置基础属性
        """
        self.__menu = None          # 菜单实例
        self.__context = None       # 上下文实例
        self.__plugins_fileds = {}  # 插件字段
        self.__handle = None        # 软件包处理器
        self.__is_start = False     # 引擎启动状态
        self.__software = {}        # 软件信息
        self.menu_items = {}        # 菜单项集合
        self.commands = {}          # 命令集合

    def list_command(self):
        """
        获取所有已注册的命令列表
        
        Returns:
            list: 命令列表
        """
        if self.__menu:
            return self.__menu._cmds
        return []

    def restart(self, menu=None):
        """
        重启引擎
        
        Args:
            menu: 菜单实例，可选
        """
        self.__menu = None          # 菜单实例
        self.__context = None       # 上下文实例
        self.__plugins_fileds = {}  # 插件字段
        self.__handle = None        # 软件包处理器
        self.__is_start = False     # 引擎启动状态
        self.__software = {}        # 软件信息
        self.menu_items = {}        # 菜单项集合
        self.commands = {}          # 命令集合

        self.__start(True, menu)

    def start_without_software(self):
        """
        不加载软件的情况下启动引擎
        """
        if self.is_start:
            return
        self.__start(False, None)

    def start(self, menu=None):
        """
        启动引擎
        
        Args:
            menu: 菜单实例，可选
        """
        self.__start(True, menu)

    def set_context(self, value):
        """
        更新上下文信息
        
        Args:
            value (Context or dict): 上下文对象或字典数据
            
        Raises:
            ValueError: 引擎未初始化时尝试更改上下文
            TypeError: value类型不是Context或dict
        """
        if not self.is_start:
            raise ValueError('can not change context without init engine!')
        if isinstance(value, Context):
            if value.Task['id'] == self.__context.Task['id']:
                return

            self.update = False
            if not value.has_key('Software'):
                value.update_key('Software', self.__software)
            if not value.has_key('User'):
                value.update_key('User', {'type': 'User',
                                          'code': os.environ['%s_USER' % DCC_APP_CODE],
                                          'id': os.environ['%s_USER_ID' % DCC_APP_CODE]})
            self.__context = value

        elif isinstance(value, dict):
            if value['Task']['id'] == self.__context.Task['id']:
                return
            value['Software'] = self.__software
            value['User'] = {'type': 'User',
                             'id': os.environ['%s_USER_ID' % DCC_APP_CODE],
                             'code': os.environ['%s_USER' % DCC_APP_CODE]}
            self.__context = Context(value)
        else:
            raise TypeError("context must be an instance of Context.")
        os.environ['%s_TASK_ID' % DCC_APP_CODE] = str(self.__context.Task['id'])
        if self.__handle:
            if hasattr(self.__handle, 'api'):
                if hasattr(self.__handle.api, 'set_env'):
                    self.__handle.api.set_env(copy.deepcopy(self.__context))
        self.__update_menu()

    def __update_menu(self):
        """
        更新菜单：更新任务信息菜单项
        
        功能：
        1. 检查菜单实例是否存在
        2. 更新任务信息标签
        3. 重新注册菜单命令
        """
        if not self.__menu:
            return
        if self.context and hasattr(self.context, 'Task'):
            name = u'{} > {} > {}'.format(
                self.context.Entity['code'], self.context.Step['code'], self.context.Task['code'])
            item = self.menu_items.get('taskInfoLabel')
            if item:
                item.update(name, functools.partial(self.__print, name))
                self.__menu.register_command(item)

    def __pre_start(self):
        """
        引擎启动前执行：执行检查操作
        
        主要功能：
        1. 获取软件信息
        2. 加载软件包
        3. 检查版本兼容性
        
        Raises:
            ValueError: 版本不匹配时报错
        """
        if self.is_start:
            return
        self.__software = {
            'type': 'Software',
            'id': os.environ['%s_SOFTWARE_ID' % DCC_APP_CODE],
            'code': os.environ['%s_SOFTWARE_CODE' % DCC_APP_CODE],
            'version': os.environ['%s_SOFTWARE_VERSION' % DCC_APP_CODE],
            'engine_code': os.environ['%s_SOFTWARE_ENGINE_CODE' % DCC_APP_CODE],
        }
        software_package = self.__software['engine_code']
        self.__handle = importlib.import_module(software_package)
        version = self.__handle.api.current_version(self.__software['version'])
        if version:
            if str(self.__software['version']) != str(version):
                self.__handle.api.version_error(
                    str(self.__software['version']))
                # raise ValueError('软件版本不匹配')

    def __post_start(self):
        """
        引擎启动后执行：执行用户自定义的启动脚本
        
        功能：
        1. 获取软件启动脚本
        2. 执行脚本的main函数
        """
        if not self.__software:
            return
        ids_env = os.environ.get('%s_START_SCRIPT_IDS' % DCC_APP_CODE, '').split(';')
        ids = [int(i) for i in ids_env if i]
        if ids:
            _start_scripts = self.app._get_startup_scripts(ids)
            if _start_scripts:
                for script in _start_scripts:
                    hook = load_script(script, True)
                    if hasattr(hook, 'main'):
                        hook.main()

    def __print(self, name, *args, **kwargs):
        """
        打印函数，用于显示菜单项信息
        """
        print(name)

    @error_decorator
    def __start(self, has_software, menu):
        """
        引擎启动的核心实现
        
        Args:
            has_software (bool): 是否加载软件
            menu: 菜单实例
            
        功能：
        1. 初始化上下文
        2. 加载插件和脚本
        3. 注册菜单项
        """
        if self.is_start:
            return
        if has_software:
            self.__pre_start()
        _context_data = {}
        _context_data = self.app.get_task_context(TASK_ID)
        _context_data['Software'] = self.__software
        _context_data['User'] = {'type': 'User',
                                 'id': os.environ['%s_USER_ID' % DCC_APP_CODE],
                                 'code': os.environ['%s_USER' % DCC_APP_CODE]}

        if 'Step' in _context_data:
            self.__plugins_fileds['step'] = _context_data['Step']['code']
        if 'Entity' in _context_data:
            self.__plugins_fileds['entity_type'] = _context_data['Entity']['type']


        self.__menu = menu
        if _context_data and hasattr(_context_data, 'Task'):
            name = u'{} > {} > {}'.format(
                _context_data['Entity'].get('code', 'null'), _context_data['Step']['code'], _context_data['Task']['code'])
            _item = MenuItem(
                'taskInfoLabel',
                name,
                MenuType.Action,
                functools.partial(self.__print, name),
                'taskInfoLabel'
            )
            self.menu_items[_item.uuid] = _item
            if self.__menu:
                self.__menu.register_command(_item)
        if self.__software:
            self.__plugins_fileds['software'] = _context_data['Software']['code']
            plugin_ids_env = os.environ.get('%s_PLUGIN_IDS' % DCC_APP_CODE, '').split(';')
            script_ids_env = os.environ.get('%s_SCRIPT_IDS' % DCC_APP_CODE, '').split(';')
            plugin_ids = [int(i) for i in plugin_ids_env if i]
            script_ids = [int(i) for i in script_ids_env if i]
            if plugin_ids:
                _plugins = self.app._get_plugins_menus(plugin_ids)
                for plugin in _plugins:
                    # TODO 插件菜单项需要根据具体接口数据解析
                    if plugin['menus']:
                        for _action in plugin['menus']:
                            action_str = ''
                            if '{self}' in _action['command']:
                                action_str += 'import {};'.format(plugin['code'])
                                action_str += _action['command'].replace(
                                    '{self}', plugin['code'])
                            else:
                                action_str = _action['command']
                            label = _action['label']
                            # if os.environ.get("%s_LANGUAGE" % DCC_APP_CODE) != "zh-CN":
                            #     if _action.get("english_label"):
                            #         label = _action["english_label"]

                            _item = MenuItem(
                                plugin['code'],
                                label,
                                MenuType.Action,
                                action_str,
                                menu_group=_action['group'] if _action.get('group') else 'Custom',
                                extra_fields = _action.get('extra_fields', {})
                            )
                            self.menu_items[_item.uuid] = _item
                            if self.__menu:
                                self.__menu.register_command(_item)
            if script_ids:
                _scripts = self.app._get_scripts(script_ids)
                if _scripts:
                    if self.__menu:
                        _item = MenuItem(
                            menu_type=MenuType.Separator
                        )
                        self.menu_items[_item.uuid] = _item
                        self.__menu.register_command(_item)
                    
                    for script in _scripts:
                        try:
                            hook = load_script(script, True)
                        except:
                            traceback.print_exc()
                            continue
                        if script['menus']:
                            for _action in script['menus']:
                                label = _action['label']
                                # if os.environ.get("%s_LANGUAGE" % DCC_APP_CODE) != "zh-CN":
                                #     if _action.get("english_label"):
                                #         label = _action["english_label"]
                                _item = MenuItem(
                                    script['code'],
                                    label,
                                    MenuType.Action,
                                    functools.partial(self.__script_action,
                                                    hook, _action['command'], _context_data),
                                    menu_group=_action['group'] if _action.get('group') else 'Custom',
                                    extra_fields = _action.get('extra_fields', {})

                                )
                                self.menu_items[_item.uuid] = _item
                                if self.__menu:
                                    self.__menu.register_command(_item)
                        else:
                            if hasattr(hook, 'main'):
                                _item = MenuItem(
                                    script['code'],
                                    script.get('name', script['code']),
                                    MenuType.Action,
                                    hook.main
                                )
                                self.menu_items[_item.uuid] = _item
                                if self.__menu:
                                    self.__menu.register_command(_item)
            
        self.__is_start = True
        self.__context = Context(_context_data)
        self.__post_start()

    @staticmethod
    def __script_action(hook, command_str, context_data, *args, **kwargs):
        """
        执行脚本动作
        
        Args:
            hook: 脚本钩子
            command_str: 命令字符串
        """
        if '{self}' in command_str:
            command_str = command_str.replace('{self}', 'self')
        for _key in context_data:
            if '{%s}' % _key.lower() in command_str:
                command_str = command_str.replace('{%s}' % _key, context_data[_key].get('code', ''))
            elif '{%s.' % _key.lower() in command_str:
                for __key in context_data[_key]:
                    if '{%s.%s}' % (_key.lower(), __key) in command_str:
                        command_str = command_str.replace('{%s.%s}' % (_key.lower(), __key), context_data[_key][__key])
        self = hook
        exec(command_str)

    @property
    def plugins_fileds(self):
        """获取插件字段的副本"""
        return copy.deepcopy(self.__plugins_fileds)

    @property
    def project_template(self):
        """获取项目模板"""
        return PROJECT_TEMPLATE

    @property
    def context(self):
        """获取当前上下文"""
        return self.__context

    @property
    def app(self):
        """获取Kmoke实例"""
        return APP

    @property
    def handle(self):
        """获取软件包处理器"""
        return self.__handle

    @property
    def is_start(self):
        """获取引擎启动状态"""
        return self.__is_start

    @property
    def menu(self):
        """获取Kmoke主菜单实例"""
        return self.__menu