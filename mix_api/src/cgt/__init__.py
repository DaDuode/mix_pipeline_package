# -*- coding: utf-8 -*-
"""
mix_api.cgt
统一 CGTeamwork 数据通信 SDK，100% 宿主无关。
"""

from .session import CGTSession, get_tw
from .client import CGTClient
from .models import (
    Project,
    Entity,
    EntityType,
    Task,
    TaskSource,
    TaskValidationState,
    FileboxInfo,
    ParsedContext
)


def login(account: str, password: str, http_ip: str = "172.16.10.16:8383") -> bool:
    """快速登录 CGTeamwork 服务端并维持全局会话"""
    return CGTSession().login(account=account, password=password, http_ip=http_ip)


def get_client(database: str = "", project_name: str = "") -> CGTClient:
    """获取指定项目的 CGTClient 实例"""
    return CGTClient(database=database, project_name=project_name)


__all__ = [
    "CGTSession",
    "get_tw",
    "CGTClient",
    "Project",
    "Entity",
    "EntityType",
    "Task",
    "TaskSource",
    "TaskValidationState",
    "FileboxInfo",
    "ParsedContext",
    "login",
    "get_client",
]
