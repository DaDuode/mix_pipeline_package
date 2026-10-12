#!/usr/bin/env python
# -*- coding: utf8 -*-

import os
import re
import getpass
import shutil
import traceback
import functools
import datetime
import yaml
from .utils import load_script
from .logger import error_decorator

from .__engine import Engine
from .__template import Template
from .__context import Context
from .__app import get_app
from .__setting import SOFTWARE_ID, PROJECT_TEMPLATE, PROJECT_LOCATIONS, LOCATIONS_DATA, VERSION_KEY, VARIANT_KEY, PROJECT_ID, APP, TOOL_ID, DCC_APP_CODE

ENGINE_INSTANCE = None
# Classes first
class _IncludeLoader(yaml.Loader):
    """
    YAML文件包含加载器
    
    继承自yaml.Loader，用于处理YAML文件中的!include标签。
    支持从插件配置中加载和包含其他YAML文件的内容。
    
    Attributes:
        plugin (str): 插件名称，用于定位配置文件
        
    Example:
        yaml_content = '''
        config:
          !include other_config.yaml
        '''
        data = yaml.load(yaml_content, _IncludeLoader)
    """
    plugin = ''  # 插件名称，用于查找配置文件

    def __init__(self, *args, **kwargs):
        """初始化加载器，注册!include构造器"""
        super(_IncludeLoader, self).__init__(*args, **kwargs)
        self.add_constructor('!include', self._include)

    def _include(self, loader, node):
        """
        处理!include标签的构造器方法
        
        Args:
            loader: YAML加载器实例
            node: 当前处理的YAML节点
            
        Returns:
            dict: 解析后的YAML数据
            
        Raises:
            ValueError: 当指定的配置文件不存在时抛出
        """
        value = loader.construct_scalar(node)  # 获取include标签的值
        value = format_value(value).lower().strip()  # 格式化配置文件名
        config_data = APP._get_plugin_config(self.plugin, value)  # 获取配置
        if not config_data:
            raise ValueError(
                '"{0}" config "{1}" not exists!'.format(self.plugin, value))
        return yaml.load(config_data['content'], _IncludeLoader)  # 递归加载配置


def get_samba_path(in_path, location):
    """获取Samba路径
    路径规则：//{ip}/{share}/{samba_sub}/{relative_path}
    """
    
    in_path = in_path.replace('\\', '/')
    _location_data = LOCATIONS_DATA.get(location.lower())
    if not _location_data:
        return
    samba_info = _location_data.get('samba_info')
    if not samba_info:
        return
    samba_sub = samba_info.get('samba_sub_path')
    if not samba_sub:
        return
    samba_sub = samba_sub.replace('\\', '/')
    if samba_sub.endswith('/'):
        samba_sub = samba_sub[:-1]
    if samba_sub.startswith('/'):
        samba_sub = samba_sub[1:]
    _location_path = _location_data['path'].replace('\\', '/')
    if not in_path.lower().startswith(_location_path.lower()):
        return
    relative_path = in_path[len(_location_path):].replace('\\', '/')
    if relative_path.startswith('/'):
        relative_path = relative_path[1:]
    return '//{ip}/{share}/{samba_sub}/{relative_path}'.format(
        ip=samba_info['ip'],
        share=samba_info['share'],
        samba_sub=samba_sub,
        relative_path=relative_path)

# Functions in alphabetical order
def change_task(id):
    """切换任务
    
    根据任务ID切换当前工作任务。会获取任务的上下文信息并更新当前引擎的上下文。
    
    Args:
        id (int): 任务ID，用于标识要切换到的目标任务
        
    Example:
        >>> change_task(123) # 切换到ID为123的任务
        
    注意:
        - 需要确保传入的任务ID是有效的
        - 切换任务会影响当前工作环境的上下文
    """
    engine = get_current_engine()
    ctx_data = APP.get_task_context(id)
    engine.set_context(ctx_data)

def check_fields_all_by_context(fields, context):
    """检查所有字段是否与上下文匹配
    
    检查给定的字段值是否完全匹配当前上下文中的对应值。
    只有当所有字段都匹配时才返回True。
    
    Args:
        fields (dict): 要检查的字段字典，键为字段名，值为期望值
        context (Context): 当前上下文对象，包含实际的字段值
        
    Returns:
        bool: 如果所有字段都匹配返回True，否则返回None
        
    Example:
        >>> ctx = Context({'Asset': {'name': 'prop_01'}})
        >>> check_fields_all_by_context({'asset_name': 'prop_01'}, ctx)
        True
        >>> check_fields_all_by_context({'asset_name': 'prop_02'}, ctx)
        None
        
    注意:
        - 字段必须在PROJECT_TEMPLATE['keys']中定义
        - 如果字段未定义entity_type，返回None
        - 任何字段不匹配都返回None
    """
    context_data = context.to_dict()
    keys_config = PROJECT_TEMPLATE['keys']

    for key in fields:
        if key not in keys_config:
            return
        value = fields[key]
        k_data = keys_config[key]
        if k_data.get('entity_type'):
            field_name = k_data['field_name']
            field_entity = k_data['entity_type']
            if context_data[field_entity][field_name] != value:
                return
        else:
            return
    return True

