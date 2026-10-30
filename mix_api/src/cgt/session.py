# -*- coding: utf-8 -*-
"""
CGTeamwork 会话连接管理 (mix_api.cgt.session)
支持：
1. 优先复用本机已运行且已登录的 CGTeamwork 客户端 Session；
2. 自动从环境变量 (MAYA_CGT_ACCOUNT, MAYA_CGT_PASSWORD, CGT_ACCOUNT, CGT_PASSWORD) 获取明文凭据自动后台静默登录；
3. 支持显式调用 login(account, password, http_ip) 登录并维持单例会话。
"""

import os
import sys
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("mix_api.cgt.session")

CGT_DEFAULT_PATHS = [
    r"C:\CgTeamWork_v7\bin\base",
    r"C:\CgTeamWork_v6\bin\base",
    r"C:\CgTeamWork\bin\base"
]


class CGTSession(object):
    """CGTeamwork 连接管理单例"""

    _instance = None
    _tw = None
    _connected = False
    _auth_mode = "offline"  # "client" | "auto_login" | "offline"
    _account = ""
    _http_server_ip = "172.16.10.16:8383"
    _last_error = ""

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(CGTSession, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._tw is None:
            self._init_connection()

    @classmethod
    def reset(cls):
        """重置当前会话，便于切换账号或重连"""
        if cls._instance is not None:
            cls._instance.__dict__.clear()
        cls._tw = None
        cls._connected = False
        cls._auth_mode = "offline"
        cls._account = ""
        cls._last_error = ""

    def _ensure_cgtw2_imported(self) -> bool:
        """确保 cgtw2 模块可用"""
        if "cgtw2" in sys.modules:
            return True
        for p in CGT_DEFAULT_PATHS:
            if os.path.isdir(p) and p not in sys.path:
                sys.path.insert(0, p)
                break
        try:
            import cgtw2
            return True
        except ImportError:
            self._last_error = "无法加载 CGTeamwork SDK (cgtw2)，请检查 CGTeamwork 安装目录"
            logger.warning("Unable to import cgtw2 module. Please ensure CGTeamwork SDK is installed or available.")
            return False

    def _init_connection(self):
        """核心连接逻辑：客户端复用 -> 环境变量/配置免密登录 -> 脱机模式"""
        if not self._ensure_cgtw2_imported():
            self._tw = None
            self._connected = False
            self._auth_mode = "offline"
            return

        import cgtw2

        # The launcher passes its active login to each independent bridge process.
        # It must take precedence over a different account in the desktop CGT app.
        launcher_account = os.environ.get("MIX_LAUNCHER_CGT_ACCOUNT", "").strip()
        if launcher_account:
            self.login(
                launcher_account,
                os.environ.get("MIX_LAUNCHER_CGT_PASSWORD", ""),
                os.environ.get("MIX_LAUNCHER_CGT_SERVER_IP") or self._http_server_ip,
            )
            return

        # 1. 优先尝试复用本机已登录的桌面客户端会话
        try:
            tw_candidate = cgtw2.tw()
            if tw_candidate and hasattr(tw_candidate, "login") and tw_candidate.login.is_login():
                self._tw = tw_candidate
                self._connected = True
                self._auth_mode = "client"
                self._account = tw_candidate.login.account()
                self._http_server_ip = tw_candidate.login.http_server_ip()
                logger.info(
                    "Connected to CGTeamwork via local client session (User: %s, Server: %s).",
                    self._account, self._http_server_ip
                )
                return
        except Exception as client_err:
            logger.debug("Local CGTeamwork desktop socket unavailable: %s", client_err)

        # 2. 尝试从环境变量获取凭据进行静默登录
        http_ip = os.environ.get("MAYA_CGT_SERVER_IP") or os.environ.get("CGT_SERVER_IP") or self._http_server_ip
        account = (os.environ.get("MAYA_CGT_ACCOUNT") or os.environ.get("CGT_ACCOUNT") or "").strip()
        password = os.environ.get("MAYA_CGT_PASSWORD") or os.environ.get("CGT_PASSWORD") or ""

        if account and password:
            if self.login(account, password, http_ip):
                return

        # 3. 兜底脱机
        self._tw = None
        self._connected = False
        self._auth_mode = "offline"

    def login(self, account: str, password: str, http_ip: str = "172.16.10.16:8383") -> bool:
        """显式登录 CGTeamwork 服务端并维持会话"""
        self._tw = None
        self._connected = False
        self._auth_mode = "offline"
        self._account = ""
        self._last_error = ""
        if not self._ensure_cgtw2_imported():
            return False
        import cgtw2

        try:
            tw_instance = cgtw2.tw(http_ip=http_ip, account=account, password=password)
            if tw_instance and hasattr(tw_instance, "login") and tw_instance.login.is_login():
                self._tw = tw_instance
                self._connected = True
                self._auth_mode = "auto_login"
                self._account = account
                self._http_server_ip = http_ip
                logger.info("CGTeamwork login succeeded (User: %s, Server: %s).", account, http_ip)
                return True
            else:
                self._last_error = "CGTeamwork 登录被拒绝，请核对账号、密码和服务器地址"
                logger.warning("CGTeamwork login rejected for account '%s' at %s.", account, http_ip)
                return False
        except Exception as err:
            self._last_error = str(err).replace(password, "***") if password else str(err)
            logger.error("CGTeamwork login failed: %s", err)
            return False

    @property
    def tw(self):
        """获取 cgtw2.tw() 实例"""
        if self._tw is None and not self._connected:
            self._init_connection()
        return self._tw

    @property
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected and (self._tw is not None)

    @property
    def auth_mode(self) -> str:
        return self._auth_mode

    @property
    def account(self) -> str:
        return self._account

    @property
    def http_server_ip(self) -> str:
        return self._http_server_ip

    @property
    def last_error(self) -> str:
        return self._last_error

    def get_connection_status(self) -> Dict[str, Any]:
        """获取当前连接状态摘要"""
        return {
            "connected": self.is_connected,
            "account": self.account,
            "server_ip": self.http_server_ip,
            "auth_mode": self.auth_mode,
        }


def get_tw():
    """获取 CGTeamwork 底层 tw() 实例"""
    return CGTSession().tw
