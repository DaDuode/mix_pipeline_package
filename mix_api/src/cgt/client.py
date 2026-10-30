# -*- coding: utf-8 -*-
"""
CGTeamwork 业务层封装客户端 (mix_api.cgt.client)
面向对象的项目、资产、镜头、个人待办任务与文件框数据查询与提交接口。
"""

import logging
from typing import Optional, List, Dict, Any

from .session import CGTSession, get_tw
from .models import (
    Project,
    Entity,
    EntityType,
    Task,
    TaskSource,
    TaskValidationState,
    FileboxInfo,
)

logger = logging.getLogger("mix_api.cgt.client")


class CGTClient(object):
    """CGTeamwork 业务访问客户端"""

    def __init__(self, database: str = "", project_name: str = ""):
        self.database = database
        self.project_name = project_name
        self.session = CGTSession()
        self.last_query_error = ""

    @property
    def tw(self):
        return self.session.tw

    @property
    def is_connected(self) -> bool:
        return self.session.is_connected

    def get_projects(self) -> List[Project]:
        """获取所有可用项目"""
        self.last_query_error = ""
        if not self.is_connected:
            return [Project(self.project_name, self.database)] if self.database else []

        try:
            fields = ["project.entity", "project.database", "project.id", "project.frame_rate", "project.resolution"]
            project_ids = self.tw.project.get_id([])
            if not project_ids:
                return []
            proj_data = self.tw.project.get(project_ids, fields)
            projects = []
            for p in proj_data:
                projects.append(Project(
                    name=p.get("project.entity", ""),
                    database=p.get("project.database", ""),
                    id=p.get("project.id", ""),
                    frame_rate=p.get("project.frame_rate", "24"),
                    resolution=p.get("project.resolution", "1920x1080")
                ))
            return projects
        except Exception as e:
            self.last_query_error = str(e)
            logger.warning("Failed to get projects from CGT: %s", e)
            return [Project(self.project_name, self.database)] if self.database else []

    def get_asset_types(self) -> List[str]:
        """获取资产类型分类"""
        if not self.is_connected or not self.database:
            return ["Chars", "Props", "Scene", "Element"]
        try:
            type_ids = self.tw.info.get_id(self.database, "asset_type", [])
            data = self.tw.info.get(self.database, "asset_type", type_ids, ["asset_type.entity"])
            return sorted(list(set([d["asset_type.entity"] for d in data if d.get("asset_type.entity")])))
        except Exception as e:
            logger.warning("Failed to get asset types: %s", e)
            return ["Chars", "Props", "Scene", "Element"]

    def get_assets(self, asset_type: Optional[str] = None, limit: str = "5000") -> List[Entity]:
        """获取指定分类或全部资产"""
        if not self.is_connected or not self.database:
            return []
        try:
            filters = []
            if asset_type:
                filters.append(["asset_type.entity", "=", asset_type])
            ids = self.tw.info.get_id(self.database, "standard_asset", filters, limit=limit)
            if not ids:
                return []
            data = self.tw.info.get(self.database, "standard_asset", ids, [
                "standard_asset.id", "standard_asset.entity", "asset_type.entity"
            ])
            return [
                Entity(
                    entity_type=EntityType.ASSET,
                    name=d.get("standard_asset.entity", ""),
                    id=d.get("standard_asset.id", ""),
                    asset_type=d.get("asset_type.entity", "")
                )
                for d in data
            ]
        except Exception as e:
            logger.warning("Failed to get assets: %s", e)
            return []

    def get_episodes(self) -> List[str]:
        """获取所有分集"""
        if not self.is_connected or not self.database:
            return ["E010", "E020", "E070"]
        try:
            ids = self.tw.info.get_id(self.database, "ep", [], limit="200")
            if not ids:
                return []
            data = self.tw.info.get(self.database, "ep", ids, ["ep.entity"])
            return sorted(list(set([d["ep.entity"] for d in data if d.get("ep.entity")])))
        except Exception as e:
            logger.warning("Failed to get episodes: %s", e)
            return ["E010", "E020", "E070"]

    def get_shots(self, episode: Optional[str] = None, limit: str = "5000") -> List[Entity]:
        """获取指定分集的镜头列表"""
        if not self.is_connected or not self.database:
            return []
        try:
            filters = []
            if episode:
                filters.append(["ep.entity", "=", episode])
            ids = self.tw.info.get_id(self.database, "scope", filters, limit=limit)
            if not ids:
                return []
            data = self.tw.info.get(self.database, "scope", ids, [
                "scope.id", "scope.entity", "ep.entity"
            ])
            return [
                Entity(
                    entity_type=EntityType.SHOT,
                    name=d.get("scope.entity", ""),
                    id=d.get("scope.id", ""),
                    episode=d.get("ep.entity", "")
                )
                for d in data
            ]
        except Exception as e:
            logger.warning("Failed to get shots: %s", e)
            return []

    def get_tasks(self, entity_type: str, entity_name: str, step: Optional[str] = None,
                  parent_name: Optional[str] = None, include_deleted: bool = False) -> List[Task]:
        """获取实体的任务列表"""
        self.last_query_error = ""
        if not self.is_connected or not self.database:
            return []
        module = "standard_asset" if entity_type == EntityType.ASSET else "scope"
        entity_field = "standard_asset.entity" if entity_type == EntityType.ASSET else "scope.entity"

        filters = [[entity_field, "=", entity_name]]
        if step:
            filters.append(["pipeline.entity", "=", step])
        if parent_name:
            if entity_type == EntityType.SHOT:
                filters.append(["ep.entity", "=", parent_name])
            elif entity_type == EntityType.ASSET:
                filters.append(["asset_type.entity", "=", parent_name])

        try:
            t_ids = self.tw.task.get_id(self.database, module, filters, limit="100")
            if not t_ids:
                return []
            data = self.tw.task.get(self.database, module, t_ids, [
                "task.id", entity_field, "pipeline.entity", "task.entity", "task.status", "task.artist"
            ])
            tasks = []
            for d in data:
                status = d.get("task.status", "Wait") or "Wait"
                if not include_deleted and status in ("删除", "已删除", "作废", "Del", "Delete", "废弃"):
                    continue
                tasks.append(
                    Task(
                        id=d.get("task.id", ""),
                        entity_name=d.get(entity_field, entity_name),
                        step=d.get("pipeline.entity", ""),
                        task_name=d.get("task.entity", ""),
                        status=status,
                        artist=d.get("task.artist", ""),
                        module=module,
                        source=TaskSource.CGT,
                        validation_state=TaskValidationState.VERIFIED,
                    )
                )
            return tasks
        except Exception as e:
            self.last_query_error = str(e)
            logger.warning("Failed to get tasks for %s: %s", entity_name, e)
            return []

    def get_my_tasks(self, account: Optional[str] = None, module: str = "standard_asset") -> List[Task]:
        """查询指定制作人在当前项目、指定模块（standard_asset 或 scope）下的所有待办任务"""
        if not self.is_connected or not self.database:
            return []
        target_account = account or self.session.account
        if not target_account:
            return []

        entity_field = "standard_asset.entity" if module == "standard_asset" else "scope.entity"
        filters = [["task.artist", "=", target_account]]

        try:
            t_ids = self.tw.task.get_id(self.database, module, filters, limit="500")
            if not t_ids:
                return []
            data = self.tw.task.get(self.database, module, t_ids, [
                "task.id", entity_field, "pipeline.entity", "task.entity", "task.status", "task.artist"
            ])
            tasks = []
            for d in data:
                status = d.get("task.status", "Wait") or "Wait"
                if status in ("删除", "已删除", "作废", "Del", "Delete", "废弃"):
                    continue
                tasks.append(
                    Task(
                        id=d.get("task.id", ""),
                        entity_name=d.get(entity_field, ""),
                        step=d.get("pipeline.entity", ""),
                        task_name=d.get("task.entity", ""),
                        status=status,
                        artist=d.get("task.artist", target_account),
                        module=module,
                        source=TaskSource.CGT,
                        validation_state=TaskValidationState.VERIFIED,
                    )
                )
            return tasks
        except Exception as e:
            logger.warning("Failed to get my tasks for account %s: %s", target_account, e)
            return []

    def get_filebox(self, module: str, task_id: str, sign: str = "work") -> Optional[FileboxInfo]:
        """查询指定任务的 Filebox 路径与命名规则"""
        if not self.is_connected or not self.database:
            return None
        try:
            box_data = self.tw.task.get_filebox_with_id(self.database, module, task_id, sign)
            if not box_data:
                return None
            return FileboxInfo(
                title=box_data.get("title", sign),
                sign=sign,
                classify=box_data.get("classify", ""),
                path=box_data.get("path", ""),
                rule=box_data.get("rule", [])
            )
        except Exception as e:
            logger.warning("Failed to get filebox for task %s (%s): %s", task_id, sign, e)
            return None

    def update_task_status(self, module: str, task_id: str, status: str) -> bool:
        """更新任务状态 (如 In Progress, Check)"""
        if not self.is_connected or not self.database:
            return False
        try:
            return bool(self.tw.task.update(self.database, module, task_id, {"task.status": status}))
        except Exception as e:
            logger.error("Failed to update task status %s -> %s: %s", task_id, status, e)
            return False
