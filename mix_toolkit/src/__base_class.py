#!/usr/bin/env python
# -*- coding: utf8 -*-
# title       :
# description :
# author      :'ShenMeng'

import os

from .utils import import_hook
from .__io import yaml_load


class ApplicationBase(object):
    project_config_root = ''
    __settings = {}

    @property
    def hook_env_name(self):
        raise NotImplementedError

    @property
    def settings(self):
        return self.__settings

    @settings.setter
    def settings(self, value):
        if isinstance(value, dict):
            self.__settings = value
        else:
            self.__settings = {}

    @property
    def app_root(self):
        raise NotImplementedError

    def get_setting(self, name):
        if not name in self.settings:
            value = self.__get_app_info_value(name)
        else:
            value = self.settings.get(name)
            # if value.lower() == 'default':
            # value = self.__get_app_info_value(name)
        # if not value:
        #     raise IOError(u'配置文件错误，缺少{}的配置！'.format(name))
        return value

    def __get_app_info_value(self, key):
        # 读取插件默认配置
        key_value = ''
        _info_data = {}
        app_info_file = os.path.join(
            self.app_root, 'info.yml').replace(os.sep, '/')
        if not os.path.isfile(app_info_file):
            raise IOError(
                u'获取{}默认配置失败，默认配置文件不存在：{}'.format(key, app_info_file))

        _info_data = yaml_load(app_info_file)

        if not key in _info_data.get('config', {}):
            raise IOError(u'配置文件错误，缺少{}的配置！'.format(key))
        key_info = _info_data.get('config', {}).get(key, {})
        key_value = key_info.get('default_value')
        return key_value

    def get_hook(self, hook_name, hook_value):
        hook_file = self.get_hook_file_path(hook_name, hook_value)
        return import_hook(hook_file)

    def get_icon(self, icon_name):
        icon_file = ''
        if not icon_name:
            return icon_file
        icon_file = icon_name
        if icon_name.startswith('{self}'):
            # 插件自身hooks目录查询
            icon_root = os.path.join(
                self.app_root, 'icons').replace(os.sep, '/')
            icon_file = icon_name.replace(
                '{self}', icon_root).replace(os.sep, '/')
        elif not icon_name.startswith(':'):
            # 项目配置包icons目录查询
            if self.project_config_root:
                icon_root = os.path.join(
                    self.project_config_root, 'config', 'icons').replace(os.sep, '/')
                icon_file = os.path.join(
                    icon_root, icon_name).replace(os.sep, '/')
        return icon_file

    def get_config_value(self, config_value):
        if config_value.startswith('{self}'):
            config_value = config_value.replace(
                '{self}', self.app_root).replace(os.sep, '/')
        else:
            if self.project_config_root:
                config_value = os.path.join(
                    self.project_config_root, 'config', config_value).replace(os.sep, '/')
            else:
                config_value = os.path.join(
                    self.app_root, config_value).replace(os.sep, '/')
        return config_value

    def get_hook_file_path(self, hook_name, hook_value):
        """
        解析hook文件路径
        hook_name: 配置名
        hook_value: 配置值
            有四种情况：
            '{self}/../xxx.py' : 插件自身hooks文件里面查询
            '{env}/../xxx.py'  : 环境变量KMOKE_WORKFILE_HOOKS_PATH中查询
            'xxx.py'           : 项目配置hooks路径中查询，没有则查询环境变量，再次查询插件自身hooks文件夹
            'default'          : 读取插件根目录下的info.yml中相关的值，然后解析
        """
        hook_file = ''
        hook_root = ''
        if hook_value.startswith('{self}'):
            # 插件自身hooks目录查询
            hook_root = os.path.join(
                self.app_root, 'hooks').replace(os.sep, '/')
            hook_file = hook_value.replace(
                '{self}', hook_root).replace(os.sep, '/')
            if not os.path.isfile(hook_file):
                raise IOError(u'获取{}配置文件失败，文件不存在: {}'.format(
                    hook_name, hook_file))
        elif hook_value.startswith('{env}'):
            # 环境变量路径查询
            hook_root = os.getenv(self.hook_env_name)
            hook_file = hook_value.replace(
                '{env}', hook_root).replace(os.sep, '/')
            if not os.path.isfile(hook_file):
                raise IOError(u'获取{}配置文件失败，文件不存在: {}'.format(
                    hook_name, hook_file))
        elif hook_value == 'default':
            # 读取插件默认配置
            app_info_file = os.path.join(
                self.app_root, 'info.yml').replace(os.sep, '/')
            if not os.path.isfile(app_info_file):
                raise IOError(u'获取{}默认配置失败，默认配置文件不存在: {}'.format(
                    hook_name, app_info_file))
            error = None
            try:
                _info_data = yaml_load(app_info_file)
            except Exception as f:
                error = u'文件读取失败:　{}'.format(app_info_file)
            else:
                hook_info = _info_data.get('config', {}).get(hook_name, {})
                hook_value = hook_info.get('default_value')
            if error:
                raise IOError(error)
            if (not hook_value) or (hook_value == 'default'):
                raise IOError(u'获取{}默认配置失败!'.format(hook_name))
            hook_file = self.get_hook_file_path(hook_name, hook_value)
        else:
            # 项目配置包hooks目录查询
            # 如果没有指定项目配置目录则在环境变量中查询
            # 如果没有指定环境变量则在插件自身hooks目录中查询
            if self.project_config_root:
                hook_root = os.path.join(
                    self.project_config_root, 'config', 'hooks').replace(os.sep, '/')
            if not hook_root:
                hook_root = os.getenv(self.hook_env_name)
            if not hook_root:
                hook_root = os.path.join(
                    self.app_root, 'hooks').replace(os.sep, '/')
            hook_file = os.path.join(
                hook_root, hook_value).replace(os.sep, '/')
            if not os.path.isfile(hook_file):
                raise IOError(u'获取{}配置文件失败，文件不存在: {}'.format(
                    hook_name, hook_file))
        return hook_file
