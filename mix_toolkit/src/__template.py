#!/usr/bin/env python
# -*- coding: utf8 -*-
# title       :
# description :
# author      :'ShenMeng'

import re
import copy
import sys
from .__setting import PROJECT_TEMPLATE, PROJECT_LOCATIONS


def get_path(path):
    """获取路径

    Args:
        path (str): 路径值

    Returns:
        str: 路径值
    """
    pass


class Template(object):
    """模板类，用于处理和管理路径模板

    该类用于处理包含变量占位符的路径模板，支持变量替换和路径验证。
    模板中的变量使用 {variable_name} 的格式定义。

    Attributes:
        _fields (dict): 存储模板变量的字典
        _path (str): 原始路径模板
        _location_name (str): 存储位置的名称
    """
    def __init__(self, path, location):
        """初始化

        Args:
            path (str): 路径模板值
            location (str): 存储空间名字

        Raises:
            ValueError: 如果location不存在
        """
        self._fields = {}
        self._path = path
        location = location.lower()

        if location not in PROJECT_LOCATIONS:
            raise ValueError(u"location不存在")
        self._location_name = location

    def __repr__(self):
        """获取类的字符串表示

        Returns:
            str: 类的字符串表示
        """
        return "<class %s: location:%s, path:%s>" % (self.__class__.__name__, self._location_name, self._path)

    @property
    def location_name(self):
        """获取存储位置名称

        Returns:
            str: 存储位置的名称
        """
        return self._location_name

    @property
    def location(self):
        """获取存储位置的完整路径

        Returns:
            str: 存储位置的完整路径
        """
        return PROJECT_LOCATIONS[self._location_name]

    @property
    def template_value(self):
        """获取原始路径模板值

        Returns:
            str: 原始路径模板字符串
        """
        return self._path

    @property
    def keys(self):
        """获取模板中所有的变量键名

        Returns:
            list: 模板中所有变量键名的列表，去重后的结果
        """
        return list(set(self.order_keys(self._path)))

    def order_keys(self, path):
        """按顺序提取路径中的所有变量键名

        Args:
            path (str): 要分析的路径模板

        Returns:
            list: 按顺序排列的变量键名列表
        """
        regex = r"(?<={)%s(?=})" % "[a-zA-Z_ 0-9\.]+"
        return re.findall(regex, path)

    def _apply_fields(self, fields):
        """应用变量值到模板中（内部方法）

        Args:
            fields (dict): 变量名和对应值的字典

        Returns:
            str: 替换变量后的路径

        Raises:
            ValueError: 当提供的变量不足以填充所有模板占位符时
        """
        keys = self.keys
        result_fields = {k: fields[k] for k in fields if k in keys}
        if len(list(result_fields.keys())) != len(keys):
            raise ValueError('提供的变量不足以填充所有模板占位符')
        return self._path.format(**result_fields).replace('\\', '/')

    def apply_fields(self, fields):
        """应用变量值并生成完整路径

        Args:
            fields (dict): 变量名和对应值的字典

        Returns:
            str: 包含存储位置的完整路径
        """
        _path = self._apply_fields(fields)
        return '{}/{}'.format(self.location, _path)

    @property
    def fields(self):
        """获取当前模板中已存储的变量值

        Returns:
            dict: 变量名和值的深拷贝
        """
        return copy.deepcopy(self._fields)

    def update_fields(self, fields):
        """更新模板变量值

        只更新模板中存在的变量键值对

        Args:
            fields (dict): 要更新的变量字典
        """
        keys = self.keys
        for _k in fields:
            if _k in keys:
                self._fields[_k] = fields[_k]

    def has_unknow_field(self):
        """检查是否包含未知字段

        Returns:
            bool: 如果包含未知字段返回True，否则返回False
        """
        template_keys_data = PROJECT_TEMPLATE['keys']
        for k in self.keys:
            if k not in template_keys_data:
                return True
            is_unknow = template_keys_data[k].get('unknow')
            if is_unknow:
                return True

    def get_fields(self, in_path):
        """从给定路径中提取变量值

        尝试从给定的路径中提取与模板匹配的变量值

        Args:
            in_path (str): 要分析的路径

        Returns:
            dict: 提取出的变量字典，如果路径不匹配则返回None
        """
        result = {}
        in_path = in_path.replace('\\', '/')
        _location_root = '{}/'.format(
            self.location.replace('\\', '/')).lower()
        if in_path.lower().startswith(_location_root):
            in_path = in_path[len(_location_root):]
        else:

            return
        _tmp_path = self._path
        if self._fields:
            for key in self._fields:
                if key == 'version':
                    continue
                _tmp_path = _tmp_path.replace('{%s}' % key, str(self._fields[key]))

        tmp_part = _tmp_path.split('/')
        tag_part = in_path.split('/')

        if len(tmp_part) != len(tag_part):
            return

        keys = self.keys
        # 遍历第一遍，将每部分只有一个key的解析出来
        for i, v in enumerate(tmp_part):
            _tag_part = tag_part[i]
            if '{' in v:
                if v.count('{') == 1:
                    if v.startswith('{') and v.endswith('}'):
                        _key = v[1:-1]
                        if _key in result:
                            if result[_key] != tag_part[i]:
                                return
                        else:
                            result[_key] = tag_part[i]
                    else:
                        _start_index = v.index('{')
                        _end_index = v.index('}')
                        _tmp_left_word = v[:_start_index]
                        _tmp_right_word = v[_end_index+1:]
                        _tmp_key = v[_start_index:_end_index+1]
                        _key = _tmp_key[1:-1]
                        _tag_end_index = _end_index-len(v)+1
                        _tag_left_word = _tag_part[:_start_index]
                        if _tag_end_index == 0:
                            _tag_right_word = ''
                            _tag_key = _tag_part[_start_index:]
                        else:
                            _tag_right_word = _tag_part[_tag_end_index:]
                            _tag_key = _tag_part[_start_index:_tag_end_index]
                        if _tmp_left_word == _tag_left_word and _tmp_right_word == _tag_right_word:
                            if _key in result:
                                if result[_key] != _tag_key:
                                    return
                                    # raise ValueError('Different parts of the same key "%s" have different values:["%s", "%s"]' % (
                                    #     _key, result[_key], _tag_key))
                            result[_key] = _tag_key
                        else:
                            return
                            # raise ValueError(
                            #     'Inconsistent constants between the original and target parts: "%s" <=>"%s"' % (v, _tag_part))
                else:
                    pass
            else:

                if v.lower() != tag_part[i].lower():
                    return

        # 遍历第二遍，将只有一个的key解析出来
        template_keys_data = PROJECT_TEMPLATE['keys']
        # if self._fields:
        #     _temp_keys = list(set(copy.deepcopy(keys)))
        #     for _k in _temp_keys:
        #         if _k in self._fields:
        #             if 'entity_type' in template_keys_data[_k]:
        #                 _tmp_path = _tmp_path.replace(
        #                     '{%s}' % _k, self._fields[_k])
        #     keys = self.order_keys(_tmp_path)
        self._fields.update(result)
        for key in result:
            _tmp_path = _tmp_path.replace('{%s}' % key, str(result[key]))

        pp = _tmp_path
        for k in keys:
            if k not in template_keys_data:

                return
            key_type = template_keys_data[k].get('type')
            if key_type == 'int':
                _tmp_path = _tmp_path.replace('{%s}' % k, '([0-9]*)')
            else:
                _tmp_path = _tmp_path.replace('{%s}' % k, '([a-zA-Z0-9_]*)')

        mat = re.match(_tmp_path, in_path)
        if not mat:

            return
        groups = mat.groups()
        order_keys = self.order_keys(pp)
        for _index, _key in enumerate(order_keys):
            self._fields[_key] = groups[_index]

        return copy.deepcopy(self._fields)
