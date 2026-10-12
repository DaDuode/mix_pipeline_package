#!/usr/bin/env python
# -*- coding: utf8 -*-
# title       : YAML配置文件处理模块
# description : 提供YAML文件的读写、模板处理和引用解析功能
# author      :'ShenMeng'

import yaml
import copy
import os
import re


def yaml_load(content):
    """
    加载YAML内容
    
    Args:
        content: YAML格式的字符串内容
        
    Returns:
        dict: 解析后的YAML数据
    """
    if hasattr(yaml, 'FullLoader'):
        return yaml.load(content, Loader=yaml.FullLoader)
    else:
        return yaml.load(content)


def yaml_safe_load(file_path, load_type='rb'):
    """
    安全加载YAML文件
    
    Args:
        file_path (str): YAML文件路径
        load_type (str): 文件打开模式，默认为'rb'
        
    Returns:
        dict: 解析后的YAML数据
    """
    data = None
    with open(file_path, load_type) as f:
        data = yaml.safe_load(f)
    return data


def yaml_dump(file_path, data, dump_type='w', allow_unicode=False, default_flow_style=False):
    """
    将数据写入YAML文件
    
    Args:
        file_path (str): 目标文件路径
        data: 要写入的数据
        dump_type (str): 文件写入模式，默认为'w'
        allow_unicode (bool): 是否允许Unicode字符
        default_flow_style (bool): 是否使用默认流式风格
    """
    with open(file_path, dump_type) as f:
        yaml.safe_dump(data, f, default_flow_style=default_flow_style,
                       allow_unicode=allow_unicode)


def get_full_path(base_path, path):
    """
    获取文件的完整路径
    
    Args:
        base_path (str): 基础路径
        path (str): 相对路径或文件名
        
    Returns:
        str: 完整的文件路径，如果文件不存在则返回None
    """
    path = path.replace('\\', '/')
    base_path = base_path.replace('\\', '/')
    if not os.path.isfile(path):
        if path.startswith('./'):
            mat = re.match('^([./]*)(.*)', path)
            if mat:
                aa = mat.groups()[0]
                bb = mat.groups()[1]
                if aa == './':
                    path = os.path.join(base_path, bb).replace('\\', '/')
        elif path.startswith('../'):
            mat = re.match('^([../]*)(.*)', path)
            if mat:
                aa = mat.groups()[0]
                bb = mat.groups()[1]
                if aa.count('../')*3 == len(aa) and base_path.count('/') >= aa.count('../'):
                    for i in range(aa.count('../')):
                        base_path = os.path.dirname(base_path)
                    path = os.path.join(base_path, bb).replace('\\', '/')
        else:
            path = os.path.join(base_path, path).replace('\\', '/')

    if os.path.isfile(path):
        return path


def _resolve_refs_r(lookup_dict, data, is_template=False):
    """
    递归解析数据中的引用标记(@)并替换为实际值
    
    Args:
        lookup_dict (dict): 查找字典，用于解析引用
        data: 需要处理的数据
        is_template (bool): 是否为模板模式
        
    Returns:
        处理后的数据，引用被替换为实际值
        
    Raises:
        ValueError: 当引用未定义或配置错误时抛出
    """
    # default is no processing
    processed_val = data

    if isinstance(data, list):
        processed_val = []
        for x in data:
            processed_val.append(_resolve_refs_r(lookup_dict, x, is_template))

    elif isinstance(data, dict):
        processed_val = {}

        if '<@' in data:
            _data = _resolve_refs_r(lookup_dict, data['<@'], is_template)
            if not isinstance(_data, dict):
                raise ValueError("Error config: %s!" % data['<@'])
            for _k, _v in _data:
                _v = _data[_k]
                processed_val[_k] = _v
        keys = data.keys()
        for k in keys:
            if k != '<@':
                v = data[k]
                _rv = _resolve_refs_r(lookup_dict, v, is_template)
                if k in processed_val:
                    if type(processed_val[k]) != type(_rv):
                        processed_val[k] = _rv
                    else:
                        if isinstance(_rv, dict):
                            processed_val[k].update(_rv)
                        elif isinstance(_rv, list):
                            for i in _rv:
                                if i not in processed_val[k]:
                                    processed_val[k].append(i)
                        else:
                            processed_val[k] = _rv
                else:
                    processed_val[k] = _rv

    # elif isinstance(data, basestring) and data.startswith("@"):
    elif isinstance(data, str) and data.startswith("@"):
        if is_template:
            ref_token = data[1:].replace(os.sep, '/').split('/')[0]
            if ref_token not in lookup_dict:
                raise ValueError("Undefined Reference %s!" % ref_token)

            data = data.replace('@{}'.format(ref_token),
                                lookup_dict[ref_token])
            if data.startswith("@"):
                _resolve_refs_r(lookup_dict, data, is_template)
            else:
                processed_val = data
        else:
            ref_token = data[1:]
            if ref_token not in lookup_dict:
                raise ValueError("Undefined Reference %s!" % ref_token)
            processed_val = copy.deepcopy(lookup_dict[ref_token])

    return processed_val


