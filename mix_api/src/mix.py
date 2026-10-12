#!/usr/bin/env python
# -*- coding: utf8 -*-

"""
Mix 应用服务 Python SDK

提供对 Mix 应用服务接口的访问能力，
并动态生成第三方应用接口的调用方法。

使用示例：
    sdk = MixSDK(base_url="http://app-server.com", api_key="your-api-key")
    # 调用应用服务自身的接口
    sdk.app_some_endpoint(param1="value1")
    # 调用动态生成的第三方应用接口
    sdk.third_party_app_code.aa_bb_cc(cc=[1, 2], aa=123, bb="test")
"""
import os
import types
import yaml
import requests
import functools
import mimetypes
def re_build():
    def _wraper(func, *args, **kwargs):
        functools.wraps(func)
        def __wraper(self, *args, **kwargs):
            data = func(self, *args, **kwargs)
            if data:
                if data.get('code') != 200:
                    print(data['code'])
                    raise Exception(data['message'])
                data = data.get('data', None)
            return data
        return __wraper
    return _wraper

# ---------------------------------------------------------------------------
# 类型校验辅助类
# ---------------------------------------------------------------------------

class TypeValidator:
    """校验并转换参数值到期望的数据类型。"""

    TYPE_MAP = {
        "int": int,
        "str": str,
        "float": float,
        "list": list,
        "dict": dict,
        "bool": bool,
    }

    @classmethod
    def validate_and_convert(cls, value, type_name, param_name):
        """根据 type_name 校验 value 的值，并尝试进行类型转换。"""
        expected_type = cls.TYPE_MAP.get(type_name.lower())
        if expected_type is None:
            return value
        if isinstance(value, expected_type):
            return value
        try:
            return expected_type(value)
        except (ValueError, TypeError):
            raise TypeError(
                f"Parameter '{param_name}': cannot convert {value!r} to {type_name}"
            )


# ---------------------------------------------------------------------------
# 主 SDK
# ---------------------------------------------------------------------------

