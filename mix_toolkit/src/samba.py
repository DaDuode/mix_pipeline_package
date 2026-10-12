#!/user/bin/env python
# -*- encoding: utf-8 -*-
"""
SMB文件操作模块，提供与Samba服务器交互的功能
"""
import sys
import subprocess
import re
import os
import base64
from smb.SMBConnection import SMBConnection
from .logger import error_decorator

@error_decorator
def get_remote_path(in_path):
    """
    获取远程路径
    将本地路径转换为网络共享路径
    
    Args:
        in_path: 输入路径，可以是本地路径或网络路径
        
    Returns:
        转换后的网络共享路径
    """
    def _get_nas_path(in_path):
        mat = re.search('^[a-zA-Z]:', in_path)
        if not mat:
            return
        drive_letter = mat.group()
        if sys.version_info.major == 3:
            output = subprocess.run(
                'net use', capture_output=True, text=True).stdout.strip()
        else:
            output = subprocess.check_output('net use', shell=True)
        output = output.replace('\\', '/')
        result = re.findall(
            '([a-zA-Z]:)[^0-9]*(//[0-9]+.[0-9]+.[0-9]+.[0-9]+/[\w]*)', output)
        if not result:
            return
        for _data in result:
            if _data[0].lower() != drive_letter.lower():
                continue
            return _data[1] + in_path[len(drive_letter):]
    in_path = in_path.replace('\\', '/')
    if in_path.startswith('//'):
        return in_path
    if sys.version_info.major == 3:
        import pathlib
        _path = str(pathlib.Path(in_path).resolve()).replace('\\', '/')
        if _path.startswith('//'):
            return _path
    return _get_nas_path(in_path).replace('\\', '/')



def valid_pad_length(length):
    return 2 <= length <= 9