def check_fields_by_context(fields, context):
    """检查字段是否与上下文匹配
    
    检查给定的字段值是否匹配当前上下文中的对应值。
    只要有一个字段不匹配就返回None。
    
    Args:
        fields (dict): 要检查的字段字典，键为字段名，值为期望值
        context (Context): 当前上下文对象，包含实际的字段值
        
    Returns:
        bool: 如果所有字段都匹配返回True，否则返回None
        
    Example:
        >>> ctx = Context({'Asset': {'name': 'prop_01'}})
        >>> check_fields_by_context({'asset_name': 'prop_01'}, ctx)
        True
        >>> check_fields_by_context({'asset_name': 'prop_02'}, ctx)
        None
        
    注意:
        - 字段必须在PROJECT_TEMPLATE['keys']中定义
        - 如果字段未定义entity_type，返回None
    """
    context_data = context.to_dict()
    keys_config = PROJECT_TEMPLATE['keys']

    for key in fields:
        if key not in keys_config:
            return
        value = fields[key]
        k_data = keys_config[key]
        if k_data.get('entity_type'):
            field_name = k_data['field_name']
            field_entity = k_data['entity_type']
            if context_data[field_entity][field_name] != value:
                return
    return True

def decorator_primary_publish(func):
    def wrapper(scene_path, publish_path, publish_type, publish_template, fields, engine, comment, thumbnail, *args, **kwargs):
        """主发布装饰器
        
        装饰主发布函数，处理文件发布流程，包括路径处理、执行发布、错误处理和缩略图处理。
        
        Args:
            scene_path (str): 场景文件路径
            publish_path (str): 发布文件目标路径
            publish_type (str): 发布类型
            publish_template (str): 发布模板名称
            fields (dict): 发布相关的字段信息
            engine (Engine): 引擎对象
            comment (str): 发布说明
            thumbnail (str): 缩略图路径
            *args: 额外的位置参数
            **kwargs: 额外的关键字参数
            
        Returns:
            dict: 包含发布信息的参数字典
            
        Raises:
            IOError: 发布过程中出现错误时抛出
            
        注意:
            - 会自动处理临时发布路径
            - 会处理缩略图的复制和上传
            - 支持SMB方式发布
        """
        publish_type = format_value(publish_type)
        tmp_publish_path = get_tmp_publish_path(publish_path, publish_template)
        try:
            exrea_files = func(scene_path, tmp_publish_path, publish_type, publish_template,
                               fields, engine, comment, thumbnail, *args, **kwargs)
        except Exception as e:
            traceback.print_exc()
            raise IOError("Primary File Publish Error: %s" % e)
        parms = register_publish(publish_template, publish_path, publish_type, fields,
                                 engine.context, comment, thumbnail, tmp_publish_path, '', exrea_files)
        if os.path.isfile(thumbnail):
            # TODO
            try:
                work_thumbnail = '{}.png'.format(
                    os.path.splitext(scene_path)[0])
                publish_thumbnail = '{}.png'.format(
                    os.path.splitext(tmp_publish_path)[0])
                shutil.copy(thumbnail, work_thumbnail)
                
                if os.environ.get('DCC_PUBLISH_TYPE', '').lower() == 'smb':
                    from .samba import Samba
                    _publish_thumbnail = '{}.png'.format(
                        os.path.splitext(publish_path)[0])
                    
                    remote_path = get_samba_path(_publish_thumbnail, publish_template.location_name)
                    if not remote_path:
                        raise IOError('Can not get remote path: %s' % remote_path)
                    # ip = get_remote_ip(remote_path)
                    samba_info = LOCATIONS_DATA[publish_template.location_name.lower()]['samba_info']
                    with Samba(
                        samba_info['ip'], 
                        samba_info['account'], 
                        samba_info['password'],
                        share = samba_info['share'],
                        domain = samba_info['domain']) as smb:
                        smb.upload_file(thumbnail, remote_path)
                else:
                    shutil.copy(thumbnail, publish_thumbnail)
            except:
                pass

            # _data = app.upload_file(thumbnail, 'Task')
            # APP.update('Task', engine.context.Task['id'], {
            #     'thumbnail': _data.get('url', '') if isinstance(_data, dict) else ''})

        return parms
    return wrapper


    

def decorator_secondary_publish(func):
    """数据发布装饰器"""
    def wrapper(task, fields, primary_path, engine, comment, thumbnail_path, *args, **kwargs):
        """数据发布装饰器函数的包装器
        
        Args:
            task (dict): 任务信息字典
            fields (dict): 字段信息字典 
            primary_path (str): 主要文件路径
            engine (object): 引擎对象
            comment (str): 发布注释
            thumbnail_path (str): 缩略图路径
            *args: 可变位置参数
            **kwargs: 可变关键字参数
            
        Returns:
            dict: 包含发布信息的字典
            
        Raises:
            ValueError: 当找不到指定的模板时抛出
            IOError: 当发布失败时抛出
        """
        publish_template_name = format_value(
            task['output']['publish_template'])
        template = get_template_by_name(publish_template_name)
        if not template:
            raise ValueError('can not find template by name : "%s"' %
                             publish_template_name)
        publish_fields = get_template_fields_from_context(
            template, engine.context)
        publish_fields.update(fields)
        publish_path = template.apply_fields(publish_fields).replace('\\', '/')
        tmp_publish_path = get_tmp_publish_path(publish_path, template)

        try:
            exrea_files = func(task, publish_fields, primary_path, engine,
                               comment, thumbnail_path, tmp_publish_path, template.location_name, *args, **kwargs)
        except Exception as e:
            traceback.print_exc()
            raise IOError("Publish Error %s: %s" % (task['output']['name'], e))
        publish_type = format_value(task['output']["publish_type"])
        return register_publish(template, publish_path, publish_type, publish_fields, engine.context, comment, thumbnail_path, tmp_publish_path, primary_path, exrea_files)
    return wrapper


