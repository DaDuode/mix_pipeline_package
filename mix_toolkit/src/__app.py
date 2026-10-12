#!/usr/bin/env python
# -*- coding: utf8 -*-
# title       : Kmoke API接口模块
# description : 提供Kmoke API的单例封装和环境配置管理
# author      :'ShenMeng'


import functools
import os

import mix_api

def singleton_app(cls, *args, **kwargs):
    """
    Kmoke类的单例装饰器
    
    Args:
        cls: 要装饰的类
        *args: 可变位置参数
        **kwargs: 可变关键字参数
        
    Returns:
        function: 确保类只有一个实例的装饰器函数
    """
    instances = {}

    @functools.wraps(cls)
    def _singleton(*args, **kwargs):
        # 如果有参数，创建新实例
        if args or kwargs:
            instances[cls] = cls(*args, **kwargs)
        # 如果没有实例，创建新实例
        elif cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return _singleton

@singleton_app
class SingleAPP():
    """
    APP API的单例封装类
    
    主要功能：
    1. 提供API接口的统一访问点
    2. 确保全局只有一个实例
    """
    
    def __init__(self, url=None, api_key=None):
        if url and api_key:
            # 使用传入的参数初始化
            self.sdk = mix_api.MixSDK(url, api_key)
        else:
            # 使用环境变量初始化
            self.sdk = mix_api.MixSDK(
                os.getenv('DCC_BASE_URL'), os.getenv('DCC_API_KEY')
            )


def get_app(*args, **kwargs):
    """获取kmoke api实例
    Returns:
        Kmoke: 
    """
    return SingleAPP(*args, **kwargs).sdk