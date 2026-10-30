# Runtime foundation: first iteration

This iteration adds read-only configuration queries and diagnostics. It does not
open/save scenes, run server scripts, change task status, or switch tasks.

## Serve API

`ServeClient` is independent of Maya, Qt and the legacy `MixSDK` application
authorization. Construction is offline; each method connects only when called.
`MixSDK` keeps its existing behavior for third-party integrations.

```python
from mix_api import ServeClient

with ServeClient.from_environment() as client:
    print(client.health())
    config = client.resolve_software_template(
        project_code='proj_mxdckz', step_code='Mod',
        software_code='maya', software_version='2024',
    )
```

Other queries: `get_cgt_config()`, `get_softwares()`, `get_plugins()`.
No matching template returns `None`; HTTP/transport/application errors raise
`ServeAPIError`. `status_code` and `code` distinguish HTTP and application errors.
The default connection/read timeouts are 3/10 seconds.

## Toolkit

```python
import mix_toolkit

context = mix_toolkit.get_runtime_context()
config = mix_toolkit.get_runtime_configuration()
resolver = mix_toolkit.get_path_resolver(configuration=config)
report = mix_toolkit.diagnose()
offline_report = mix_toolkit.diagnose(check_server=False)
```

The existing engine context takes priority over the launch environment so a task
switch does not return stale launch data. Queries return copies and never create
an engine. Configuration queries strictly match the current project, step,
software and version. They use the current server configuration, not a frozen
copy of the launch configuration.

`Context` now has one backing dictionary for attributes, `set_entity()`,
`update_key()` and `to_dict()`. Constructor inputs and exported dictionaries are
copied; nested edits made through `context.Task` update that context only.

Diagnostics include the task identity, loaded package paths/versions, engine
startup state, server health, configured engine and storage YAML validation.
They omit credentials, API keys, raw environment values and script contents.
Placeholder entity/step IDs equal to `1` produce warnings for later CGT identity
work. Missing context or malformed YAML is reported as an error.

## Inspect the already-running Maya

Run this in Maya's **Python** Script Editor:

```python
import runpy
runpy.run_path(
    r'D:/td/mix_dcc/mix_pipeline_package/tools/diagnose_maya.py',
    run_name='__main__',
)
```

The script makes the new diagnostic modules discoverable alongside the existing
1.0.0 packages. It does not reload or replace existing engine/context objects.
It prints the report and saves `%TEMP%/mix-runtime-<Maya PID>.json`. Applying the
`Context` fix to a running engine requires loading the updated packages in a new
Maya session. The launch snapshot integration test uses a separate Python
process; it does not establish access to the GUI Maya session.

## Verification

```powershell
.\mix_studio_client\public\python\win\python377\python.exe mix_pipeline_package/tests/test_runtime_foundation.py -v
& 'C:/Program Files/Autodesk/Maya2024/bin/mayapy.exe' mix_pipeline_package/tests/test_runtime_foundation.py -v
```

Optionally set `MIX_TEST_LAUNCH_FILE` to an existing launcher JSON payload to
check its task against the local Serve API. Tests read only the needed task and
software fields and never output the credentials in that file.