def decorator_publish_template_fields(func):
    def wrapper(task, fields, primary_path, engine, comment, thumbnail_path, *args, **kwargs):
        """装饰器函数，用于处理发布模板字段
        
        Args:
            task (dict): 任务信息字典
            fields (dict): 字段信息字典
            primary_path (str): 主要文件路径
            engine (object): 引擎对象
            comment (str): 发布注释
            thumbnail_path (str): 缩略图路径
            *args: 可变位置参数
            **kwargs: 可变关键字参数
            
        Returns:
            dict: 包含发布信息的字典
            
        Raises:
            ValueError: 当找不到指定的模板时抛出
            IOError: 当发布失败时抛出
        """
        publish_template_name = format_value(
            task['output']['publish_template'])
        template = get_template_by_name(publish_template_name)
        if not template:
            raise ValueError('can not find template by name : "%s"' %
                             publish_template_name)
        publish_fields = get_template_fields_from_context(
            template, engine.context)
        publish_fields.update(fields)

        publish_path = template.apply_fields(publish_fields).replace('\\', '/')
        publish_root = template.location.replace('\\', '/')
        transfer_root = get_location_root('transfer').replace('\\', '/')
        _transfer_path = transfer_root + publish_path[len(publish_root):]

        publish_folder = os.path.dirname(_transfer_path)
        if not os.path.isdir(publish_folder):
            os.makedirs(publish_folder)
        try:
            func(task, publish_fields, primary_path, engine,
                 comment, thumbnail_path, _transfer_path, template.location_name, *args, **kwargs)
        except Exception as e:
            traceback.print_exc()
            raise IOError("发布失败 %s: %s" % (task['output']['name'], e))
        publish_type = format_value(task['output']["publish_type"])
        return register_publish(template, publish_path, publish_type, publish_fields, engine.context, comment, thumbnail_path, primary_path=primary_path)

    return wrapper

    
def decorator_publish_file(func):
    """
    制作文件发布提交装饰器

    - **被装饰的`func`函数的具名参数定义顺序如下**：
        - `publish_template` (Template)：文件模板，装饰器会将模板名字解析转为模板对象, 注意：`调用函数`时传`模板名字`字符串
        - `publish_type` (str)：发布类型
        - `engine` (Engine)：Engine实列
        - `upstream_file` (str)：上游文件，一般是主软件场景文件，场景文件本身是没有上游文件的，默认为空
        - `fields` (dict)：调用的时候可以传入额外字段，装饰器解析后会重新覆盖该字段值
        - `comment` (str)：发布的描述信息
        - `thumbnail_file` (str)：预览图文件路径
        - `publish_path` (str， auto)：注意：此参数是装饰器额外生成的，调用函数的时候不用传
        - `*args`：其它额外参数
        - `**kwargs`：其它额外参数


    Note:
       - 参数（publish_template）：传入的时候是模板名字，`str`类型；函数中使用的时候是`Template`对象（装饰器会自动将模板名字转为模板对象）
       - 参数（fields）：传入和返回都是`dict`类型，一般只用于指定`version`版本号；函数中使用的数据是装饰器解析后的最终所有字段，
       - 参数（publish_path）：这个参数是装饰器新增加的，不用传。

    Example:
        import mix_toolkit.api
        import shutil

        # 1. 完全定义方式
        @mix_toolkit.api.decorator_publish_file
        def publish_maya(
            publish_template, 
            publish_type, 
            engine, 
            upstream_file='', 
            fields={}, 
            comment='', 
            thumbnail_file='', 
            publish_path='',
            *args, 
            **kwargs
        ):
            current_scene = engine.handle.api.current_scene()
            shutil.copy2(current_scene, publish_path)

        # 2. 简短定义方式：根据需要暴露出想要的参数
        @mix_toolkit.api.decorator_publish_file
        def publish_maya(engine=None, publish_path='', *args, **kwargs):
            current_scene = engine.handle.api.current_scene()
            shutil.copy2(current_scene, kwargs['publish_path'])

        # 3. 精简定义方式：从kwargs里面取想要的数据
        @mix_toolkit.api.decorator_publish_file
        def publish_maya(*args, **kwargs):
            current_scene = kwargs['engine'].handle.api.current_scene()
            shutil.copy2(current_scene, kwargs['publish_path'])

        engine = mix_toolkit.api.get_current_engine()
        publish_maya('publish_asset_maya', 'Maya', engine)

    """
    @functools.wraps(func)
    def wrapper(publish_template=None, publish_type='', engine=None, upstream_file='', fields={}, comment='', thumbnail_file='', *args, **kwargs):
        if not isinstance(publish_template, str) or not publish_template:
            raise ValueError('"publish_template" must be a valid string not None or ""')
        if not isinstance(publish_type, str) or not publish_type:
            raise ValueError('"publish_type" must be a valid string not None or ""')
        if not isinstance(engine, Engine) or not engine:
            raise ValueError('"engine" must be a "Engine" type')
        
        
        publish_template = format_value(publish_template)
        template = get_template_by_name(publish_template)
        if not template:
            raise ValueError('can not find template by name : "%s"' %
                            publish_template)
        publish_fields = get_template_fields_from_context(template, engine.context)
        if fields and isinstance(fields, dict):
            publish_fields.update(fields)
        publish_path = template.apply_fields(publish_fields).replace('\\', '/')
        tmp_publish_path = get_tmp_publish_path(publish_path, template)
        try:
            exrea_files = func(publish_template=template, publish_type=publish_type, engine=engine, upstream_file=upstream_file,
                            fields=fields, comment=comment, thumbnail_file=thumbnail_file, publish_path=tmp_publish_path, *args, **kwargs)
        except Exception as e:
            traceback.print_exc()
            raise IOError("Publish Error %s: %s" % (publish_type, e))
        return register_publish(template, publish_path, publish_type, publish_fields, engine.context, comment, thumbnail_file, tmp_publish_path, upstream_file, exrea_files)
    return wrapper