def yaml_template_load(file_path):
    """
    加载并处理YAML模板文件
    
    Args:
        file_path (str): 模板文件路径
        
    Returns:
        dict: 处理后的模板数据，包含keys、paths和strings三个部分
    """
    def __parse(data):
        find_ref = False
        keys = data.keys()
        for k in keys:
            _value = data[k]
            if _value.startswith('@'):
                ref_key = _value[1:].replace(os.sep, '/').split('/')[0]
                if ref_key not in keys:
                    raise ValueError('未知应用@{}'.format(ref_key))
                _n_value = _value.replace('@{}'.format(ref_key), data[ref_key])
                data[k] = _n_value
                if _n_value.startswith('@'):
                    find_ref = True
        if find_ref:
            __parse(data)

    _data = parse_yaml_file(file_path)
    result_data = {}
    result_data['keys'] = copy.deepcopy(_data.get('keys', {}))
    paths_data = _data.get('paths', {})
    __parse(paths_data)
    result_data['paths'] = copy.deepcopy(paths_data)

    strings_data = _data.get('strings', {})
    __parse(strings_data)
    result_data['strings'] = copy.deepcopy(strings_data)

    # lockup_data = copy.deepcopy(paths_data)
    # includes_files = resolved_includes_files(file_path, _data)
    # if includes_files:
    # for _file in includes_files:
    # lockup_data.update(yaml_config_load(_file))
    # result_data['paths'] = _resolve_refs_r(lockup_data, paths_data, True)

    # lockup_data = copy.deepcopy(strings_data)
    # includes_files = resolved_includes_files(file_path, _data)
    # if includes_files:
    # for _file in includes_files:
    # lockup_data.update(yaml_config_load(_file))
    # result_data['strings'] = _resolve_refs_r(lockup_data, strings_data, True)

    return result_data


def yaml_config_load(file_path):
    """
    加载YAML配置文件，支持引用解析
    
    Args:
        file_path (str): 配置文件路径
        
    Returns:
        dict: 解析后的配置数据
    """
    _data = parse_yaml_file(file_path)
    result_data = _data['config']
    lockup_data = {}
    includes_files = resolved_includes_files(file_path, _data)
    if includes_files:
        for _file in includes_files:
            lockup_data.update(yaml_config_load(_file))
    return _resolve_refs_r(lockup_data, result_data)


def resolved_includes_files(file_path, data):
    """
    解析YAML文件中的include和includes指令
    
    Args:
        file_path (str): YAML文件路径
        data (dict): YAML数据
        
    Returns:
        list: 所有被包含文件的完整路径列表
    """
    includes = []
    resolved_includes = set()

    if 'include' in data:
        includes.append(data['include'])

    if 'includes' in data:
        includes.extend(data['includes'])

    for include in includes:
        path = get_full_path(os.path.dirname(file_path), include)
        if path:
            resolved_includes.add(path)
    return list(resolved_includes)


def yaml_include(loader, node):
    """
    YAML的!include指令处理器
    
    Args:
        loader: YAML加载器实例
        node: YAML节点
        
    Returns:
        包含文件的内容
    """
    file_path = os.path.dirname(loader.name)
    value = node.value
    if not os.path.isfile(value):
        value = os.path.join(file_path, value)
        if not os.path.isfile(value):
            return
    return yaml_config_load(value)


def parse_yaml_file(file):
    """
    解析YAML文件，支持!include指令
    
    Args:
        file (str): YAML文件路径
        
    Returns:
        dict: 解析后的YAML数据，如果文件不存在返回False
    """
    yaml.add_constructor("!include", yaml_include)
    if os.path.isfile(file):
        return yaml_safe_load(file)
    return False


def yaml_include_load(file_path):
    """
    加载包含!include指令的YAML文件
    
    Args:
        file_path (str): YAML文件路径
        
    Returns:
        dict: 处理后的YAML数据
    """
    def _include_str(file_path):
        """
        处理文件中的!include指令
        
        Args:
            file_path (str): 文件路径
            
        Returns:
            list: 处理后的文件行列表
        """
        result = []
        with open(file_path) as f:
            for _line in f.readlines():
                if '!include' in _line:
                    root = os.path.dirname(file_path)
                    _value = _line.split('!include')[-1]
                    _value = _value.strip()
                    for _s in ["'", '"']:
                        _value = _value.replace(_s, '')
                    _path = os.path.join(root, _value)

                    _lines = _include_str(_path)
                    result.append(_line.split('!include')[0] + '\n')
                    num = len(_line.split('!include')[0])
                    for _l in _lines:
                        result.append(' '*num+_l)
                else:
                    result.append(_line)
        return result
    return yaml_safe_load(''.join(_include_str(file_path)))
