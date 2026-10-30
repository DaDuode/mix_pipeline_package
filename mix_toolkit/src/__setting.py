#!/usr/bin/env python
# -*- coding: utf8 -*-
# title       : 配置模块
# description : Kmoke工具包的配置和路径管理模块
# author      :'ShenMeng'


import os
import re

from .__io import yaml_load
from .__app import get_app
from . import logger
import traceback
import json

def parse_path(key, paths):
    """
    解析配置中的路径引用，处理@语法的路径引用
    
    参数:
        key (str): 需要解析的路径键名
        paths (dict): 包含路径映射的字典
        
    返回:
        str: 解析后的完整路径，所有@引用都被替换为实际路径
        
    示例:
        如果paths = {'root': '/data', 'sub': '@root/subdir'}
        parse_path('sub', paths) 将返回 '/data/subdir'
    """
    path = paths[key]
    if path.startswith('@'):
        results = re.findall('(@([a-zA-Z0-9_]*)/)', path)
        for _data in results:
            path = path.replace(_data[0], parse_path(_data[-1], paths)+'/')
        paths[key] = path
    return paths[key]


def format_template(template):
    """
    格式化和标准化模板配置:
    1. 处理所有路径引用
    2. 将路径键转换为小写
    3. 按位置组织路径
    
    参数:
        template (dict): 包含paths部分的模板配置字典
        
    返回:
        dict: 处理后的模板，包含解析后的路径和标准化的结构
    """
    result = {}
    for _location in template['paths']:
        for _key in template['paths'][_location]:
            _value = parse_path(_key, template['paths'][_location])
            result.setdefault(_location, {})[_key.lower()] = _value
    template['paths'] = result
    return template


# 全局配置初始化
try:
    # 从环境变量获取Kmoke配置
    DCC_APP_CODE = (os.environ.get('MSC_DCC_APP_CODE') or os.environ.get('DCC_APP_CODE') or 'MIX').upper()
    SOFTWARE_ID = os.environ.get('%s_SOFTWARE_ID' % DCC_APP_CODE)  # 软件唯一标识符
    TOOL_ID = os.environ.get('%s_TOOL_ID' % DCC_APP_CODE, 0)         # 工具标识符
    PROJECT_ID = os.environ.get('%s_PROJECT_ID' % DCC_APP_CODE)    # 当前项目标识符
    TASK_ID = os.environ.get('%s_TASK_ID' % DCC_APP_CODE)    # 当前项目标识符
    
    # 初始化Kmoke实例
    APP = None
    if os.getenv('DCC_BASE_URL'):
        try:
            APP = get_app()
        except Exception as err:
            logger.error("Failed to initialize APP: %s" % err)
    
    # 项目模板配置
    PROJECT_TEMPLATE = {}
    if PROJECT_ID and APP:
        try:
            PROJECT_TEMPLATE = format_template(
                yaml_load(APP._get_file_path_template()['content']))
        except Exception as err:
            logger.error("Failed to load project template: %s" % err)
    
    # 项目位置映射（代码转小写）
    LOCATIONS_DATA = {}
    PROJECT_LOCATIONS = {}
    storages_str = os.environ.get('%s_STORAGES' % DCC_APP_CODE)
    location_datas = json.loads(storages_str) if storages_str else []
    if location_datas and isinstance(location_datas, list):
        for location_data in location_datas:
            if location_data and isinstance(location_data, dict):
                if APP:
                    try:
                        location_data['samba_info'] = APP._get_storage_samba(location_data['code'].lower())
                    except Exception:
                        pass
                LOCATIONS_DATA[location_data['code'].lower()] = location_data
                PROJECT_LOCATIONS[location_data['code'].lower()] = location_data['path']

    # 版本和变体的键名定义
    VERSION_KEY = 'version'
    VARIANT_KEY = 'variant'
    
except Exception as e:
    logger.error(traceback.format_exc())