def decorator_register_publish(func):
    """数据发布装饰器"""
    # def wrapper(publish_template, publish_type, primary_path, engine, extra_fields={}, comment='', thumbnail_path='', *args, **kwargs):
    def wrapper(task, fields, primary_path, engine, comment, thumbnail_path, *args, **kwargs):
        """数据发布装饰器函数的包装器
        
        Args:
            task (dict): 任务信息字典
            fields (dict): 字段信息字典 
            primary_path (str): 主要文件路径
            engine (object): 引擎对象
            comment (str): 发布注释
            thumbnail_path (str): 缩略图路径
            *args: 可变位置参数
            **kwargs: 可变关键字参数
            
        Returns:
            dict: 包含发布信息的字典
            
        Raises:
            ValueError: 当找不到指定的模板时抛出
            IOError: 当发布失败时抛出
        """
        publish_template_name = format_value(
            task['output']['publish_template'])
        template = get_template_by_name(publish_template_name)
        if not template:
            raise ValueError('can not find template by name : "%s"' %
                             publish_template_name)
        publish_fields = get_template_fields_from_context(
            template, engine.context)
        publish_fields.update(fields)
        publish_path = template.apply_fields(publish_fields).replace('\\', '/')
        tmp_publish_path = get_tmp_publish_path(publish_path, template)

        try:
            exrea_files = func(task, publish_fields, primary_path, engine,
                               comment, thumbnail_path, tmp_publish_path, template.location_name, *args, **kwargs)
        except Exception as e:
            traceback.print_exc()
            raise IOError("Publish Error %s: %s" % (task['output']['name'], e))
        publish_type = format_value(task['output']["publish_type"])
        return register_publish(template, publish_path, publish_type, publish_fields, engine.context, comment, thumbnail_path, tmp_publish_path, primary_path, exrea_files)
    return wrapper




def filter_by_template(in_template, paths, fields={}):
    """通过模板过滤符合规范的路径

    根据给定的模板对象过滤路径列表，返回符合模板规范的路径和对应的模板对象。
    会检查路径的层级结构和文件扩展名是否匹配模板定义。

    Args:
        in_template (Template): 用于过滤的模板对象
        paths (list): 需要过滤的路径列表
        fields (dict, optional): 用于更新模板字段的参考字段字典，默认为空

    Returns:
        dict: 过滤后的结果字典，键为符合规范的路径，值为对应的模板对象
              例如: {'/path/to/file.ext': Template对象, ...}

    示例:
        >>> template = Template('shot_{shot}/work/maya/scenes/model.ma', 'maya')
        >>> paths = ['/shows/shot_010/work/maya/scenes/model.ma',
                    '/shows/shot_020/work/maya/scenes/rig.ma']
        >>> result = filter_by_template(template, paths)
        >>> print(result)
        {'/shows/shot_010/work/maya/scenes/model.ma': <Template object>}
    """
    result = {}
    for _path in paths:
        _path = _path.replace('\\', '/')
        _root = in_template.location.replace('\\', '/')
        if _root.endswith('/'):
            _root = _root[:-1]
        value_path = _path[len(_root)+1:]
        if value_path.count('/') != in_template.template_value.count('/'):
            continue

        if '.' in _path or '.' in in_template.template_value:
            if _path.split('.')[-1].lower() != in_template.template_value.split('.')[-1].lower():
                continue
        _template = Template(in_template.template_value,
                             in_template.location_name)
        if fields:
            _template.update_fields(fields)
        _fields = _template.get_fields(_path)
        if _fields:
            __path = _template.apply_fields(_fields)
            if __path.replace('\\', '/') == _path.replace('\\', '/'):
                result[_path] = _template
    return result

def format_value(name):
    """格式化字符串中的三元运算符表达式

    将字符串中的三元运算符表达式替换为实际值。支持以下两种格式:
    1. {variable} operator value ? true_value : false_value
    2. {variable:value} ? true_value : false_value

    支持的运算符:
    - =, == : 等于
    - != : 不等于  
    - in : 包含于列表
    - not in : 不包含于列表

    Args:
        name (str): 包含三元运算符表达式的字符串

    Returns:
        str: 替换表达式后的字符串

    示例:
        >>> format_value("{task} == asset ? Model : Layout") 
        'Model'  # 当task字段值为'asset'时
        >>> format_value("{task:asset} ? Model : Layout")
        'Model'  # 简写形式
        >>> format_value("{dept} in [model,rig] ? Asset : Shot")
        'Asset'  # 当dept字段值在列表中时
    """
    engine = get_current_engine()
    fields = engine.plugins_fileds
    if not fields:
        if os.environ.get('%s_SOFTWARE_code' % DCC_APP_CODE):
            fields['software'] = os.environ.get('%s_SOFTWARE_code' % DCC_APP_CODE)
        if os.environ.get('%s_USER' % DCC_APP_CODE):
            fields['user'] = os.environ.get('%s_USER' % DCC_APP_CODE)
        if os.environ.get('%ss_PROJECT_NAME' % DCC_APP_CODE):
            fields['project'] = os.environ.get('%ss_PROJECT_NAME' % DCC_APP_CODE)
        if os.environ.get('%s_ENTITY_TYPE' % DCC_APP_CODE):
            fields['entity_type'] = os.environ.get('%s_ENTITY_TYPE' % DCC_APP_CODE)
    if '?' in name:
        mat = re.match(
            '\s*{\s*(\w+)\s*}\s*([!=in]*|not in)\s*(\w+|\[[a-zA-Z0-9, -]+\])\s*\?\s*([a-zA-Z{}_ ]+)\s*:\s*([a-zA-Z{}_ ]+)\s*', name)
        if mat:
            variable, operator, value, ok_value, no_value = mat.groups()
            if variable in fields:
                if operator in ['=', '==']:
                    if (fields[variable].lower() == value.lower()):
                        name = ok_value
                    else:
                        name = no_value
                elif operator in ['!=']:
                    if (fields[variable].lower() != value.lower()):
                        name = ok_value
                    else:
                        name = no_value
                elif operator in ['in', 'not in'] and value.startswith('[') and value.endswith(']'):
                    value_list = []
                    for i in value[1:-1].split():
                        v = i.strip()
                        if v:
                            value_list.append(v.lower())
                    if operator == 'in':
                        if fields[variable].lower() in value_list:
                            name = ok_value
                        else:
                            name = no_value
                    else:
                        if fields[variable].lower() not in value_list:
                            name = ok_value
                        else:
                            name = no_value
        else:
            mat = re.match(
                '\s*{\s*(\w+)\s*:\s*(\w+)\s*}\s*\?\s*([a-zA-Z{}_ ]+)\s*:\s*([a-zA-Z{}_ ]+)\s*', name)
            if mat:
                variable, value, ok_value, no_value = mat.groups()
                if variable in fields:
                    if (fields[variable].lower() == value.lower()):
                        name = ok_value
                    else:
                        name = no_value

    for field in fields:
        name = name.replace('{%s}' % field, str(fields[field]))
    return name

