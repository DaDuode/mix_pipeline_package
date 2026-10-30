# -*- coding: utf-8 -*-
"""Run inside Maya's Python Script Editor; never opens or saves a scene.

import runpy
runpy.run_path(r'D:/td/mix_dcc/mix_pipeline_package/tools/diagnose_maya.py', run_name='__main__')
"""
import json
import os
import tempfile


def main():
    import mix_api
    import mix_toolkit

    # Make only the new diagnostic modules available to an already-running
    # 1.0.0 session. Existing engine/menu modules and objects stay loaded.
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for package, name in [(mix_api, 'mix_api'), (mix_toolkit, 'mix_toolkit')]:
        source = os.path.join(root, name, 'src')
        if source not in package.__path__:
            package.__path__.append(source)

    from mix_toolkit.runtime import diagnose
    report = diagnose()
    destination = os.path.join(tempfile.gettempdir(), 'mix-runtime-{}.json'.format(os.getpid()))
    with open(destination, 'w', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print('MIX diagnostic report: ' + destination)
    return report


if __name__ == '__main__':
    main()
