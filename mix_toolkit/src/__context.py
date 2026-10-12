#!/usr/bin/env python
# -*- coding: utf8 -*-
# title       : 上下文管理模块
# description : 提供上下文数据的封装和管理功能
# author      :'ShenMeng'

import copy


class Context(object):
    """
    上下文管理类，用于封装和管理上下文数据
    
    主要功能：
    1. 管理和存储上下文数据
    2. 提供数据访问和更新接口
    3. 支持深拷贝和字典转换
    
    属性：
        __data (dict): 存储上下文数据的内部字典
    """
    
    def __init__(self, data={}):
        """
        初始化上下文实例
        
        Args:
            data (dict): 初始化数据字典，默认为空字典
        """
        self.__data = copy.deepcopy(data)  # 深拷贝确保数据独立性
        for _key in data:
            self.__dict__[_key] = data[_key]  # 将数据映射为实例属性

    def set_entity(self, entity_type, entity_data):
        """
        设置实体数据
        
        Args:
            entity_type (str): 实体类型
            entity_data (dict): 实体数据
        """
        self.__data[entity_type] = entity_data

    def update_key(self, key, data):
        """
        更新指定键的数据
        
        Args:
            key (str): 要更新的键名
            data: 新的数据值
        """
        self.__data[key] = copy.deepcopy(data)

    def has_key(self, key):
        """
        检查是否存在指定键
        
        Args:
            key (str): 要检查的键名
            
        Returns:
            bool: 如果键存在返回True，否则返回False
        """
        return (key in self.__data)

    def __repr__(self):
        """
        返回上下文对象的字符串表示
        
        Returns:
            str: 格式化的上下文数据字符串
        """
        msg = []
        for _key in self.__data:
            msg.append("  %s: %s" % (str(_key),  str(self.__data[_key])))
        return "<Ver Context: %s>" % ("\n".join(msg))

    def __deepcopy__(self, memo):
        """
        实现深拷贝操作
        
        Args:
            memo (dict): 用于存储已拷贝对象的字典
            
        Returns:
            Context: 当前上下文对象的深拷贝
        """
        ctx_copy = Context(copy.deepcopy(self.__data, memo))
        return ctx_copy

    def to_dict(self):
        """
        将上下文数据转换为字典
        
        Returns:
            dict: 上下文数据的深拷贝字典
        """
        return copy.deepcopy(self.__data)