def format_version(version_number):
    return PROJECT_TEMPLATE['keys'][VERSION_KEY]['format'].format(
        int(version_number))

def get_context(data):
    """生成Context对象
    Args:
        data (dict): 相关数据
    Returns:
        Context: Context对象
    """
    return Context(data)

def get_context_from_path(path):
    """通过文件路径解析context

    根据给定的文件路径查找对应的发布文件记录，获取关联的任务ID，
    然后获取该任务的上下文数据并返回Context对象。

    Args:
        path (str): 发布的文件路径

    Returns:
        Context: 如果找到对应的任务则返回Context对象，否则返回None

    Example:
        >>> context = get_context_from_path('/path/to/file.ma')
        >>> if context:
        ...     print(context.Task['id'])
    """
    all_publish_files = APP.find(
        'PublishFile', [['path', 'is', path.replace('\\', '/')]])
    if not all_publish_files:
        return
    task_id = all_publish_files[0]['task_id']
    data = APP.get_task_context(task_id)
    if data:
        return Context(data)

@error_decorator
def get_context_from_task(task):
    """通过任务对象获取context

    根据给定的任务对象获取该任务的上下文数据并返回Context对象。

    Args:
        task (dict): 任务对象，必须包含id字段

    Returns:
        Context: 如果找到对应的任务则返回Context对象，否则返回None

    Example:
        >>> task = {'id': 123}
        >>> context = get_context_from_task(task)
        >>> if context:
        ...     print(context.Task['id'])
    """
    data = APP.get_task_context(task["id"])
    if data:
        return Context(data)

def get_current_engine():
    global ENGINE_INSTANCE
    if not ENGINE_INSTANCE or not isinstance(ENGINE_INSTANCE, Engine):
        ENGINE_INSTANCE = Engine()
    return ENGINE_INSTANCE
    
    # instances = {}
    # @functools.wraps(cls)
    # def _singleton(*args, **kwargs):
    #     if cls not in instances:
    #         instances[cls] = cls(*args, **kwargs)
    #     return instances[cls]
    # return _singleton


    # return Engine()

def get_current_project():
    """获取项目详情

    从环境变量中获取项目ID，并通过kmoke API查询项目详细信息。

    Returns:
        dict: 项目详情，包含项目的基本信息如名称、ID等

    Raises:
        ValueError: 当环境变量中未配置项目ID或项目不存在时抛出

    Example:
        >>> project = get_current_project()
        >>> print(project['name'])
    """
    id = os.getenv('%s_PROJECT_ID' % DCC_APP_CODE)
    if not id:
        raise ValueError('project id is not config: %s_PROJECT_ID' % DCC_APP_CODE)
    project = None
    try:
        project = APP.find_one('Project', int(id))
    except:
        pass
    if not project:
        raise ValueError('PROJECT {} is not exists' .format(str(id)))
    return project

def get_current_project_id():
    """获取当前项目id
    
    从环境变量中获取当前项目的ID。

    Returns:
        int: 项目ID。如果环境变量未设置则返回None

    Example:
        >>> project_id = get_current_project_id()
        >>> if project_id:
        ...     print(f"Current project ID: {project_id}")
    """
    id = os.getenv('%s_PROJECT_ID' % DCC_APP_CODE)
    if not id:
        return
    return int(id)



def get_laset_version_fields(template, fields):
    """获取最新版本的字段

    根据模板文件名中的version字段，获取当前最大版本号并生成下一个版本号。
    
    Args:
        template (Template): 模板对象，包含文件名模板和字段信息
        fields (dict): 字段字典，包含需要替换到文件名中的字段值
        
    Returns:
        dict: 更新后的fields字典，其中version字段被设置为下一个版本号
        
    Example:
        >>> template = Template("shot_{version}.ma")
        >>> fields = {"version": "v001"}
        >>> result = get_laset_version_fields(template, fields)
        >>> print(result["version"])  # 输出: v002
    """
    keys_data = PROJECT_TEMPLATE.get('keys', {})
    result_verison = 0
    file_name_template = os.path.basename(template.template_value)
    file_name_keys = template.order_keys(file_name_template)
    if 'version' in file_name_keys:
        for key in fields:
            if key in file_name_keys:
                if key == "version":
                    continue
                file_name_template = file_name_template.replace(
                    '{%s}' % key, str(fields[key]))
        version_count = file_name_template.count('{version}')
        file_name_re = file_name_template.replace('{version}', '([0-9]+)')
        template_file_path = template.apply_fields(fields)
        file_root = os.path.dirname(template_file_path)
        if os.path.isdir(file_root):
            all_file_name = os.listdir(file_root)
            versions = [0]
            for _file in all_file_name:
                _file_path = os.path.join(file_root, _file).replace('\\', '/')
                if not os.path.isfile(_file_path):
                    continue
                mat = re.match(file_name_re, _file)
                if mat:
                    groups = [int(i) for i in list(mat.groups())]
                    if version_count == 1:
                        versions.append(groups[0])
                    else:
                        if min(groups) == max(groups):
                            versions.append(max(groups))
            result_verison = max(versions)
    fields['version'] = keys_data['version']['format_spec'].format(
        result_verison+1)
    return fields

