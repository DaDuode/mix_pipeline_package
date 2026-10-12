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


@error_decorator
def load_script(script, is_uuid=True):
    """
    从字典数据加载并导入Python脚本
    
    将脚本内容写入临时文件并导入为模块，支持Python2和Python3
    
    Args:
        script (dict): 包含脚本信息的字典，必须包含'content'键
        is_uuid (bool, optional): 是否使用UUID作为模块名，默认为True
        
    Returns:
        module: 加载的脚本模块对象
        
    Note:
        - 脚本内容会被写入临时文件
        - 临时文件会在进程结束时自动清理
        - Python2和Python3使用不同的编码处理方式
    """
    # 生成模块名
    if is_uuid:
        _name = uuid.uuid4().hex
    else:
        _name = script['code']
        
    # 创建临时文件
    tf, tmpfile = tempfile.mkstemp(suffix=".data", prefix="tanktmp")
    if tf:
        os.close(tf)
        
    # 根据Python版本使用不同的编码处理
    if sys.version.startswith('2.'):
        with open(tmpfile, 'w') as f:
            f.write(script['content'].encode('utf-8'))
        return imp.load_source(uuid.uuid4().hex, tmpfile)
    else:
        with open(tmpfile, 'w', encoding='utf-8') as f:
            f.write(script['content'])
        return imp.load_source(_name, tmpfile)


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