class MixSDK:
    """
    Mix 应用服务的 Python SDK。

    实例化时 SDK 会执行以下操作：
    1. 通过调用 ``app/info`` 接口校验 api_key 的有效性。
    2. 读取该接口返回的第三方应用配置信息。
    3. 将第三方应用的接口方法直接附加到本 SDK 实例上。

    实例化完成后 SDK 可以：
    - 调用主应用自身的接口（通过内置的辅助方法）。
    - 直接调用第三方应用接口（方法名由 YAML 配置动态生成）。

    参数：
        base_url: 应用服务的基础 URL。
        api_key:  授权给第三方应用的 API Key。
        connect_timeout: 连接超时时间，单位秒（默认 10）。
        read_timeout: 读取超时时间，单位秒（默认 30）。
    """

    def __init__( self, base_url, api_key, connect_timeout=10, read_timeout=30):
        if not base_url:
            raise ValueError("base_url is required")
        if not api_key:
            raise ValueError("api_key is required")

        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout

        # 主应用的公共请求头
        self._headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

        # 第三方应用的访问凭证
        self._tp_base_url = None
        self._tp_api_key  = None
        self._tp_headers  = None

        # 授权校验接口返回的应用信息
        self.app_info = None

        # -- 授权校验并加载第三方应用配置 ---------------------
        self._verify_and_load()

    # -- 授权校验 ------------------------------------------------------

    def _verify_and_load(self):
        """调用 ``app/info`` 接口校验 api_key 并加载第三方应用配置。"""
        try:
            resp = requests.get(
                f"{self.base_url}/api/client/app/info",
                params={"api_key": self.api_key},
                headers=self._headers,
                timeout=(self.connect_timeout, self.read_timeout),
            )
            resp.raise_for_status()
            # print(resp.text)
            # data = json.loads(resp.text)
            data = resp.json()
        except requests.exceptions.RequestException as exc:
            raise ConnectionError(
                f"Failed to verify api_key via {self.base_url}/app/info: {exc}"
            )

        # 预期返回的是已授权的应用信息。
        # 如果返回数据被包裹在 'data' 键中，则解包。
        if isinstance(data, dict) and "data" in data:
            data = data["data"]

        if not data:
            raise PermissionError(
                "Authorisation failed: the api_key is not associated with any application."
            )

        self.app_info = data
        self._register_app(data)

    def _register_app(self, app_cfg):
        """从应用配置字典加载第三方应用的接口方法。"""
        code = app_cfg.get("name")
        tp_base_url = app_cfg.get("base_url")
        app_api_key = app_cfg.get("app_api_key")
        content = app_cfg.get("content", "")

        if not code or not tp_base_url or not app_api_key:
            return  # 跳过不完整的配置项

        # 保存第三方应用的访问凭证
        self._tp_base_url = tp_base_url.rstrip("/")
        self._tp_api_key = app_api_key
        self._tp_headers = {
            "X-API-Key": app_api_key,
            "Content-Type": "application/json",
        }

        # 加载 YAML 配置并生成动态方法
        if content:
            self._load_app_yaml_config(content)

    # -- 第三方应用动态方法生成 ------------------------------------------

    @staticmethod
    def _path_to_method_name(path):
        """将接口路径转换为 Python 方法名。

        规则：
        - ``/`` → ``_``
        - ``-`` → 移除
        """
        return path.replace("/", "_").replace("-", "")

    @re_build()
    def _app_request(self, method, path, params=None, data=None, is_file=False, **kwargs):
        """向第三方应用服务发送 HTTP 请求。"""
        url = f"{self._tp_base_url}/{path.lstrip('/')}"
        method = method.upper()
        try:
            if method == "GET":
                resp = requests.get(url, params=params, headers=self._tp_headers)
            elif method == "POST":
                if is_file:
                    _header = {'X-API-Key': self._tp_headers['X-API-Key']}
                else:
                    _header = self._tp_headers
                resp = requests.post(url, data=data, headers=_header, **kwargs) if is_file else requests.post(url, json=data, headers=_header, **kwargs)
            elif method == "PUT":
                resp = requests.put(url, json=data, headers=self._tp_headers)
            elif method == "DELETE":
                resp = requests.delete(url, params=params, headers=self._tp_headers)
            else:
                raise ValueError(f"不支持的 HTTP 方法: {method}")
            resp.raise_for_status()
            return resp.json()
        except Exception as error:
            raise Exception(f"第三方应用接口请求失败: {error}")

    def _load_app_yaml_config(self, yaml_content):
        """解析第三方应用的 YAML 配置并在此 SDK 实例上创建动态方法。"""
        config = yaml.safe_load(yaml_content)
        if not isinstance(config, dict):
            raise ValueError("第三方应用 YAML 配置必须为字典格式")

        for endpoint_path, endpoint_cfg in config.items():
            http_method = endpoint_cfg.get("type", "GET").upper()
            args_cfg = endpoint_cfg.get("args", {}) or {}
            method_name = endpoint_cfg.get("name", endpoint_path)
            method_name = self._path_to_method_name(str(method_name))
            self._create_app_method(
                method_name,
                str(endpoint_path),
                http_method,
                args_cfg,
                endpoint_cfg,
            )

    @staticmethod
    def _format_help_value(value):
        """将参数 schema 的值格式化为适合 help() 阅读的文本。"""
        if not isinstance(value, dict):
            return str(value)

        parts = []
        type_name = value.get("type")
        description = value.get("description")
        if type_name:
            parts.append(str(type_name))
        if description:
            parts.append(str(description))
        if "default" in value:
            parts.append(f"默认值={value['default']!r}")
        if value.get("required") is False:
            parts.append("可选")
        return "，".join(parts) if parts else str(value)

    @classmethod
    def _format_help_items(cls, title, items):
        """将 YAML 中的列表/字典帮助信息格式化为 docstring 文本。"""
        if not items:
            return []

        lines = [f"{title}:"]
        if isinstance(items, dict):
            items = [items]

        for item in items:
            if isinstance(item, dict):
                for key, value in item.items():
                    lines.append(f"  - {key}: {cls._format_help_value(value)}")
            else:
                lines.append(f"  - {item}")
        return lines

    @classmethod
    def _format_docs_help(cls, docs):
        """将 YAML 中的 docs 帮助信息格式化为 docstring 文本。"""
        if not docs:
            return []

        lines = ["Docs:"]
        for action_item in docs:
            if not isinstance(action_item, dict):
                lines.append(f"  - {action_item}")
                continue

            for action_name, action_info in action_item.items():
                if not isinstance(action_info, dict):
                    lines.append(f"  - {action_name}: {action_info}")
                    continue

                description = action_info.get("description")
                title_parts = [action_name]
                if description:
                    title_parts.append(f"- {description}")
                lines.append("  - " + " ".join(title_parts))

                for section_title, section_key in (
                    ("参数", "args"),
                    ("返回", "returns"),
                    ("说明", "notes"),
                ):
                    section_lines = cls._format_help_items(
                        section_title, action_info.get(section_key)
                    )
                    for section_line in section_lines:
                        lines.append("    " + section_line)
        return lines

    @classmethod
    def _build_method_doc(cls, path, http_method, endpoint_cfg, sig_parts):
        """基于 YAML 接口配置构建动态方法的 help() 文档。"""
        description = endpoint_cfg.get("description")
        doc_lines = []
        if description:
            doc_lines.append(str(description))
            doc_lines.append("")

        doc_lines.append(f"{http_method} {path}")
        doc_lines.append("")
        doc_lines.append(f"调用参数: {', '.join(sig_parts) if sig_parts else '（无）'}")

        doc_lines.extend(cls._format_help_items("接口参数", endpoint_cfg.get("args")))
        doc_lines.extend(cls._format_help_items("返回", endpoint_cfg.get("returns")))
        doc_lines.extend(cls._format_help_items("说明", endpoint_cfg.get("notes")))
        doc_lines.extend(
            cls._format_docs_help(endpoint_cfg.get("docs") or endpoint_cfg.get("actions"))
        )

        return "\n".join(doc_lines)

    def _create_app_method(self, method_name, path, http_method, args_cfg, endpoint_cfg=None):
        """构建第三方应用的动态方法并绑定到 SDK 实例上。"""
        endpoint_cfg = endpoint_cfg or {}

        # 分离必传参数（无默认值）和可选参数（有默认值）
        required_params = []
        optional_params = []
        param_types = {}

        for arg_name, arg_info in args_cfg.items():
            if not isinstance(arg_info, dict):
                # 简化形式: arg_name: type_str
                param_types[arg_name] = str(arg_info)
                required_params.append(arg_name)
                continue

            param_types[arg_name] = arg_info.get("type", "str")
            has_default = "default" in arg_info
            is_required = arg_info.get("required", True) if not has_default else False

            if has_default:
                optional_params.append((arg_name, arg_info["default"]))
            elif is_required:
                required_params.append(arg_name)
            else:
                optional_params.append((arg_name, None))

        # 闭包捕获
        _path = path
        _http_method = http_method
        _required = list(required_params)
        _optional = list(optional_params)
        _param_types = dict(param_types)

        def _dynamic_method(self_inner, *args, **kwargs):
            # 将位置参数映射到参数名（必传参数在前，可选参数在后）
            all_names = _required + [n for n, _ in _optional]
            for idx, val in enumerate(args):
                if idx < len(all_names):
                    kwargs[all_names[idx]] = val

            # 为未传递的可选参数应用默认值
            for opt_name, opt_default in _optional:
                if opt_name not in kwargs:
                    kwargs[opt_name] = opt_default

            # 检查必传参数
            for rname in _required:
                if rname not in kwargs or kwargs[rname] is None:
                    raise ValueError(f"缺少必传参数: '{rname}'")

            # 类型校验与转换
            for pname, pval in list(kwargs.items()):
                if pname in _param_types and pval is not None:
                    kwargs[pname] = TypeValidator.validate_and_convert(
                        pval, _param_types[pname], pname
                    )

            if _http_method in ("GET", "DELETE"):
                return self_inner._app_request(_http_method, _path, params=kwargs)
            else:
                return self_inner._app_request(_http_method, _path, data=kwargs)

        # 构建方法签名信息，便于 help() 内省
        sig_parts = []
        for rname in _required:
            sig_parts.append(rname)
        for oname, odefault in _optional:
            sig_parts.append(f"{oname}={odefault!r}")
        _dynamic_method.__name__ = method_name
        _dynamic_method.__qualname__ = f"MixSDK.{method_name}"
        _dynamic_method.__doc__ = self._build_method_doc(
            _path, _http_method, endpoint_cfg, sig_parts
        )

        bound = types.MethodType(_dynamic_method, self)
        setattr(self, method_name, bound)

    # -- 主应用方法 --------------------------------------

    @re_build()
    def _post(self, path, data=None, **kwargs):
        """向主应用服务发送 POST 请求。"""
        url = f"{self.base_url}/{path.lstrip('/')}"
        resp = requests.post(
            url,
            json=data or {},
            headers=self._headers,
            timeout=(self.connect_timeout, self.read_timeout),
            **kwargs,
        )
        resp.raise_for_status()
        return resp.json()

    @re_build()
    def _get(self, path, params=None, **kwargs):
        """向主应用服务发送 GET 请求。"""
        url = f"{self.base_url}/{path.lstrip('/')}"
        resp = requests.get(
            url,
            params=params or {},
            headers=self._headers,
            timeout=(self.connect_timeout, self.read_timeout),
            **kwargs,
        )
        resp.raise_for_status()
        return resp.json()

    def _get_file_path_template(self):
        return self._get("api/client/storage/template")

    def _get_storage_samba(self, code):
        if not code:
            raise ValueError("code不能为空!")
        return self._get("api/client/storage/samba_info", params={'code':code})

    def _get_startup_scripts(self, ids):
        if not ids:
            raise ValueError("ids不能为空!")
        return self._post("api/client/softwares/startup_scripts", data={"ids": ids})

    def _get_scripts(self, ids):
        if not ids:
            raise ValueError("ids不能为空!")
        return self._post("api/client/softwares/scripts", data={"ids": ids})

    def _get_check_items(self, ids):
        if not ids:
            raise ValueError("ids不能为空!")
        return self._post("api/client/softwares/check_items", data={"ids": ids})

    def _get_plugins_menus(self, ids):
        if not ids:
            raise ValueError("ids不能为空!")
        return self._post("api/client/plugins/versions/menus", data={"ids": ids})

    def _get_plugin_attrs_config(self, code):
        if not code:
            raise ValueError("code不能为空!")
        return self._get("api/client/plugins/attrs_config", params={"code": code})

    def _get_plugin_config(self, code, config_code):
        if not code or not config_code:
            raise ValueError("code或config_code不能为空!")
        return self._get("api/client/plugins/config", params={"code": code, "config_code": config_code})

    def _get_plugin_scripts(self, code):
        if not code:
            raise ValueError("code不能为空!")
        return self._get("api/client/plugins/scripts/all", params={"code": code})

    def _get_software_config(self, software_id, id=None, code=''):
        if id or code:
            parms = {'software_version_id':software_id} 
            if id:
                parms['config_id'] = id
            else:
                parms['code'] = code
            return self._get("api/client/softwares/versions/configs", params=parms)
        raise ValueError("id或code不能为空!")

    # -- 第三方应用基本接口 ------------------------
    
    def find_one(self, entity_type, entity_id):
        """根据实体类型和 id 查询单个实体。"""
        if not entity_type or not entity_id:
            raise ValueError("entity_type或entity_id不能为空!")
        return self._app_request( method='POST', path=self.app_info['find_one_endpoint'],  data={
            "entity_type": entity_type,
            "entity_id": entity_id,
        })

    def find(self, entity_type, filters):
        """根据实体类型和过滤条件查询实体列表。"""
        if not entity_type or not filters:
            raise ValueError("entity_type或filters不能为空!")
        return self._app_request( method='POST', path=self.app_info['find_endpoint'], data={
            "entity_type": entity_type,
            "filters": filters or [],
        })

    def create(self, entity_type, data):
        """创建新实体。"""
        if not entity_type or not data:
            raise ValueError("entity_type或data不能为空!")
        return self._app_request( method='POST', path=self.app_info['create_endpoint'], data={
            "entity_type": entity_type,
            "data": data or {},
        })

    def update(self, entity_type, entity_id, data):
        """更新已有实体。"""
        if not entity_type or not entity_id or not data:
            raise ValueError("entity_type或entity_id或data不能为空!")
        return self._app_request( method='POST', path=self.app_info['update_endpoint'], data={
            "entity_type": entity_type,
            "entity_id": entity_id,
            "data": data or {},
        })

    def upload_file(self, file_path, *args, **kwargs):
        """
        上传文件到DCC文件中心
        :param file_path: 本地文件路径
        :param biz_id: 业务对象ID（如任务ID）
        :param biz_domain: 文件中心业务域（默认dcc）
        :param biz_type: 文件中心业务类型（默认publish_file）
        :param usage_type: 文件中心使用场景（默认dcc_upload）
        :param file_kind_hint: 文件类型提示（image/video/audio/document/binary）
        :param path_namespace_hint: 路径兜底命名空间
        """
        if not file_path:
            raise ValueError("file_path不能为空!")
        if not os.path.exists(file_path):
            raise ValueError("file_path不存在:" + file_path)
        # 构造表单数据
        form_data = {}
        # 读取文件并构造文件字段
        with open(file_path, "rb") as file_obj:
            content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
            # files = {"file": file_obj}
            files = {"file": (os.path.basename(file_path), file_obj, content_type)}
            return self._app_request(
                method='POST', 
                path=self.app_info['upload_endpoint'], 
                data=form_data, 
                is_file=True, 
                files=files,
                # timeout=60  # 可根据文件大小调整超时时间
                **kwargs
                )

    def get_task_context(self, task_id):
        if not task_id:
            raise ValueError("task_id不能为空!")
        return self._app_request( method='GET', path=self.app_info['context_endpoint'], params={
            "task_id": task_id
        })

    def my_tasks(self, project_id, user_id):
        if not project_id or not user_id:
            raise ValueError("project_id或user_id不能为空!")
        return self._app_request( method='GET', path=self.app_info['my_task_endpoint'], params={
            "project_id": project_id,
            "user_id": user_id
        })

    def entity_tasks(self, entity_type, entity_id):
        if not entity_type or not entity_id:
            raise ValueError("entity_type或entity_id不能为空!")
        return self._app_request( method='POST', path=self.app_info['entity_task_endpoint'], data={
            "entity_type": entity_type,
            "entity_id": entity_id
        })