def get_location_root(location):
    """获取位置根路径
    
    Args:
        location (str): 位置名称，将被转换为小写进行匹配
        
    Returns:
        str: 如果位置存在于PROJECT_LOCATIONS中，返回格式化后的路径（使用'/'作为分隔符）
             如果位置不存在，返回None
             
    Example:
        >>> root = get_location_root("SHOTS")
        >>> print(root)  # 输出: /path/to/shots
    """
    location = location.lower()
    if location in PROJECT_LOCATIONS:
        return PROJECT_LOCATIONS[location].replace('\\', '/')

@error_decorator
def get_publish_type_from_path(path, task):
    path = path.replace(os.sep, '/')
    if isinstance(task, int):
        task_id = task
    elif isinstance(task, dict):
        task_id = task['id']
    else:
        return
    all_publish_files = APP.find(
        'PublishFile', [['path', 'is', path], ['task_id', 'is', task_id]])
    for _file in all_publish_files:
        return _file['publish_type']

@error_decorator
def get_script(name, scripts):
    """获取插件脚本模块
    
    根据脚本名从插件脚本列表中获取对应的脚本模块。脚本名会被转换为小写进行匹配。

    Args:
        name (str): 脚本名称，将被转换为小写进行匹配
        scripts (dict): 插件脚本字典，key为脚本名(小写)，value为脚本数据

    Returns:
        module: 加载后的脚本模块对象

    Raises:
        ValueError: 当scripts为空或name不存在于scripts中时抛出

    Example:
        >>> scripts = {'test_script': {'path': '/path/to/script.py'}}
        >>> module = get_script('test_script', scripts)
    """
    if not scripts:
        raise ValueError("not scripts found in plugins")
    name = format_value(name).lower()
    if name not in scripts:
        raise ValueError("plugin has no script: %s" % name)
    return load_script(scripts[name.lower()])

def get_template_by_name(name, location=None):
    """通过名字获取模板对象
    
    根据模板名称从项目模板配置中获取对应的模板对象。如果指定了location参数，则只在该location下查找模板。
    模板名称会被转换为小写进行匹配。

    Args:
        name (str): 模板名称，将被转换为小写进行匹配
        location (str, optional): 模板所在的位置，如'shots'、'assets'等。默认为None，表示在所有位置查找

    Returns:
        Template: 找到的模板对象。如果未找到对应模板则返回None

    Example:
        >>> template = get_template_by_name('shot_work')  # 在所有位置查找
        >>> template = get_template_by_name('asset_work', 'assets')  # 只在assets位置查找
    """
    name = format_value(name)
    name = name.lower()
    template_locations = {i.lower(): i for i in PROJECT_TEMPLATE['paths']}
    if location:
        location = location.lower()
        if location not in PROJECT_LOCATIONS:
            return
        if location not in template_locations:
            return
        tag_location = template_locations[location]
        _value = PROJECT_TEMPLATE['paths'][tag_location].get(name)
        if _value:
            return Template(_value, location)
    else:
        for _location in template_locations:
            if _location not in PROJECT_LOCATIONS:
                continue
            tag_location = template_locations[_location]
            _value = PROJECT_TEMPLATE['paths'][tag_location].get(name)
            if _value:
                return Template(_value, _location)

def get_template_fields_from_context(template, context):
    """从上下文中获取模板字段值
    
    根据模板定义和上下文信息，获取模板中各个字段的具体值。支持从实体属性和当前时间中获取字段值。

    Args:
        template (Template): 模板对象，包含需要填充的字段定义
        context (object): 上下文对象，包含实体信息和其他属性

    Returns:
        dict: 包含模板字段名和对应值的字典

    Raises:
        ValueError: 当template或context为None时抛出
        ValueError: 当无法从context中获取某个必需字段的值时抛出

    Example:
        >>> template = get_template_by_name('shot_work')
        >>> context = get_current_context()
        >>> fields = get_template_fields_from_context(template, context)
        >>> print(fields)
        {'Shot': 'shot_010', 'Step': 'comp', 'version': 1}
    """
    if not context or not template:
        raise ValueError('template and context can not be None')
    fields = {}
    keys = template.keys
    keys_config = PROJECT_TEMPLATE['keys']
    for k in keys:
        if k not in fields:
            k_data = keys_config[k]
            if k_data.get('entity_type'):
                field_name = k_data['field_name']
                field_entity = k_data['entity_type']
                if hasattr(context, field_entity):
                    __data = getattr(context, field_entity)
                    value = __data.get(field_name)
                else:
                    if field_name in context.Entity:
                        value = context.Entity[field_name]
                    else:
                        raise ValueError('unknow key: %s' % k)
                if value:
                    fields[k] = value
            else:
                key_type = k_data.get('type')
                k_format = k_data.get('format')
                if key_type == 'datetime' and k_format:
                    tt = datetime.datetime.now()
                    value = datetime.datetime.strftime(tt, k_format)
                    fields[k] = value
                elif key_type == 'int' and k_format:
                    fields[k] = k_format.format(int(k_data.get('default', 1)))
                else:
                    fields[k] = k_data.get('default', 'unknow')
    return fields

