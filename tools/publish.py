#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
一键发布工具：打包并上传至 Mix Studio Serve 服务端
用法:
    python publish.py mix_toolkit --version 1.0.0 --server http://127.0.0.1:8765
"""
import os
import sys
import argparse
import requests
from build_rez import build_package, REPO_ROOT

def publish(package_name, version='1.0.0', server_url='http://127.0.0.1:8765', api_key=None):
    server_url = server_url.rstrip('/')
    headers = {}
    if api_key:
        headers['Authorization'] = f"Bearer {api_key}"

    print(f"[*] Step 1: Building {package_name}...")
    zip_path = build_package(package_name, version)

    print(f"[*] Step 2: Uploading ZIP archive to {server_url}...")
    upload_url = f"{server_url}/api/v1/upload/zip"
    with open(zip_path, 'rb') as fp:
        files = {'file': (os.path.basename(zip_path), fp, 'application/zip')}
        resp = requests.post(upload_url, files=files, headers=headers)

    if resp.status_code != 200:
        raise RuntimeError(f"Upload failed ({resp.status_code}): {resp.text}")

    upload_result = resp.json()
    if upload_result.get('code') != 200 and 'data' not in upload_result:
        raise RuntimeError(f"Upload returned error: {upload_result}")

    stored_file_path = upload_result['data']['url']
    print(f"[+] ZIP uploaded successfully: {stored_file_path}")

    print(f"[*] Step 3: Registering version in Mix Studio Serve...")
    # 查找插件是否存在
    plugins_url = f"{server_url}/api/v1/plugins"
    resp = requests.get(plugins_url, headers=headers)
    plugins = resp.json().get('data', []) if resp.status_code == 200 else []

    target_plugin = None
    for p in plugins:
        if p.get('code') == package_name:
            target_plugin = p
            break

    if not target_plugin:
        print(f"[*] Plugin {package_name} does not exist, creating new...")
        plugin_type = "engine" if "maya" in package_name or "houdini" in package_name else "plugin"
        create_payload = {
            "name": package_name.replace('_', ' ').title(),
            "code": package_name,
            "plugin_type": plugin_type,
            "description": f"Auto-created package {package_name}"
        }
        resp = requests.post(plugins_url, json=create_payload, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to create plugin ({resp.status_code}): {resp.text}")
        target_plugin = resp.json().get('data')

    plugin_id = target_plugin['id']
    version_url = f"{server_url}/api/v1/plugins/{plugin_id}/versions"
    version_payload = {
        "version": version,
        "path": stored_file_path,
        "filename": os.path.basename(zip_path),
        "release_note": f"Published via publish.py CLI"
    }
    resp = requests.post(version_url, json=version_payload, headers=headers)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to register version ({resp.status_code}): {resp.text}")

    print(f"[SUCCESS] {package_name} v{version} published successfully to Mix Studio Serve!")

def main():
    parser = argparse.ArgumentParser(description="Publish Package to Mix Studio Serve")
    parser.add_argument("package", help="Package name (e.g. mix_toolkit)")
    parser.add_argument("--version", default="1.0.0", help="Version to release")
    parser.add_argument("--server", default=os.getenv("MSC_SERVER_URL", "http://127.0.0.1:8765"), help="Server URL")
    parser.add_argument("--api-key", default=os.getenv("MSC_API_KEY", ""), help="API Key / Token")
    args = parser.parse_args()

    publish(args.package, args.version, args.server, args.api_key)

if __name__ == '__main__':
    main()
