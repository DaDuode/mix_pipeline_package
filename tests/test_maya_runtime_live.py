# -*- coding: utf-8 -*-
"""Opt-in local Serve -> downloaded Rez packages -> isolated Maya smoke check.

Run with the launcher's bundled Python 3.7 while local Serve is running.
The probe never connects to an existing Maya session.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BASE = 'http://127.0.0.1:8765'
LIBS = ROOT / 'mix_studio_client/public/python/libs'


def probe():
    import maya.standalone
    maya.standalone.initialize(name='python')
    try:
        import mix_maya
        import mix_toolkit
        import maya.cmds as cmds
        report = mix_maya.INITIALIZATION_REPORT
        assert report['status'] == 'ready', report
        assert report['source'] == 'project_template', report
        assert report['version'] == '1.0.2', report
        assert report['attributes'] == ['api'], report
        assert report['scripts'] == [] and not report['config_loaded'], report
        assert mix_maya.ATTRIBUTES['api'].save is mix_maya.api.save
        assert mix_maya.api.current_version() == '2024'
        assert '1.0.2' in mix_maya.api.__file__
        assert not cmds.file(query=True, modified=True)
        assert not cmds.file(query=True, sceneName=True)
        diagnostic = mix_toolkit.diagnose()
        assert diagnostic['server'] == 'healthy', diagnostic['checks']
        assert diagnostic['configuration']['engine']['version'] == '1.0.2'
        assert mix_toolkit.get_plugin_state('mix_maya')['status'] == 'ready'
        output = {'initialization': report, 'maya_version': mix_maya.api.current_version(),
                  'scene_unchanged': True, 'packages': diagnostic['packages'],
                  'configured_runtime': diagnostic['configuration']['plugin_runtime']}
        Path(sys.argv[2]).write_text(json.dumps(output, indent=2), encoding='utf-8')
        print('Downloaded 1.0.2 runtime and api attribute initialized successfully in Maya 2024')
    finally:
        maya.standalone.uninitialize()


def main():
    url = BASE + '/api/client/software_templates/resolve?project_code=proj_mxdckz&step_code=Mod&software_code=maya&software_version=2024&strict_project=true'
    with urllib.request.urlopen(url, timeout=15) as response:
        payload = json.load(response)
    assert payload['code'] == 200
    config = payload['data']
    assert config['engine']['version'] == '1.0.2'
    manifest = json.loads((ROOT / 'mix_pipeline_package/package_output/plugin-runtime-1.0.2/manifest.json').read_text(encoding='utf-8'))
    hashes = {item['code']: item['sha256'] for item in manifest}
    with tempfile.TemporaryDirectory(prefix='mix-live-runtime-') as tmp:
        target = Path(tmp)
        warehouse = target / 'packages'
        warehouse.mkdir()
        requested = []
        for plugin in config['plugins']:
            code = plugin['code']
            assert code in hashes and plugin['version'] == '1.0.2'
            with urllib.request.urlopen(BASE + plugin['zip_url'], timeout=15) as response:
                data = response.read()
            assert hashlib.sha256(data).hexdigest() == hashes[code]
            archive = target / (code + '.zip')
            archive.write_bytes(data)
            with zipfile.ZipFile(str(archive)) as zipped:
                for member in zipped.namelist():
                    resolved = (warehouse / member).resolve()
                    assert warehouse.resolve() in resolved.parents
                zipped.extractall(str(warehouse))
            requested.append(code + '-1.0.2')
        sys.path.append(str(LIBS))
        from rez.resolved_context import ResolvedContext
        context = ResolvedContext(requested, package_paths=[str(warehouse)])
        assert context.success, context.failure_description
        # Match execute_shell's inherited parent environment; get_environ()
        # returns Rez's changes, not every Windows variable (SystemRoot, etc.).
        env = dict(os.environ)
        env.update(context.get_environ(parent_environ=env))
        env.update(DCC_BASE_URL=BASE, DCC_APP_CODE='MIX', DCC_PYTHON_LIBS=str(LIBS),
                   MIX_SOFTWARE_CODE='maya', MIX_SOFTWARE_VERSION='2024', MIX_SOFTWARE_ENGINE_CODE='mix_maya',
                   MAYA_APP_DIR=str(target / 'maya-user'), PYTHONIOENCODING='utf-8')
        env['MIX_CONTEXT_JSON'] = json.dumps({'Project': {'id': 'live-probe', 'code': 'proj_mxdckz'},
                                            'Entity': {'id': 'live-probe', 'code': 'probe', 'type': 'Asset', 'asset_type': 'Chars'},
                                            'Step': {'id': 'live-probe', 'code': 'Mod'},
                                            'Task': {'id': 'live-probe', 'code': 'Mod'},
                                            'Software': {'code': 'maya', 'version': '2024', 'engine_code': 'mix_maya'}})
        result_file = ROOT / 'mix_studio_serve/backend/tests/artifacts/plugin-runtime-live-1.0.2.json'
        command = [r'C:\Program Files\Autodesk\Maya2024\bin\mayapy.exe', str(Path(__file__).resolve()), '--probe', str(result_file)]
        process = subprocess.run(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
        print(process.stdout.decode('utf-8', errors='replace'))
        print(process.stderr.decode('utf-8', errors='replace'))
        assert process.returncode == 0, process.returncode
        print('Live report: ' + str(result_file))
        assert target.parent.resolve() == Path(tempfile.gettempdir()).resolve()
        assert target.name.startswith('mix-live-runtime-')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--probe':
        probe()
    else:
        main()