def get_template_from_path(path, fields={}, location=''):
    """通过路径解析对应的模板对象，忽略大小写匹配路径和模板名称

    根据给定路径解析出对应的模板对象。会忽略路径和模板名称的大小写进行匹配。
    如果指定了location，则只在该location下查找匹配的模板，否则会遍历所有可用的locations。

    Args:
        path (str): 需要解析的完整路径
        fields (dict, optional): 用于辅助模板匹配的字段值字典。默认为空字典
        location (str, optional): 指定查找模板的location。默认为空字符串，表示查找所有locations

    Returns:
        Template: 匹配成功返回对应的模板对象，否则返回None

    Example:
        >>> path = '/shots/seq_010/shot_010/comp/publish/shot_010_comp_v001.mov'
        >>> template = get_template_from_path(path, location='publish')
        >>> print(template)
        <Template '{Shot}_comp_v{version}.mov'>
    """
    path = path.replace('\\', '/')
    locations = []
    template_locations = {i.lower(): i for i in PROJECT_TEMPLATE['paths']}
    if location:
        location = location.lower()
        if location in PROJECT_LOCATIONS:
            locations.append(location)
    else:
        for _location in template_locations:
            if _location in PROJECT_LOCATIONS:
                locations.append(_location)

    for _location in locations:
        _location_root = PROJECT_LOCATIONS[_location].lower().replace('\\', '/')
        if not path.lower().startswith(_location_root):
            continue
        if not _location_root.endswith('/'):
            _location_root = _location_root + '/'
        relative_path = path[len(_location_root):]
        keys = PROJECT_TEMPLATE['paths'][template_locations[_location]]
        for _name in keys:
            value = keys[_name]
            if value.count('/') != relative_path.count('/'):
                continue
            if os.path.splitext(value.lower())[-1].lower() != os.path.splitext(relative_path.lower())[-1].lower():
                continue
            template = Template(value, _location)
            template.update_fields(fields)
            _fields = template.get_fields(path)
            if not _fields:
                continue
            _path = template.apply_fields(_fields)
            if _path.replace('\\', '/').lower() != path.replace('\\', '/').lower():
                continue
            return template

def get_tmp_publish_path(publish_path, publish_template):
    """获取临时发布路径
    
    根据发布路径和发布模板生成临时发布路径。支持不同的发布类型(transfer/smb)。

    Args:
        publish_path (str): 最终发布文件的完整路径
        publish_template (Template): 发布路径使用的模板对象

    Returns:
        str: 临时发布路径。根据DCC_PUBLISH_TYPE环境变量决定:
            - transfer: 使用transfer location作为根目录
            - smb: 使用work location作为根目录
            - 其他: 使用原始发布路径

    Example:
        >>> path = '/publish/shot_010/comp_v001.mov'
        >>> template = get_template_from_path(path, location='publish') 
        >>> tmp_path = get_tmp_publish_path(path, template)
        >>> print(tmp_path)
        '/transfer/shot_010/comp_v001.mov'
    """

    # TODO
    publish_root = publish_template.location.replace('\\', '/')
    tmp_publish_path = publish_path
    if os.environ.get('DCC_PUBLISH_TYPE', '').lower() == 'smb':
        transfer_root = get_location_root('work').replace('\\', '/')
        tmp_publish_path = transfer_root + publish_path[len(publish_root):]

    publish_folder = os.path.dirname(tmp_publish_path)
    if not os.path.isdir(publish_folder):
        os.makedirs(publish_folder)
    return tmp_publish_path

def get_version_str(version):
    keys_data = PROJECT_TEMPLATE.get('keys', {})
    return keys_data['version']['format_spec'].format(int(version))

@error_decorator
def initialize_plugin(plugin_code):
    """初始化插件属性及配置
    """
    result = {}
    if SOFTWARE_ID:# or TOOL_ID:
        # if SOFTWARE_ID:
        #     plugin_data = APP.get_plugin_attr_and_config(
        #         SOFTWARE_ID, PROJECT_ID, plugin_code)
        # else:
        #     plugin_data = APP.get_tool_plugin_attr_and_config(plugin_code)
        plugin_data = APP._get_plugin_attrs_config(plugin_code)
        if plugin_data:
            attr_list = plugin_data.get('attrs', [])
            if attr_list:
                for attr in attr_list:
                    result[attr['code']] = load_script(attr)
            config_data = plugin_data.get('config', [])
            if config_data:
                loader = _IncludeLoader
                loader.plugin = plugin_code
                result['PLUGIN_CONFIG'] = yaml.load(config_data['content'], loader)
    scripts_data = APP._get_plugin_scripts(plugin_code)
    if scripts_data:
        scripts = {}
        for script in scripts_data:
            scripts[script['code'].lower()] = script
        result['SCRIPTS'] = scripts
    return result

