# -*- coding: utf-8 -*-
"""
mix_toolkit 路径规范与模板解析器 (__path_resolver.py)
从 cgt_toolkit 提炼整合，实现对 StorageTemplate YAML 配置与 Filebox 规则的加载，
支持文件名逆向正则反解、正向路径推导与环节开关检查。
"""

import os
import re
import yaml
from typing import Optional, Dict, Any, List

from mix_api.cgt import EntityType, ParsedContext, FileboxInfo


class PathTemplateResolver(object):
    """路径模板反解与正向推导解析器"""

    def __init__(self, config_data: Optional[Dict[str, Any]] = None, config_path: Optional[str] = None):
        self.config_path = config_path
        self.config_data: Dict[str, Any] = config_data or {}
        self.compiled_patterns: Dict[str, Any] = {}
        self.compiled_filebox_templates: List[Dict[str, Any]] = []
        if not self.config_data and self.config_path and os.path.isfile(self.config_path):
            self._load_config()
        elif self.config_data:
            self._compile_all()

    def _load_config(self):
        """从 YAML 配置文件加载"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config_data = yaml.safe_load(f) or {}
        except Exception:
            self.config_data = {}
        self._compile_all()

    def _compile_all(self):
        """预编译文件名匹配正则与 Filebox 路径模板"""
        patterns = self.config_data.get("filename_parse_patterns", {})
        for name, pattern_str in patterns.items():
            try:
                self.compiled_patterns[name] = re.compile(pattern_str, re.IGNORECASE)
            except Exception:
                pass

        if not self.compiled_patterns:
            self.compiled_patterns = {
                "asset_work_file": re.compile(
                    r"^(?P<asset>\w+)_(?P<step>\w+)_(?P<task>\w+)_V(?P<version>\d+)\.(?P<ext>ma|mb)$",
                    re.IGNORECASE
                ),
                "shot_work_file_standard": re.compile(
                    r"^(?:MX_)?(?P<episode>\w+)_(?P<shot>\w+)_(?P<step>\w+)_(?P<task>\w+)_V(?P<version>\d+)\.(?P<ext>ma|mb|mov|mp4|jpg|png|psd)$",
                    re.IGNORECASE
                )
            }

        self._compile_filebox_templates()

    def _compile_filebox_templates(self):
        """编译配置中所有 Filebox 的 path_template 为逆向匹配正则表达式"""
        self.compiled_filebox_templates = []

        # 收集 Shot Filebox 模板
        for pipe, pinfo in self.config_data.get("shot_pipelines", {}).items():
            en = self.is_step_enabled(pipe, EntityType.SHOT)
            for fb in pinfo.get("fileboxes", []):
                pt = fb.get("path_template", "")
                if "{shot}" in pt:
                    reg, lit_len = self._build_template_regex(pt)
                    if reg:
                        self.compiled_filebox_templates.append({
                            "entity_type": EntityType.SHOT,
                            "pipeline": pipe,
                            "filebox_sign": fb.get("sign", ""),
                            "filebox_title": fb.get("title", ""),
                            "pattern": reg,
                            "enabled": en,
                            "literal_len": lit_len,
                            "path_template": pt
                        })

        # 收集 Asset Filebox 模板
        for pipe, pinfo in self.config_data.get("asset_pipelines", {}).items():
            en = self.is_step_enabled(pipe, EntityType.ASSET)
            for fb in pinfo.get("fileboxes", []):
                pt = fb.get("path_template", "")
                if "{asset}" in pt:
                    reg, lit_len = self._build_template_regex(pt)
                    if reg:
                        self.compiled_filebox_templates.append({
                            "entity_type": EntityType.ASSET,
                            "pipeline": pipe,
                            "filebox_sign": fb.get("sign", ""),
                            "filebox_title": fb.get("title", ""),
                            "pattern": reg,
                            "enabled": en,
                            "literal_len": lit_len,
                            "path_template": pt
                        })

        # 排序：已启用的环节优先，路径字面量最长（最具体）的模板优先
        self.compiled_filebox_templates.sort(
            key=lambda x: (x["enabled"], x["literal_len"]),
            reverse=True
        )

    def _build_template_regex(self, tmpl: str):
        """将单个 Filebox 的 path_template 转换为逆向匹配正则"""
        if not tmpl:
            return None, 0
        p = tmpl.replace("\\", "/")
        if p.startswith("@project_root/"):
            p = p[len("@project_root/"):]
        elif p.startswith("@project_root"):
            p = p[len("@project_root"):]
        p = p.lstrip("/")

        replacements = {
            "{asset_type}": r"(?P<asset_type>[A-Za-z0-9_]+)",
            "{asset}": r"(?P<asset>[A-Za-z0-9_]+)",
            "{episode}": r"(?P<episode>[A-Za-z0-9_]+)",
            "{shot}": r"(?P<shot>[A-Za-z0-9_]+)",
            "{step}": r"(?P<step>[A-Za-z0-9_]+)",
            "{task}": r"(?P<task>[A-Za-z0-9_]+)",
            "{project_prefix}": r"[A-Za-z0-9_]+",
            "{project}": r"[A-Za-z0-9_]+",
            "{ver}": r"(?P<ver>\d+)",
            "{user}": r"[A-Za-z0-9_]+"
        }

        parts = re.split(r"(\{[a-zA-Z0-9_]+\})", p)
        regex_parts = []
        literal_len = 0
        for part in parts:
            if part in replacements:
                regex_parts.append(replacements[part])
            else:
                literal_len += len(part)
                escaped = re.escape(part)
                escaped = escaped.replace(r"/SC/", r"/(?:SCProject|SC)/")
                escaped = escaped.replace(r"/SCProject/", r"/(?:SCProject|SC)/")
                escaped = escaped.replace(r"/Asset/", r"/(?:Asset|Assembly)/")
                escaped = escaped.replace(r"/Assembly/", r"/(?:Asset|Assembly)/")
                regex_parts.append(escaped)

        pattern_str = "".join(regex_parts)
        full_pattern = rf"(?:^|/){pattern_str}(?:/.*)?/(?P<_filename>[^/]+)$"
        try:
            return re.compile(full_pattern, re.IGNORECASE), literal_len
        except Exception:
            return None, 0

    @property
    def project_name(self) -> str:
        return self.config_data.get("project_info", {}).get("project_name", "")

    @property
    def project_root(self) -> str:
        return self.config_data.get("project_info", {}).get("project_root", "")

    def parse_file_path(self, path_or_filename: str) -> Optional[ParsedContext]:
        """逆向反解核心算法：根据文件全路径或文件名提取任务实体信息"""
        if not path_or_filename:
            return None

        normalized_path = path_or_filename.replace("\\", "/")
        filename = os.path.basename(normalized_path)
        if not filename:
            return None

        # 1. 第一层：根据 CGTeamwork Filebox 模板逆向解析
        fb_result = self._parse_from_filebox_templates(normalized_path, filename)
        if fb_result:
            return fb_result

        # 2. 第二层：基于工程目录层级的反向推导
        dir_result = self._fallback_parse_from_dir(normalized_path, filename)
        if dir_result:
            return dir_result

        # 3. 第三层：基于正则表达式的文件名解析
        fn_result = self._parse_from_filename_patterns(normalized_path, filename)
        if fn_result:
            return fn_result

        return None

    def _parse_from_filebox_templates(self, normalized_path: str, filename: str) -> Optional[ParsedContext]:
        """第一层：根据 Filebox 模板逆向解析"""
        for item in self.compiled_filebox_templates:
            m = item["pattern"].search(normalized_path)
            if not m:
                continue

            groups = m.groupdict()
            entity_type = item["entity_type"]
            pipe_name = item["pipeline"]

            step = groups.get("step") or pipe_name
            task = groups.get("task") or step

            ver = groups.get("ver")
            if not ver:
                ver_m = re.findall(r"(?:_v|\.)(\d{3,4})(?:\.|\b)", filename, re.IGNORECASE)
                ver = ver_m[-1] if ver_m else "001"

            ext = filename.rsplit(".", 1)[-1] if "." in filename else "ma"
            pattern_tag = f"filebox_template_{pipe_name}_{item['filebox_sign'] or 'fb'}"

            if entity_type == EntityType.SHOT:
                shot_name = groups.get("shot")
                episode = groups.get("episode", "")
                if not shot_name:
                    continue
                return ParsedContext(
                    raw_path=normalized_path,
                    entity_type=EntityType.SHOT,
                    project=self.project_name,
                    episode=episode,
                    shot_name=shot_name,
                    step=step,
                    task=task,
                    version=ver,
                    extension=ext,
                    matched_pattern=pattern_tag
                )
            else:
                asset_name = groups.get("asset")
                if not asset_name:
                    continue
                asset_type = groups.get("asset_type") or self._extract_asset_type_from_path(normalized_path)
                return ParsedContext(
                    raw_path=normalized_path,
                    entity_type=EntityType.ASSET,
                    project=self.project_name,
                    asset_name=asset_name,
                    asset_type=asset_type,
                    step=step,
                    task=task,
                    version=ver,
                    extension=ext,
                    matched_pattern=pattern_tag
                )

        return None

    def _parse_from_filename_patterns(self, normalized_path: str, filename: str) -> Optional[ParsedContext]:
        """第三层：基于正则表达式的文件名解析"""
        has_sc_in_filename = bool(re.search(r"_(SC\d+)_", filename, re.IGNORECASE))
        if has_sc_in_filename:
            shot_match = re.match(
                r"^(?:MX_)?(?P<episode>[A-Za-z0-9_]+)_(?P<shot>SC\d+)_(?P<step>\w+)_(?P<task>\w+)_V(?P<version>\d+)\.(?P<ext>\w+)$",
                filename, re.IGNORECASE
            )
            if shot_match:
                groups = shot_match.groupdict()
                return ParsedContext(
                    raw_path=normalized_path,
                    entity_type=EntityType.SHOT,
                    project=self.project_name,
                    episode=groups.get("episode", ""),
                    shot_name=groups.get("shot", ""),
                    step=groups.get("step", ""),
                    task=groups.get("task", ""),
                    version=groups.get("version", "001"),
                    extension=groups.get("ext", "ma"),
                    matched_pattern="shot_work_file"
                )

        for pat_name, pat in self.compiled_patterns.items():
            m = pat.match(filename)
            if not m:
                continue

            groups = m.groupdict()
            ext = groups.get("ext", "ma")
            version = groups.get("version", "001")
            step = groups.get("step", "")
            task = groups.get("task", step)

            if "episode" in groups and "shot" in groups:
                return ParsedContext(
                    raw_path=normalized_path,
                    entity_type=EntityType.SHOT,
                    project=self.project_name,
                    episode=groups.get("episode", ""),
                    shot_name=groups.get("shot", ""),
                    step=step,
                    task=task,
                    version=version,
                    extension=ext,
                    matched_pattern=pat_name
                )
            elif "asset" in groups:
                asset_name = groups.get("asset", "")
                asset_type = self._extract_asset_type_from_path(normalized_path)
                return ParsedContext(
                    raw_path=normalized_path,
                    entity_type=EntityType.ASSET,
                    project=self.project_name,
                    asset_name=asset_name,
                    asset_type=asset_type,
                    step=step,
                    task=task,
                    version=version,
                    extension=ext,
                    matched_pattern=pat_name
                )

        return None

    def _extract_asset_type_from_path(self, normalized_path: str) -> str:
        """从文件全路径中提取资产分类"""
        match = re.search(r"/Asset/(?P<atype>Chars|Props|Scene|Element|Set)/", normalized_path, re.IGNORECASE)
        if match:
            return match.group("atype")
        return "Chars"

    def _fallback_parse_from_dir(self, normalized_path: str, filename: str) -> Optional[ParsedContext]:
        """目录路径特征识别兜底"""
        ext = filename.rsplit(".", 1)[-1] if "." in filename else "ma"

        shot_match = re.search(
            r"/(?:SCProject|SC|Shot)/(?P<ep>[A-Za-z0-9_]+)/(?P<shot>[A-Za-z0-9_]+)/(?P<step>[A-Za-z0-9_]+)",
            normalized_path,
            re.IGNORECASE
        )
        if shot_match:
            ver_m = re.findall(r"(?:_v|\.)(\d{3,4})(?:\.|\b)", filename, re.IGNORECASE)
            version = ver_m[-1] if ver_m else "001"
            step = shot_match.group("step")
            return ParsedContext(
                raw_path=normalized_path,
                entity_type=EntityType.SHOT,
                project=self.project_name,
                episode=shot_match.group("ep"),
                shot_name=shot_match.group("shot"),
                step=step,
                task=step,
                version=version,
                extension=ext,
                matched_pattern="directory_inference_shot"
            )

        asset_match = re.search(
            r"/(?:Asset|Assembly)/(?P<atype>[A-Za-z0-9_]+)/(?P<asset>[A-Za-z0-9_]+)/(?P<step>[A-Za-z0-9_]+)",
            normalized_path,
            re.IGNORECASE
        )
        if asset_match:
            ver_m = re.findall(r"(?:_v|\.)(\d{3,4})(?:\.|\b)", filename, re.IGNORECASE)
            version = ver_m[-1] if ver_m else "001"
            step = asset_match.group("step")
            return ParsedContext(
                raw_path=normalized_path,
                entity_type=EntityType.ASSET,
                project=self.project_name,
                asset_name=asset_match.group("asset"),
                asset_type=asset_match.group("atype"),
                step=step,
                task=step,
                version=version,
                extension=ext,
                matched_pattern="directory_inference_asset"
            )

        return None

    def is_step_enabled(self, step_name: str, entity_type: Optional[str] = None) -> bool:
        """检查制作环节是否开启"""
        if not step_name:
            return False

        chk_settings = self.config_data.get("pipeline_check_settings", {})
        disabled_steps = [s.lower() for s in chk_settings.get("disabled_steps", [])]
        if step_name.lower() in disabled_steps:
            return False
        active_steps = [s.lower() for s in chk_settings.get("active_steps", [])]
        if active_steps and (step_name.lower() not in active_steps):
            return False

        pipes = []
        if entity_type == EntityType.ASSET or not entity_type:
            pipes.extend(self.config_data.get("asset_pipelines", {}).items())
        if entity_type == EntityType.SHOT or not entity_type:
            pipes.extend(self.config_data.get("shot_pipelines", {}).items())

        for p_name, p_info in pipes:
            if p_name.lower() == step_name.lower():
                if isinstance(p_info, dict) and p_info.get("enabled") is False:
                    return False
        return True

    def get_pipeline_fileboxes(self, entity_type: str, step: str) -> List[Dict[str, Any]]:
        """获取指定环节的所有文件框配置"""
        root_key = "asset_pipelines" if entity_type == EntityType.ASSET else "shot_pipelines"
        pipes = self.config_data.get(root_key, {})
        pipe_info = pipes.get(step, {})
        return pipe_info.get("fileboxes", [])
