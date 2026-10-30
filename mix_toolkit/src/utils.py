#!/usr/bin/env python
# -*- coding: utf8 -*-
# title       : Kmoke工具函数模块
# description : 提供模块导入、单例模式和脚本加载等通用工具函数
# author      : 'ShenMeng'


import sys
import functools
import imp
import uuid
import os
import tempfile
import types
import linecache
from .logger import error_decorator


@error_decorator
def import_hook(hook_file):
    """
    通过文件路径导入Python模块
    
    将指定路径的Python文件作为模块导入，使用随机UUID作为模块名
    以避免命名冲突
    
    Args:
        hook_file (str): Python文件的完整路径
        
    Returns:
        module: 导入的模块对象
        
    Example:
        module = import_hook('/path/to/script.py')
    """
    return imp.load_source(uuid.uuid4().hex, hook_file)


def load_script(script, is_uuid=True, package=None):
    """
    从字典数据编译独立模块，可指定属性脚本的相对导入包。
    
    Args:
        script (dict): 包含脚本信息的字典，必须包含'content'键
        is_uuid (bool, optional): 是否使用UUID作为模块名，默认为True
        
    Returns:
        module: 加载的脚本模块对象
        
    不写临时脚本文件；加载失败由调用方记录状态，避免自动输出脚本内容。
    """
    name = uuid.uuid4().hex if is_uuid else script['code']
    filename = '<mix-script:{}:{}>'.format(script.get('code', name), name)
    content = script.get('content') or ''
    if not isinstance(content, str):
        raise TypeError('Script content must be text')
    module = types.ModuleType(name)
    module.__file__ = filename
    module.__package__ = package or ''
    linecache.cache[filename] = (len(content), None, content.splitlines(True), filename)
    previous = sys.modules.get(name)
    sys.modules[name] = module
    try:
        exec(compile(content, filename, 'exec'), module.__dict__)
    except BaseException:
        if previous is not None:
            sys.modules[name] = previous
        else:
            sys.modules.pop(name, None)
        linecache.cache.pop(filename, None)
        raise
    return module


def singleton(cls, *args, **kwargs):
    """
    单例模式装饰器
    
    确保一个类只有一个实例，如果实例已存在则返回该实例
    
    Args:
        cls: 要装饰的类
        *args: 可变位置参数
        **kwargs: 可变关键字参数
        
    Returns:
        function: 确保单例的装饰器函数
        
    Example:
        @singleton
        class MyClass:
            pass
    """
    instances = {}
    @functools.wraps(cls)
    def _singleton(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return _singleton


@error_decorator
def get_hook(name):
    """
    获取或重新加载指定名称的模块
    
    如果模块已存在，先卸载再重新导入，确保获取最新版本
    
    Args:
        name (str): 模块名称
        
    Returns:
        module: 导入的模块对象
        
    Note:
        这个函数会强制重新加载模块，即使它已经被导入
    """
    try:
        del sys.modules[name]  # 尝试卸载已存在的模块
    except:
        pass
    hook = __import__(name)  # 导入新的模块
    return hook
