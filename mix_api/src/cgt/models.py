# -*- coding: utf-8 -*-
"""
CGTeamwork 数据模型定义 (mix_api.cgt.models)
纯数据实体类，保持 100% 宿主与 GUI 无关性。
"""

from typing import Optional, List, Dict, Any


class EntityType(object):
    """实体类型常量"""
    ASSET = "Asset"
    SHOT = "Shot"


class TaskSource(object):
    """任务数据来源。"""
    CGT = "cgt"
    OFFLINE = "offline"
    FALLBACK = "fallback"
    MANUAL = "manual"


class TaskValidationState(object):
    """任务与 CGTeamwork 的校验状态。"""
    VERIFIED = "verified"
    MISSING = "missing"
    OFFLINE = "offline"
    QUERY_ERROR = "query_error"


class Project(object):
    """项目对象"""

    def __init__(self, name: str, database: str, id: str = "", code: str = "",
                 root_path: str = "", frame_rate: str = "24", resolution: str = "1920x1080"):
        self.name = name
        self.database = database
        self.id = id
        self.code = code or name
        self.root_path = root_path
        self.frame_rate = frame_rate
        self.resolution = resolution

    def __repr__(self):
        return f"<Project {self.name} (db={self.database})>"

    @property
    def config_key(self) -> str:
        """项目级配置使用数据库标识，缺失时回退到项目代码/名称。"""
        return self.database or self.code or self.name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "database": self.database,
            "id": self.id,
            "code": self.code,
            "config_key": self.config_key,
            "root_path": self.root_path,
            "frame_rate": self.frame_rate,
            "resolution": self.resolution
        }


class Entity(object):
    """资产或镜头实体基类"""

    def __init__(self, entity_type: str, name: str, id: str = "",
                 asset_type: str = "", episode: str = "", sequence: str = ""):
        self.entity_type = entity_type
        self.name = name
        self.id = id
        # 资产特有字段
        self.asset_type = asset_type
        # 镜头特有字段
        self.episode = episode
        self.sequence = sequence

    @property
    def is_asset(self) -> bool:
        return self.entity_type == EntityType.ASSET

    @property
    def is_shot(self) -> bool:
        return self.entity_type == EntityType.SHOT

    def __repr__(self):
        if self.is_asset:
            return f"<Asset {self.name} (type={self.asset_type})>"
        return f"<Shot {self.name} (ep={self.episode})>"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "name": self.name,
            "id": self.id,
            "asset_type": self.asset_type,
            "episode": self.episode,
            "sequence": self.sequence
        }


class Task(object):
    """制作环节任务对象"""

    def __init__(self, id: str, entity_name: str, step: str, task_name: str,
                 status: str = "Wait", artist: str = "", module: str = "standard_asset",
                 source: str = TaskSource.CGT,
                 validation_state: str = TaskValidationState.VERIFIED,
                 validation_message: str = ""):
        self.id = id
        self.entity_name = entity_name
        self.step = step
        self.task_name = task_name
        self.status = status
        self.artist = artist
        self.module = module
        self.source = source
        self.validation_state = validation_state
        self.validation_message = validation_message

    @property
    def is_verified(self) -> bool:
        return self.validation_state == TaskValidationState.VERIFIED

    def __repr__(self):
        return f"<Task {self.step}/{self.task_name} on {self.entity_name} [{self.status}]>"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_name": self.entity_name,
            "step": self.step,
            "task_name": self.task_name,
            "status": self.status,
            "artist": self.artist,
            "module": self.module,
            "source": self.source,
            "validation_state": self.validation_state,
            "validation_message": self.validation_message,
        }


class FileboxInfo(object):
    """文件框与规范信息"""

    def __init__(self, title: str, sign: str, classify: str,
                 path: str = "", rule: Optional[List[str]] = None):
        self.title = title
        self.sign = sign
        self.classify = classify
        self.path = path
        self.rule = rule or []

    def __repr__(self):
        return f"<Filebox '{self.title}' (sign={self.sign}) -> {self.path}>"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "sign": self.sign,
            "classify": self.classify,
            "path": self.path,
            "rule": self.rule
        }


class ParsedContext(object):
    """从文件全路径或文件名逆向反解出的上下文参数"""

    def __init__(self,
                 raw_path: str = "",
                 entity_type: str = EntityType.ASSET,
                 project: str = "",
                 asset_name: str = "",
                 asset_type: str = "",
                 episode: str = "",
                 sequence: str = "",
                 shot_name: str = "",
                 step: str = "",
                 task: str = "",
                 version: str = "001",
                 extension: str = "ma",
                 matched_pattern: str = ""):
        self.raw_path = raw_path
        self.entity_type = entity_type
        self.project = project
        self.asset_name = asset_name
        self.asset_type = asset_type
        self.episode = episode
        self.sequence = sequence
        self.shot_name = shot_name
        self.step = step
        self.task = task
        self.version = version
        self.extension = extension
        self.matched_pattern = matched_pattern

    @property
    def display_entity_name(self) -> str:
        if self.entity_type == EntityType.ASSET:
            return self.asset_name
        return f"{self.episode}_{self.shot_name}" if self.episode else self.shot_name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_path": self.raw_path,
            "entity_type": self.entity_type,
            "project": self.project,
            "asset_name": self.asset_name,
            "asset_type": self.asset_type,
            "episode": self.episode,
            "sequence": self.sequence,
            "shot_name": self.shot_name,
            "step": self.step,
            "task": self.task,
            "version": self.version,
            "extension": self.extension,
            "matched_pattern": self.matched_pattern,
            "display_entity_name": self.display_entity_name
        }

    def __repr__(self):
        return (f"<ParsedContext {self.entity_type}: {self.display_entity_name} "
                f"Step={self.step} Task={self.task} V{self.version}>")
