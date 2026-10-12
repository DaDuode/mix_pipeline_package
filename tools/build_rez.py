#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Rez 包自动化构建工具
用法:
    python build_rez.py mix_toolkit --version 1.0.0
    python build_rez.py --all --version 1.0.0
"""
import os
import sys
import argparse
import shutil
import zipfile
import subprocess

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def build_package(package_name, version='1.0.0'):
    pkg_dir = os.path.join(REPO_ROOT, package_name)
    build_script = os.path.join(pkg_dir, 'build_package.py')
    if not os.path.exists(build_script):
        raise FileNotFoundError(f"build_package.py not found in {pkg_dir}")

    print(f"[*] Building {package_name} v{version}...")
    # 动态执行对应包下的 build_package.py
    sys_path_bak = list(sys.path)
    sys.path.insert(0, pkg_dir)
    try:
        import build_package as bp
        if hasattr(bp, 'main'):
            bp.main(version)
        else:
            raise AttributeError("build_package.py has no main(version) function")
    finally:
        sys.path = sys_path_bak

    # 打包为 zip
    build_dir = os.path.join(pkg_dir, 'build')
    target_version_dir = os.path.join(build_dir, package_name, version)
    if not os.path.exists(target_version_dir):
        raise FileNotFoundError(f"Built package directory not found: {target_version_dir}")

    zip_filename = f"{package_name}-{version}.zip"
    zip_path = os.path.join(build_dir, zip_filename)
    if os.path.exists(zip_path):
        os.remove(zip_path)

    print(f"[*] Compressing into {zip_path}...")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(target_version_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, target_version_dir)
                zipf.write(full_path, rel_path)

    print(f"[+] Successfully generated archive: {zip_path}")
    return zip_path

def main():
    parser = argparse.ArgumentParser(description="Build Rez Package for Mix Pipeline")
    parser.add_argument("package", nargs="?", help="Package name (e.g. mix_toolkit)")
    parser.add_argument("--all", action="store_true", help="Build all packages")
    parser.add_argument("--version", default="1.0.0", help="Target package version")
    args = parser.parse_args()

    if args.all:
        for item in os.listdir(REPO_ROOT):
            if item.startswith("mix_") and os.path.isdir(os.path.join(REPO_ROOT, item)):
                build_package(item, args.version)
    elif args.package:
        build_package(args.package, args.version)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
