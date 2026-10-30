#!/usr/bin/env python
# -*- coding: utf8 -*-
# title       : Kmoke日志模块
# description : 提供统一的日志记录功能，支持文件和控制台输出
# author      : ShenMeng


import os
import logging
from logging.handlers import RotatingFileHandler
DCC_APP_CODE = (os.environ.get('DCC_APP_CODE') or 'MIX').upper()

class DCCLogger(object):
    """
    Kmoke日志记录器类
    
    主要功能：
    1. 同时支持文件和控制台日志输出
    2. 文件日志支持自动轮转
    3. 支持自定义日志路径和格式
    """
    
    # 创建和配置logger实例
    logger = logging.getLogger(DCC_APP_CODE)
    logger.setLevel(logging.DEBUG)  # 设置日志级别为DEBUG
    
    # 确定日志文件存储路径
    log_root = os.environ.get('{}_LOG_PATH'.format(DCC_APP_CODE))
    if not log_root:
        # 尝试使用REZ包路径
        rez_root = os.environ.get('REZ_PACKAGES_PATH')
        if rez_root:
            log_root = os.path.join(os.path.dirname(rez_root), 'logs')
        else:
            # 默认使用用户文档目录
            doc_root = os.path.expanduser('~').replace('\\', '/')
            if not doc_root.endswith('Documents'):
                doc_root = '{}/Documents'.format(doc_root)
            log_root = os.path.join(doc_root, DCC_APP_CODE.lower())
            
    # 确保日志目录存在
    if not os.path.exists(log_root):
        os.makedirs(log_root)
        
    # 配置文件日志处理器
    file_handler = RotatingFileHandler(
        os.path.join(log_root, '{}.log'.format(DCC_APP_CODE.lower())),  # 日志文件路径
        maxBytes=1024*1024,                    # 单个日志文件最大1MB
        backupCount=10,                        # 保留10个备份文件
        encoding='utf-8'                       # 使用UTF-8编码
    )
    file_handler.setLevel(logging.DEBUG)
    
    # 配置控制台日志处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    
    # 配置日志格式
    software_code = os.environ.get('{}_SOFTWARE_CODE'.format(DCC_APP_CODE))
    
    # 根据是否有软件代码选择不同的格式
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    if software_code:
        formatter = logging.Formatter('%(asctime)s - {} - %(levelname)s - %(message)s'.format(software_code))
    
    # 应用日志格式
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 将处理器添加到logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    @classmethod
    def log(cls, msg):
        """
        记录调试级别的日志
        
        Args:
            msg: 要记录的日志消息
        """
        cls.logger.debug(msg)

    @classmethod
    def error(cls, msg):
        """
        记录错误级别的日志
        
        Args:
            msg: 要记录的错误消息
        """
        cls.logger.error(msg)
