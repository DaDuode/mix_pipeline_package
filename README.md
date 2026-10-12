# Mix Pipeline Packages (mix_pipeline_package)

通用数字资产与 DCC (Digital Content Creation) 管线工具包生态系统，由 `mix_studio_serve` 集中管理，供 `mix_studio_client` 自动化调度与 Rez 解析拉起。

## 目录结构与生态

```text
mix_pipeline_package/
├── tools/                      # 构建与一键发布 CLI 工具 (build_rez.py, publish.py)
├── docs/                       # 管线开发、DCC 规范与插件开发文档
├── mix_api/                    # 统一底层通信 SDK (MixSDK)
├── mix_toolkit/                # 核心通用 DCC 基础设施与引擎基类
├── mix_maya/                   # Autodesk Maya 集成环境与工具链
└── ...                         # 后续接入：Houdini, Blender, 3ds Max, Nuke, UE 等
```

## 快速使用

### 1. 构建 Rez 包
```bash
python tools/build_rez.py mix_toolkit --version 1.0.0
```

### 2. 发布到 Mix Studio Serve
```bash
python tools/publish.py mix_toolkit --version 1.0.0 --server http://127.0.0.1:8765 --api-key YOUR_KEY
```

## 规范约定
- 所有新包统一采用 `mix_<dcc/tool>` 标准命名。
- 环境变量统一遵从 `MSC_*` 与 `DCC_*` 规范。
- 遵循语义化版本规范 (SemVer)。
