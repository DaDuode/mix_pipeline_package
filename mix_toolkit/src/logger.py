#!/usr/bin/env python
# -*- coding: utf8 -*-
# title       : Kmoke日志工具模块
# description : 提供简化的日志记录接口和错误处理装饰器
# author      : ShenMeng


import functools
import traceback
from .__logger import DCCLogger


def log(msg):
    """
    记录调试级别的日志信息
    
    Args:
        msg  : 要记录的日志消息
    """
    DCCLogger.log(msg)


def error(msg):
    """
    记录错误级别的日志信息
    
    Args:
        msg (str): 要记录的错误消息
    """
    DCCLogger.error(msg)


def error_decorator(func):
    """
    错误处理装饰器

    用于捕获和记录函数执行过程中的异常，并重新抛出异常。
    自动记录完整的堆栈跟踪信息。
    
    Args:
        func (function): 要装饰的函数
        
    Returns:
        function: 装饰后的函数
        
    Example:
        @error_decorator
        def some_function():
           # 函数代码
           pass
    """
    
    @functools.wraps(func)
    def _wraper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            # 记录详细的错误堆栈信息
            DCCLogger.error(traceback.format_exc())
            # 重新抛出异常，保持原有的错误处理流程
            raise e
        return result
    return _wraper