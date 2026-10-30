# Maya 插件运行时 1.0.2

2026-10-30：已发布到本机 Mix Studio Serve，三个包均为 `1.0.2`：
`mix_api`、`mix_toolkit`、`mix_maya`。Maya 软件的引擎绑定和现有活动
Maya 模板的基础依赖已同步。原包、原版本记录仍保留。

## 当前实际配置和验证结果

| 内容 | 当前状态 |
| --- | --- |
| Maya 引擎包 | `mix_maya-1.0.2`，已验证下载及 Rez 解析 |
| 基础依赖 | `mix_api-1.0.2`、`mix_toolkit-1.0.2`，已验证实际导入 |
| `mix_maya` 属性 | 开启；存在一个 `api` 属性；独立 Maya 2024 验证加载成功 |
| `mix_maya` 普通脚本 | 开关开启，但没有脚本记录 |
| `mix_maya` 配置文件 | 开关开启，但没有配置记录 |

插件普通脚本与项目模板的前置脚本、通用脚本、启动脚本属于不同配置。
本次插件运行时会自动加载属性、注册普通脚本、解析默认配置；普通脚本
通过 `mix_toolkit.run_plugin_script('插件代码', '脚本代码', ...)` 显式调用 `main()`。

后台解析接口现在附带 `plugin_runtime`，按当前项目模板实际选中的插件版本返回
属性、脚本和配置，并尊重各自开关。定义本身沿用后台已有的数据模型，属于插件，
由该插件各版本共享；包版本仍由具体版本 ID 锁定。

旧实现依赖受旧应用密钥保护的属性接口，失败后静默忽略。新版插件从项目模板
解析结果加载，并提供 `ready`、`degraded`、`unavailable` 等状态。
旧 `MixSDK` 的第三方应用授权机制仍沿用原有规则。

## API 修复

维护入口是 `mix_maya/src/api.py`。后台 `api` 属性现为引用该入口的薄桥接，
避免旧脚本覆盖新版文件操作；自定义属性模块可通过 `mix_maya.ATTRIBUTES` 访问。
同名 `api` 属性中的额外 helper 可以扩展本地 API，已有核心方法保留本地实现。

- 使用原生 `maya.cmds`，无需 PyMEL。
- `current_version()` 返回真实版本；版本不匹配抛异常，不退出 Maya。
- `open()`、`new()` 默认保护未保存内容；确需丢弃时显式传 `force=True`。
- `save(path)` 仅保存目标文件一次，不先覆盖旧版本；目标已存在时需 `overwrite=True`。
- `copy_scene(path)` 导出副本，保留当前场景名称和修改状态。
- `create_reference()` 检查文件和命名空间。
- `set_env()` 更新任务环境，不改场景或工作空间。
- 建模层级识别当前项目的 `Mod`、`Chars` 命名；建组可重复调用。

保存与导出行为参考 [Autodesk Maya 2024 file 命令文档](https://help.autodesk.com/cloudhelp/2024/ENU/Maya-Tech-Docs/CommandsPython/file.html)。

## 使用和检查

保存现有工作，然后从 Launcher 重新启动 Maya，即可下载并加载新包。
已打开的 Maya 进程不会自动替换内存中的旧模块。无需重新安装 Launcher。

在新启动的 Maya Python 编辑器运行：

```python
import mix_maya
import mix_toolkit

print(mix_maya.INITIALIZATION_REPORT)
# 应包含 status='ready', version='1.0.2', attributes=['api']
print(mix_maya.api.current_version())
print(mix_maya.api.__file__)
print(mix_toolkit.get_plugin_state('mix_maya'))
```

完整诊断使用 `mix_toolkit.diagnose()`；仅本地诊断使用
`mix_toolkit.diagnose(check_server=False)`。

## 验证和回溯

- 12 项独立 Maya 2024 文件操作测试全部通过。
- 8 项属性/配置/脚本加载测试全部通过。
- 7 项后台引擎和运行时解析测试全部通过。
- 原基础运行时测试：17 项通过，1 项依赖外部启动文件而跳过。
- 真实接口下载三个发布包并校验 SHA256，以 Rez 解析后运行独立 Maya，
  确认 `api` 属性状态为 `ready`，并确认测试未修改场景。

本机配置备份：
`mix_studio_serve/backend/tests/artifacts/plugin-runtime-before-20261030_031227_f6ca1599.json`。
备份包含更新前受影响的行，不包含账号凭据表；恢复时应先核对之后的人工配置修改。

发布包与校验清单位于 `package_output/plugin-runtime-1.0.2/`。
真实链路报告位于
`mix_studio_serve/backend/tests/artifacts/plugin-runtime-live-1.0.2.json`；
报告中的包路径来自已清理的独立临时测试环境。

真实链路测试入口为 `tests/test_maya_runtime_live.py`，需本机后台运行、Maya 2024
以及 Launcher 附带的 Python 3.7。该测试只连接新建的独立 Maya 测试进程。
