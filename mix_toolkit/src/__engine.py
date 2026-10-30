#!/usr/bin/env python
# -*- coding: utf8 -*-
# title       : Kmoke引擎模块
# description : Kmoke工具包的核心引擎实现，负责软件启动、插件管理和上下文控制
# author      :'ShenMeng'


import traceback
import functools
import os
import json
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
            if isinstance(value, Context):
                self.__context = value
            elif isinstance(value, dict):
                self.__context = Context(value)
            return

        user_code = os.environ.get('%s_USER' % DCC_APP_CODE, 'artist')
        user_id = os.environ.get('%s_USER_ID' % DCC_APP_CODE, '1')

        if isinstance(value, Context):
            if self.__context and value.Task['id'] == self.__context.Task['id']:
                return

            self.update = False
            if not value.has_key('Software'):
                value.update_key('Software', self.__software)
            if not value.has_key('User'):
                value.update_key('User', {'type': 'User',
                                          'code': user_code,
                                          'id': user_id})
            self.__context = value

        elif isinstance(value, dict):
            if self.__context and value.get('Task', {}).get('id') == getattr(self.__context, 'Task', {}).get('id'):
                return
            value['Software'] = self.__software
            value['User'] = {'type': 'User',
                             'id': user_id,
                             'code': user_code}
            self.__context = Context(value)
        else:
            raise TypeError("context must be an instance of Context.")
        os.environ['%s_TASK_ID' % DCC_APP_CODE] = str(self.__context.Task['id'])
        if self.__handle:
            if hasattr(self.__handle, 'api'):
                if hasattr(self.__handle.api, 'set_env'):
                    self.__handle.api.set_env(copy.deepcopy(self.__context))
        self.__update_menu()

    def change_task(self, task_data):
        """在 DCC 内部热切换当前任务并刷新菜单状态 (Decision 1A)
        支持传入完整 context 字典/Context 对象，或者单一 task 字典 (包含 id, entity_name, step, task_name)
        """
        if isinstance(task_data, (dict, Context)):
            if isinstance(task_data, dict) and 'Task' not in task_data:
                current_ctx = self.__context.to_dict() if (self.__context and hasattr(self.__context, 'to_dict')) else (self.__context or {})
                proj = current_ctx.get('Project', {'id': os.environ.get('%s_PROJECT_ID' % DCC_APP_CODE, '1'), 'code': os.environ.get('%s_PROJECT_CODE' % DCC_APP_CODE, 'DefaultProject')})
                ent_name = task_data.get('entity_name') or task_data.get('code') or 'DefaultEntity'
                step_name = task_data.get('step') or 'General'
                task_name = task_data.get('task_name') or task_data.get('code') or 'DefaultTask'
                task_id = str(task_data.get('id', '1'))

                full_ctx = {
                    'Project': proj,
                    'Entity': {'id': str(task_data.get('entity_id', '1')), 'code': ent_name, 'type': 'Asset' if task_data.get('module') != 'scope' else 'Shot'},
                    'Step': {'id': str(task_data.get('step_id', '1')), 'code': step_name},
                    'Task': {'id': task_id, 'code': task_name, 'artist': task_data.get('artist', '')}
                }
                self.set_context(full_ctx)
                return True
            else:
                self.set_context(task_data)
                return True
        return False

    def get_task_label(self):
        """获取格式化后的任务信息标签 (Decision 1B & 3A)"""
        if not self.context:
            return ""
        ctx_data = self.context.to_dict() if hasattr(self.context, 'to_dict') else self.context
        ent = ctx_data.get('Entity', {}) if isinstance(ctx_data, dict) else getattr(ctx_data, 'Entity', {})
        stp = ctx_data.get('Step', {}) if isinstance(ctx_data, dict) else getattr(ctx_data, 'Step', {})
        tsk = ctx_data.get('Task', {}) if isinstance(ctx_data, dict) else getattr(ctx_data, 'Task', {})

        ent_code = ent.get('code', 'null') if isinstance(ent, dict) else getattr(ent, 'code', 'null')
        stp_code = stp.get('code', '') if isinstance(stp, dict) else getattr(stp, 'code', '')
        tsk_code = tsk.get('code', '') if isinstance(tsk, dict) else getattr(tsk, 'code', '')

        return u'👤 [{} > {} > {}]'.format(ent_code, stp_code, tsk_code)

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
        if self.context and (hasattr(self.context, 'Task') or (hasattr(self.context, 'has_key') and self.context.has_key('Task'))):
            ctx_data = self.context.to_dict() if hasattr(self.context, 'to_dict') else self.context
            ent = ctx_data.get('Entity', {}) if isinstance(ctx_data, dict) else getattr(ctx_data, 'Entity', {})
            stp = ctx_data.get('Step', {}) if isinstance(ctx_data, dict) else getattr(ctx_data, 'Step', {})
            tsk = ctx_data.get('Task', {}) if isinstance(ctx_data, dict) else getattr(ctx_data, 'Task', {})
            
            ent_code = ent.get('code', 'null') if isinstance(ent, dict) else getattr(ent, 'code', 'null')
            stp_code = stp.get('code', '') if isinstance(stp, dict) else getattr(stp, 'code', '')
            tsk_code = tsk.get('code', '') if isinstance(tsk, dict) else getattr(tsk, 'code', '')
            
            name = u'👤 [{} > {} > {}]'.format(ent_code, stp_code, tsk_code)
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
        sw_code = os.environ.get('%s_SOFTWARE_CODE' % DCC_APP_CODE, DCC_APP_CODE.lower())
        self.__software = {
            'type': 'Software',
            'id': os.environ.get('%s_SOFTWARE_ID' % DCC_APP_CODE, '1'),
            'code': sw_code,
            'version': os.environ.get('%s_SOFTWARE_VERSION' % DCC_APP_CODE, 'latest'),
            'engine_code': os.environ.get('%s_SOFTWARE_ENGINE_CODE' % DCC_APP_CODE, 'mix_%s' % sw_code),
        }
        software_package = self.__software['engine_code']
        self.__handle = importlib.import_module(software_package)
        req_ver = str(self.__software.get('version', '')).strip()
        if req_ver and req_ver.lower() not in ('latest', 'default', 'none') and hasattr(self.__handle, 'api'):
            adapter = self.__handle.api
            matches = adapter.version_matches(req_ver) if hasattr(adapter, 'version_matches') else str(adapter.current_version(req_ver)) == req_ver
            if not matches:
                self.__handle.api.version_error(req_ver)

    def __post_start(self):
        """
        引擎启动后执行：执行用户自定义的启动脚本
        
        功能：
        1. 获取软件启动脚本
        2. 执行脚本的main函数
        """
        if not self.__software:
            return
        _start_scripts = []
        ids_env = os.environ.get('%s_START_SCRIPT_IDS' % DCC_APP_CODE, '').split(';')
        ids = [int(i) for i in ids_env if i and str(i).isdigit()]
        if ids and self.app:
            try:
                remote_scripts = self.app._get_startup_scripts(ids)
                if remote_scripts:
                    _start_scripts.extend(remote_scripts)
            except Exception:
                pass
        inline_json = os.environ.get('%s_STARTUP_SCRIPTS_JSON' % DCC_APP_CODE, '')
        if inline_json:
            try:
                inline_scripts = json.loads(inline_json)
                if isinstance(inline_scripts, list):
                    existing_codes = {s.get('code') for s in _start_scripts if isinstance(s, dict)}
                    for s in inline_scripts:
                        if isinstance(s, dict) and s.get('content') and s.get('code') not in existing_codes:
                            _start_scripts.append(s)
            except Exception:
                pass
        for script in _start_scripts:
            try:
                hook = load_script(script, True)
                if hasattr(hook, 'main') and callable(hook.main):
                    hook.main()
            except Exception:
                traceback.print_exc()

    def __print(self, name, *args, **kwargs):
        """
        打印函数，用于显示菜单项信息
        """
        try:
            print(name)
        except UnicodeEncodeError:
            print(name.encode('utf-8', errors='replace').decode('ascii', errors='ignore'))

    def __resolve_initial_context(self):
        """从远程服务、预设上下文或环境变量回退构建完整任务上下文"""
        _context_data = {}
        if self.app and TASK_ID:
            try:
                res = self.app.get_task_context(TASK_ID)
                if isinstance(res, dict) and 'Task' in res:
                    _context_data = res
            except Exception:
                pass

        if not _context_data and self.__context:
            _context_data = self.__context.to_dict() if hasattr(self.__context, 'to_dict') else copy.deepcopy(self.__context)

        if not _context_data or 'Task' not in _context_data:
            ctx_json = os.environ.get('%s_CONTEXT_JSON' % DCC_APP_CODE, '')
            if ctx_json:
                try:
                    parsed = json.loads(ctx_json)
                    if isinstance(parsed, dict) and 'Task' in parsed:
                        _context_data = parsed
                except Exception:
                    pass

        if not _context_data or 'Task' not in _context_data:
            _context_data = {
                'Project': {
                    'id': os.environ.get('%s_PROJECT_ID' % DCC_APP_CODE, '1'),
                    'code': os.environ.get('%s_PROJECT_CODE' % DCC_APP_CODE, 'DefaultProject')
                },
                'Entity': {
                    'id': os.environ.get('%s_ENTITY_ID' % DCC_APP_CODE, '1'),
                    'code': os.environ.get('%s_ENTITY_CODE' % DCC_APP_CODE, 'DefaultEntity'),
                    'type': os.environ.get('%s_ENTITY_TYPE' % DCC_APP_CODE, 'Asset')
                },
                'Step': {
                    'id': os.environ.get('%s_STEP_ID' % DCC_APP_CODE, '1'),
                    'code': os.environ.get('%s_STEP_CODE' % DCC_APP_CODE, 'General')
                },
                'Task': {
                    'id': os.environ.get('%s_TASK_ID' % DCC_APP_CODE, '1'),
                    'code': os.environ.get('%s_TASK_CODE' % DCC_APP_CODE, 'DefaultTask')
                }
            }
        return _context_data

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
        _context_data = self.__resolve_initial_context()
        _context_data['Software'] = self.__software
        _context_data['User'] = {
            'type': 'User',
            'id': os.environ.get('%s_USER_ID' % DCC_APP_CODE, '1'),
            'code': os.environ.get('%s_USER' % DCC_APP_CODE, 'artist')
        }

        if 'Step' in _context_data:
            self.__plugins_fileds['step'] = _context_data['Step'].get('code', '')
        if 'Entity' in _context_data:
            self.__plugins_fileds['entity_type'] = _context_data['Entity'].get('type', 'Asset')

        self.__menu = menu
        if _context_data and ('Task' in _context_data or hasattr(_context_data, 'Task')):
            ent = _context_data['Entity'] if isinstance(_context_data, dict) else _context_data.Entity
            stp = _context_data['Step'] if isinstance(_context_data, dict) else _context_data.Step
            tsk = _context_data['Task'] if isinstance(_context_data, dict) else _context_data.Task
            name = u'👤 [{} > {} > {}]'.format(
                ent.get('code', 'null') if isinstance(ent, dict) else getattr(ent, 'code', 'null'),
                stp.get('code', '') if isinstance(stp, dict) else getattr(stp, 'code', ''),
                tsk.get('code', '') if isinstance(tsk, dict) else getattr(tsk, 'code', '')
            )
            _item = MenuItem(
                'taskInfoLabel',
                name,
                MenuType.Action,
                functools.partial(self.__print, name),
                'taskInfoLabel',
                menu_group='Root'
            )
            self.menu_items[_item.uuid] = _item
            if self.__menu:
                self.__menu.register_command(_item)
                _sep = MenuItem('taskInfoSep', '', MenuType.Separator, None, 'taskInfoSep', menu_group='Root')
                self.menu_items[_sep.uuid] = _sep
                self.__menu.register_command(_sep)
        if self.__software:
            self.__plugins_fileds['software'] = _context_data['Software'].get('code', '')
            plugin_ids_env = os.environ.get('%s_PLUGIN_IDS' % DCC_APP_CODE, '').split(';')
            script_ids_env = os.environ.get('%s_SCRIPT_IDS' % DCC_APP_CODE, '').split(';')
            plugin_ids = [int(i) for i in plugin_ids_env if i and str(i).isdigit()]
            script_ids = [int(i) for i in script_ids_env if i and str(i).isdigit()]

            _plugins = []
            if plugin_ids and self.app:
                try:
                    res_plugins = self.app._get_plugins_menus(plugin_ids)
                    if res_plugins:
                        _plugins.extend(res_plugins)
                except Exception:
                    pass

            plugin_menus_json = os.environ.get('%s_PLUGIN_MENUS_JSON' % DCC_APP_CODE, '')
            if plugin_menus_json:
                try:
                    env_plugins = json.loads(plugin_menus_json)
                    if isinstance(env_plugins, list):
                        existing_codes = {p.get('code') for p in _plugins if isinstance(p, dict)}
                        for ep in env_plugins:
                            if isinstance(ep, dict) and ep.get('code') not in existing_codes:
                                _plugins.append(ep)
                except Exception:
                    pass

            for plugin in _plugins:
                if plugin.get('menus'):
                    for _action in plugin['menus']:
                        action_str = ''
                        cmd_tpl = _action.get('command', '')
                        if '{self}' in cmd_tpl:
                            action_str += 'import {};'.format(plugin['code'])
                            action_str += cmd_tpl.replace('{self}', plugin['code'])
                        else:
                            action_str = cmd_tpl
                        label = _action.get('label', plugin['code'])

                        _item = MenuItem(
                            plugin['code'],
                            label,
                            MenuType.Action,
                            action_str,
                            menu_group=_action.get('group') if _action.get('group') else 'Custom',
                            extra_fields=_action.get('extra_fields', {})
                        )
                        self.menu_items[_item.uuid] = _item
                        if self.__menu:
                            self.__menu.register_command(_item)

            if script_ids and self.app:
                try:
                    _scripts = self.app._get_scripts(script_ids)
                except Exception:
                    _scripts = []
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
                        except Exception:
                            traceback.print_exc()
                            continue
                        if script.get('menus'):
                            for _action in script['menus']:
                                label = _action['label']
                                _item = MenuItem(
                                    script['code'],
                                    label,
                                    MenuType.Action,
                                    functools.partial(self.__script_action,
                                                    hook, _action['command'], _context_data),
                                    menu_group=_action['group'] if _action.get('group') else 'Custom',
                                    extra_fields=_action.get('extra_fields', {})
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
            if not isinstance(context_data[_key], dict):
                continue
            if '{%s}' % _key.lower() in command_str or '{%s}' % _key in command_str:
                code_val = str(context_data[_key].get('code', ''))
                command_str = command_str.replace('{%s}' % _key.lower(), code_val)
                command_str = command_str.replace('{%s}' % _key, code_val)
            if '{%s.' % _key.lower() in command_str:
                for __key in context_data[_key]:
                    if '{%s.%s}' % (_key.lower(), __key) in command_str:
                        command_str = command_str.replace('{%s.%s}' % (_key.lower(), __key), str(context_data[_key][__key]))
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