class Samba:
    """
    Samba客户端类
    用于处理SMB协议的文件操作，包括上传、下载、删除等功能

    Example:
        ip = '10.10.10.10'
        account = 'test'
        password = '123456'
        share = 'kmoke'
        domain = 'kmoke'
        local_path = 'D:/aa/bb/test.mb'
        remote_path = '//10.10.10.10/kmoke/test/test.mb'
        with Samba( ip, account, password, share, domain) as smb:
            smb.upload_file(local_path, remote_path)
    """
    @error_decorator
    def __init__(self, ip, account, password, share, domain):
        """
        初始化Samba连接
        
        Args:
            ip: Samba服务器IP地址
            account: 登录账号
            password: Base64编码的密码
            share: 共享名称
            domain: 域名
            
        Raises:
            ValueError: IP地址格式错误时抛出
        """
        if not re.match('^[0-9]+.[0-9]+.[0-9]+.[0-9]+$', str(ip)):
            raise ValueError('Give IP is error: %s' % str(ip))
        password = self.__decrypt_samba_password(password)

        self.__samba = SMBConnection(account, password,
                                     '', '', domain=domain, use_ntlm_v2=True)
        self.__share = share

        self.__ip = ip


    def __decrypt_samba_password(self, password):
        if not password:
            raise ValueError("密码不能为空")

        token = str(password)
        if len(token) < 6:
            raise ValueError("密码值太短")

        tail = token[-2:]
        if not tail.isdigit():
            raise ValueError("密码值不包含有效的长度标记")

        prefix_length = int(tail[0]) + 1
        suffix_length = int(tail[1]) + 1
        if not valid_pad_length(prefix_length) or not valid_pad_length(suffix_length):
            raise ValueError("密码值包含无效的长度标记")

        payload = token[:-2]
        if len(payload) <= prefix_length + suffix_length:
            raise ValueError("密码值无效")

        reversed_b64 = payload[prefix_length:len(payload) - suffix_length]
        raw_b64 = reversed_b64[::-1]
        try:
            # return base64.b64decode(raw_b64, validate=True).decode("utf-8")
            if sys.version_info.major == 3:
                return str(base64.b64decode(bytes(raw_b64, encoding='utf-8')), encoding='utf-8')
            else:
                return str(base64.b64decode(bytes(raw_b64)))

        except Exception as exc:
            raise ValueError("Password value is not valid") from exc


    def __enter__(self):
        """上下文管理器入口，建立SMB连接"""
        if self.__samba.connect(self.__ip):
            return self

    def __exit__(self, exc_type, exc_value, exc_track, *args, **kwargs):
        """上下文管理器出口，确保连接关闭并打印异常跟踪"""
        self.__samba.close()
        print(exc_track)

    def __exists(self, path):
        """
        检查路径是否存在
        
        Args:
            path: 要检查的路径
            
        Returns:
            bool: 路径存在返回True，否则返回None
        """
        try:
            return self.__samba.getAttributes(self.__share, path)
        except:
            return


    def close(self):
        """关闭SMB连接"""
        self.__samba.close()

    def _makedirs(self, path):
        """
        递归创建目录
        
        Args:
            path: 要创建的目录路径
        """
        def __makedirs(path, parts):
            if not self.__exists(path):
                self.__samba.createDirectory(self.__share, path)
            if parts:
                path += '/' + parts.pop()
                __makedirs(path, parts)

        parts = path.replace('\\', '/').split('/')
        parts.reverse()
        path = parts.pop()
        __makedirs(path, parts)

    def __delete_folder(self, root):
        """
        递归删除文件夹内容
        
        Args:
            root: 要删除的根目录路径
        """
        files = self.__samba.listPath( self.__share, root)
        for f in files:
            if f.filename.startswith('.'):
                continue
            if f.isDirectory:
                self.__delete_folder(os.path.join(root, f.filename).replace('\\', '/'))
            else:
                self.__samba.deleteFiles(self.__share, os.path.join(root, f.filename).replace('\\', '/'))
        try:
            self.__samba.deleteDirectory(self.__share, root)
        except:pass

    @error_decorator
    def delete_file(self, src_path):
        """
        删除单个文件
        
        Args:
            src_path: 要删除的文件路径
        """
        src_path = src_path.replace('\\', '/')
        file_path = self.get_smb_path(src_path)
        self.__samba.deleteFiles( self.__share, file_path, delete_matching_folders=False, timeout=30)

    @error_decorator
    def delete_folder(self, src_path):
        """
        删除文件夹及其内容
        
        Args:
            src_path: 要删除的文件夹路径
        """
        src_path = src_path.replace('\\', '/')
        file_path = self.get_smb_path(src_path)
        self.__delete_folder(file_path)

    @error_decorator
    def isfile(self, src_path):
        """
        检查SMB路径是否存在
        
        Args:
            src_path: 要检查的路径
            
        Returns:
            bool: 是否是文件
        """
        
        file_path = self.get_smb_path(src_path)
        shared_file = self.__exists(file_path)
        if shared_file:
            return not shared_file.isDirectory
        else:
            raise IOError('File not exists: %s' % src_path)
    
    @error_decorator
    def isdir(self, src_path):
        """
        检查SMB路径是否存在
        
        Args:
            src_path: 要检查的路径
            
        Returns:
            bool: 是否时文件夹
        """
        
        file_path = self.get_smb_path(src_path)
        shared_file = self.__exists(file_path)
        if shared_file:
            return shared_file.isDirectory
        else:
            raise IOError('File not exists: %s' % src_path)


    @error_decorator
    def download_file(self, src_path, tag_path):
        """
        从SMB共享下载文件
        
        Args:
            src_path: SMB源文件路径
            tag_path: 本地目标路径
        """
        tag_path = tag_path.replace('\\', '/')
        file_path = self.get_smb_path(src_path)
        tag_root = os.path.dirname(tag_path)
        if not os.path.exists(tag_root):
            os.makedirs(tag_root)
        with open(tag_path, 'wb') as f:
            self.__samba.retrieveFile(
                self.__share, file_path, f)
            

    def __download_folder(self, src_path, tag_path):
        files = self.__samba.listPath( self.__share, src_path)
        if not os.path.exists(tag_path):
            os.makedirs(tag_path)
        for f in files:
            if f.filename.startswith('.'):
                continue
            _src_path = os.path.join(src_path, f.filename).replace('\\', '/')
            _tag_path = os.path.join(tag_path, f.filename)
            if f.isDirectory:
                self.__download_folder(_src_path, _tag_path)
            else:
                with open(_tag_path, 'wb') as ff:
                    self.__samba.retrieveFile(
                        self.__share, _src_path, ff)
    @error_decorator
    def download_folder(self, src_path, tag_path):
        """
        从SMB共享下载文件夹
        
        Args:
            src_path: SMB源文件夹路径
            tag_path: 本地目标文件夹路径
        """
        remote_root = self.get_smb_path(src_path)
        if self.__exists(remote_root):
            self.__download_folder(remote_root, tag_path)

            
    @error_decorator
    def exists(self, src_path):
        """
        检查SMB路径是否存在
        
        Args:
            src_path: 要检查的路径
            
        Returns:
            bool: 路径存在返回True，否则返回False
        """
        file_path = self.get_smb_path(src_path)
        return True if self.__exists(file_path) else False

    def get_smb_path(self, in_path):
        """
        转换并验证SMB路径
        
        Args:
            in_path: 输入的SMB路径（如 //192.168.1.1/share/path）
            
        Returns:
            str: 共享内的相对路径
            
        Raises:
            ValueError: 路径格式错误或IP不匹配时抛出
        """
        in_path = in_path.replace('\\', '/')
        # mat = re.match(
        #     '^//(\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3})/([a-zA-Z0-9_]+)/(.*)$', in_path)
        mat = re.match(
            u'^//(\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3})/([^/]+)/(.*)$', in_path)
        if mat:
            groups = mat.groups()
            if len(groups) == 3:
                ip, share, file_path = groups
                if ip != self.__ip:
                    raise ValueError(
                        "smb ip ( %s ) and file location ip ( %s ) are not same" % (self.__ip, ip))
                self.__share = share
                return file_path

        raise ValueError("smb path error: %s" % in_path)

    @error_decorator
    def makedirs(self, tag_path):
        """
        创建目录及其所需的父目录
        
        Args:
            tag_path: 要创建的目录路径
        """
        file_path = self.get_smb_path(tag_path)
        self._makedirs(file_path)

    @error_decorator
    def upload_file(self, src_path, tag_path):
        """
        上传单个文件到SMB共享
        
        Args:
            src_path: 本地源文件路径
            tag_path: SMB目标路径
        """
        file_path = self.get_smb_path(tag_path)
        file_root = os.path.dirname(file_path)
        if not self.__exists(file_root):
            self._makedirs(file_root)
        with open(src_path, 'rb') as f:
            self.__samba.storeFile(
                self.__share, file_path, f)
            
    @error_decorator
    def upload_folder(self, src_path, tag_path):
        """
        上传整个文件夹及其内容到SMB共享
        
        Args:
            src_path: 本地源文件夹路径
            tag_path: SMB目标路径
        """
        src_path = src_path.replace('\\', '/')
        tag_root = self.get_smb_path(tag_path)
        for root, folders, files in os.walk(src_path):
            if not files:
                continue
            root = root.replace('\\', '/')
            for _file in files:
                if src_path == root:
                    relative_path = ''
                else:
                    relative_path = root[len(src_path):]
                _tag_root = tag_root + relative_path
                if not self.__exists(_tag_root):
                    self._makedirs(_tag_root)
                _tag_file = os.path.join(_tag_root, _file).replace('\\', '/')
                _src_file = os.path.join(root, _file).replace('\\', '/')
                with open(_src_file, 'rb') as f:
                    self.__samba.storeFile(
                        self.__share, _tag_file, f)


@error_decorator
def get_remote_ip(in_path):
    """
    从SMB路径中提取IP地址
    
    Args:
        in_path: SMB路径
        
    Returns:
        str: 提取的IP地址，如果没有匹配则返回None
    """
    in_path = in_path.replace('\\', '/')
    mat = re.match('^//(\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3})/(.*)$', in_path)
    if mat:
        return mat.groups()[0]


