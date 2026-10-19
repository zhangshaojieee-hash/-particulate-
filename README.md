# Instruct-Particulate Relay Adapter

这是一个用于同步项目本地修改的适配器仓库，不是 Instruct-Particulate 官方源码镜像，也不包含官方模型权重。

## 包含内容

- `official-patch/app.py.relay.patch`：官方 `app.py` 的小范围补丁，包含中转站调用和有限显存的 query batch 配置；
- `instruct_particulate/utils/vision_relay.py`：官方 Space 内使用的 OpenAI-compatible 多模态 relay；
- `ai4d/`：项目侧 Structure JSON 适配器、结构校验器和相关辅助代码；
- `docs/local-deployment.md`：组员本地部署指南；
- `tests/`：项目适配器的测试代码。

仓库不包含：

- 官方 Space 的完整源码；
- Instruct-Particulate、PartField、CLIP 或其他模型权重；
- Hugging Face/Conda/Python 缓存；
- 运行输出、用户模型和 API Key。

## 给组员的同步步骤

### 1. 获取官方 Space

```bash
mkdir -p ~/projects/ai4d
cd ~/projects/ai4d
git clone https://huggingface.co/spaces/rayli/instruct-particulate
cd instruct-particulate
```

如果组员已经有官方 Space，只需确认目录是干净且版本与项目要求一致。

### 2. 获取本同步仓库

在另一个目录执行：

```bash
cd ~/projects/ai4d
git clone https://github.com/zhangshaojieee-hash/-particulate-.git particulate-adapter-release
```

### 3. 安装官方 relay 文件

```bash
cp particulate-adapter-release/instruct_particulate/utils/vision_relay.py \
  instruct-particulate/instruct_particulate/utils/vision_relay.py
```

### 4. 应用官方 app 补丁

```bash
cd instruct-particulate
git apply ../particulate-adapter-release/official-patch/app.py.relay.patch
```

如果 `git apply` 提示文件已有相同修改，说明补丁可能已经应用过，不要重复应用。可以检查：

```bash
grep -n "call_auto_kinematics_model_via_relay" app.py
ls instruct_particulate/utils/vision_relay.py
```

### 5. 安装依赖和验证

请按照同步仓库中的部署文档继续：

```text
docs/local-deployment.md
```

然后在官方 Space 目录启动 `app.py`。本方案统一使用：

```text
http://localhost:7860/
```

## 中转站配置

中转站必须支持：

```text
POST {base_url}/chat/completions
```

并支持多模态 `image_url` 和合法 JSON 文本返回。启动前在同一个 WSL shell 设置：

```bash
export AI4D_VISION_BASE_URL="https://你的中转站域名/v1"
export AI4D_VISION_MODEL="中转站实际提供的视觉模型名"
read -s AI4D_VISION_API_KEY
export AI4D_VISION_API_KEY
```

API Key 只保存在本地环境变量中，不要提交到 GitHub。

## 4 GB 显存

RTX 3050 4 GB 或类似显卡建议使用：

```bash
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export INSTRUCT_PARTICULATE_QUERY_BATCH_SIZE=4096
```

默认总 query 数仍为 `51200`。如果仍然 OOM，再使用 `2048`；只有必要时才减少总 query 数。

## Structure JSON 适配器

官方推理完成后，可在拥有官方输出目录的机器上运行：

```bash
cd particulate-adapter-release
PYTHONPATH=. python -m ai4d.adapters.particulate /path/to/official/output
```

适配器会在官方输出目录旁生成 `structure.json`。该文件是候选结构，必须经过人工审核，不能直接作为打印设备参数、磁场强度、电流、PWM 或 G-code。

## 来源和许可

本仓库中的 `instruct_particulate/utils/vision_relay.py` 是为官方 Space 编写的项目修改，官方 Space 的原始代码、模型、第三方依赖和许可证仍以其上游仓库为准：

```text
https://huggingface.co/spaces/rayli/instruct-particulate
```

`partfield/` 上游代码包含 NVIDIA License。组员在公开或再分发相关内容前，应自行确认上游许可证和适用范围。本仓库只发布适配器和补丁，不重新分发模型权重。

## 安全边界

- 不提交 API Key、代理认证信息或个人路径中的敏感文件；
- 不提交模型权重和 Hugging Face 缓存；
- 不把 AI 输出直接转换为真实设备执行命令；
- 自动识别结果必须人工确认后才能进入后续规划流程。
