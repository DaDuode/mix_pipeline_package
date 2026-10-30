# -*- coding: utf-8 -*-
import os
import uuid
import sys
import shutil

def main(version='1.0.0'):
    template = '''#!/usr/bin/env python
# -*- encoding: utf-8 -*-

name = '{package_name}'
version = '{package_version}'
uuid = '{package_uuid}'
format_version = 2
requires = []

'''
    commands = '''
def commands():
    import os
    env.PYTHONPATH.append("{root}")
    if os.environ.get("DCC_PYTHON_LIBS"):
        env.PYTHONPATH.append(os.environ["DCC_PYTHON_LIBS"])
'''
    current_root = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/')
    build_root = os.path.join(current_root, 'build').replace('\\', '/')
    src_path = os.path.join(current_root, 'src')
    package_name = 'mix_api'

    if os.path.exists(build_root):
        shutil.rmtree(build_root)
    tag_root_version = os.path.join(build_root, package_name, version)
    os.makedirs(tag_root_version)

    tag_path = os.path.join(tag_root_version, package_name).replace('\\', '/')
    tag_package_py = os.path.join(tag_root_version, 'package.py').replace('\\', '/')

    content = template.format(
        package_name=package_name,
        package_version=version,
        package_uuid=uuid.uuid4().hex
    ) + commands

    with open(tag_package_py, 'w', encoding='utf-8') as f:
        f.write(content)

    if not os.path.exists(tag_path):
        shutil.copytree(src_path, tag_path)
    print(f"Successfully built {package_name} v{version} at {tag_root_version}")

if __name__ == '__main__':
    main()