@error_decorator
def register_publish(
        template,
        publish_path,
        publish_type,
        publish_fields,
        context,
        comment,
        thumbnail_path,
        tmp_publish_path,
        primary_path='',
        extra_files=[]
):
    """注册发布
    
    Args:
        template (str): 发布模板
        publish_path (str): 发布路径
        publish_type (str): 发布类型
        publish_fields (dict): 发布字段
        context (dict): 上下文数据
        comment (str): 发布说明
        thumbnail_path (str): 缩略图路径
        tmp_publish_path (str): 临时发布路径
        primary_path (str, optional): 主要文件路径. Defaults to ''.
        extra_files (list, optional): 额外文件列表. Defaults to [].
    
    Raises:
        IOError: 无法获取远程路径时抛出
    """

    if os.environ.get('DCC_PUBLISH_TYPE', '').lower() == 'smb':
        from .samba import Samba
        remote_path = get_samba_path(publish_path, template.location_name)
        if not remote_path:
            raise IOError('Can not get remote path: %s' % remote_path)
        # ip = get_remote_ip(remote_path)
        samba_info = LOCATIONS_DATA[template.location_name.lower()]['samba_info']
        with Samba(
            samba_info['ip'], 
            samba_info['account'], 
            samba_info['password'],
            share = samba_info['share'],
            domain = samba_info['domain']) as smb:
            smb.upload_file(tmp_publish_path, remote_path)
            if extra_files:
                publish_root = os.path.dirname(remote_path)
                for _path in extra_files:
                    if isinstance(_path,list):
                        _name = _path[-1]
                        _path = _path[0]
                        tag_path = os.path.join(
                            publish_root, _name).replace('\\', '/')
                    else:
                        _path = _path.replace('\\', '/')
                        tag_path = os.path.join(
                            publish_root, os.path.basename(_path)).replace('\\', '/')
                    if os.path.isfile(_path):
                        smb.upload_file(_path, tag_path)
                    elif os.path.isdir(_path):
                        for _root, _, files in os.walk(_path):
                            if not files:
                                continue
                            for f in files:
                                _src_file = os.path.join(
                                    _root, f).replace('\\', '/')
                                _tag_file = tag_path + _src_file[len(_path):]
                                smb.upload_file(_src_file, _tag_file)
    else:
        if not os.path.exists(publish_path):
            raise IOError("文件不存在！")
        if extra_files:
            publish_root = os.path.dirname(publish_path)
            for _path in extra_files:
                if isinstance(_path,list):
                    _name = _path[-1]
                    _path = _path[0]
                    tag_path = os.path.join(
                        publish_root, _name).replace('\\', '/')
                else:
                    _path = _path.replace('\\', '/')
                    tag_path = os.path.join(
                        publish_root, os.path.basename(_path)).replace('\\', '/')
                if os.path.isfile(_path):
                    shutil.copy2(_path, tag_path)
                elif os.path.isdir(_path):
                    for _root, _, files in os.walk(_path):
                        if not files:
                            continue
                        for f in files:
                            _src_file = os.path.join(
                                _root, f).replace('\\', '/')
                            _tag_file = tag_path + _src_file[len(_path):]
                            _tag_folder = os.path.dirname(_tag_file)
                            if not os.path.isdir(_tag_folder):
                                os.makedirs(_tag_folder)
                            shutil.copy2(_src_file, _tag_file)
    
    # 上传预览图文件
    publish_type = format_value(publish_type)
    publish_root = template.location.replace('\\', '/')
    _data = {}
    if thumbnail_path:
        try:
            _data = APP.upload_file(thumbnail_path)
        except:
            _data = {}
            pass
    publish_version = 1
    if 'version' in template.keys:
        publish_version = str(int(publish_fields.get('version', 1))) if isinstance(publish_fields, dict) else str(publish_version)
    parms = {
        'project_id': context.Project['id'],
        # 'master_id': context.Project.get('master_id', 0),
        'task_id': context.Task['id'],
        # 'linked_data': str(context.Entity['id']),
        'code': os.path.basename(publish_path),
        'path': publish_path.replace('\\', '/'),
        'relative_path': publish_path.replace('\\', '/')[len(publish_root):],
        'publish_type': publish_type,
        'version_number': publish_version,
        'thumbnail': _data.get('url', '') if isinstance(_data, dict) else '',
        'description': comment,
        'location': template.location_name,
        'template': template.template_value,
        'from_software': context.to_dict()['Software'].get('code', '') if context.has_key('Software') else '',
        'entity_id': context.Entity['id'],
        'entity_type': context.Entity['type'],
        'upstream_file': str(primary_path) if primary_path else '',
    }
    APP.create('PublishFile', parms)
    # try:
    #     _publish_path = ''
    #     _final_path = ''
    #     if context.Entity['type'].lower()== 'asset':
    #         publish_root_template = get_template_by_name('publish_asset_root','archive')
    #         final_root_template = get_template_by_name('final_asset_root','archive')
    #         _fields = get_template_fields_from_context(publish_root_template,context)
    #         _publish_path = publish_root_template.apply_fields(_fields)
    #         _final_path = final_root_template.apply_fields(_fields)
    #     elif context.Entity['type'].lower()== 'shot':
    #         publish_root_template = get_template_by_name('publish_shot_root','archive')
    #         final_root_template = get_template_by_name('final_shot_root','archive')
    #         _fields = get_template_fields_from_context(publish_root_template,context)
    #         _publish_path = publish_root_template.apply_fields(_fields)
    #         _final_path = final_root_template.apply_fields(_fields)
    #     elif context.Entity['type'].lower()== 'sequence':
    #         publish_root_template = get_template_by_name('publish_sequence_root','archive')
    #         final_root_template = get_template_by_name('final_sequence_root','archive')
    #         _fields = get_template_fields_from_context(publish_root_template,context)
    #         _publish_path = publish_root_template.apply_fields(_fields)
    #         _final_path = final_root_template.apply_fields(_fields)
    #     if _publish_path:
    #         print(u'通知服务器进行文件同步：Publish')
    #         print(_publish_path)
    #         APP.handover_sync_fileSync(context.Project['id'],_publish_path)
    #     if _final_path :
    #         print(u'通知服务器进行文件同步: Final')
    #         print(_final_path)
    #         APP.handover_sync_fileSync(context.Project['id'],_final_path)
    # except:
    #     traceback.print_exc()
    return parms

