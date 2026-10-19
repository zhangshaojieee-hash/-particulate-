# Instruct-Particulate 本地部署操作指南

> 适用对象：需要在自己的 Windows + WSL2 电脑上运行本地 Instruct-Particulate Gradio 应用的组员。
>
> 本文对应当前已经验证成功的部署方式：官方应用直接运行在 `7860`，自动运动学的视觉请求通过 OpenAI-compatible 中转站发送。本文不使用 `7862` 包装器，也不把任何真实 API Key 写入文件。

## 1. 最终运行链路

```text
Windows NVIDIA 驱动
        |
        v
WSL2 Ubuntu 22.04 + Conda/Python 3.10
        |
        v
官方 instruct-particulate/app.py
        |
        +--> Blender：生成 4 个自动运动学视角
        |
        +--> 中转站视觉模型：识别部件、关节和点提示
        |
        +--> Instruct-Particulate：完成 3D 分割和运动推理
        |
        v
浏览器访问 http://localhost:7860/
```

API Key 只负责自动运动学的视觉识别，不负责替代 Instruct-Particulate 的 3D checkpoint。

## 2. 硬件和软件要求

### 2.1 推荐硬件

- Windows 10/11；
- WSL2；
- Ubuntu 22.04；
- NVIDIA GPU，并且 WSL 中可以运行 `nvidia-smi`；
- 至少 4 GB 显存，建议 8 GB 或更多；
- 至少 20 GB 可用磁盘空间。首次启动会下载官方 checkpoint、PartField 资源和 CLIP 资源，实际占用取决于缓存和临时文件；
- 稳定的网络，或可用的 Clash/HTTP 代理。

4 GB 显存可以运行，但必须使用较小的 query batch。本文的验证机是 RTX 3050 4 GB，使用：

```bash
export INSTRUCT_PARTICULATE_QUERY_BATCH_SIZE=4096
```

### 2.2 不需要安装的东西

当前版本不需要在 WSL 中额外安装：

- Linux NVIDIA 驱动；
- 系统级 CUDA Toolkit；
- `nvcc`；
- 第二套旧版 PyTorch；
- PartField 独立环境。

项目使用 PyTorch `2.8.0+cu128`，由 Windows NVIDIA 驱动提供 GPU 支持。

## 3. Windows 端准备

### 3.1 安装或确认 WSL2

在 Windows PowerShell 中执行：

```powershell
wsl --install -d Ubuntu-22.04
```

如果 WSL 已经安装，检查发行版：

```powershell
wsl -l -v
```

应看到 Ubuntu 发行版的 VERSION 为 `2`。首次打开 Ubuntu 时创建 Linux 用户名和密码。

### 3.2 安装 NVIDIA 驱动

在 Windows 安装支持 WSL 的 NVIDIA 驱动。安装后重启 Windows，再在 Ubuntu 中检查：

```bash
nvidia-smi
```

能够看到 GPU 名称和显存即可。不要在 WSL 中运行 `sudo apt install nvidia-driver`。

### 3.3 可选：确认 Clash 代理端口

如果 WSL 不能访问 Hugging Face 或中转站，在 Clash Verge 中确认：

- Mixed Port，本文示例使用 `7897`；
- 已开启 `Allow LAN`；
- 必要时开启 TUN Mode。

每台电脑的端口可能不同，使用实际端口替换 `7897`。

## 4. WSL 基础工具

打开 Ubuntu 22.04 终端，在 Ubuntu 中执行以下命令：

```bash
sudo apt update
sudo apt install -y git git-lfs curl wget ca-certificates build-essential blender

git lfs install
blender --version
```

自动运动学功能需要 Blender。验证成功时会输出 Blender 版本。

## 5. 安装 Miniforge 和 Python 环境

如果电脑还没有 Miniforge，在 Ubuntu 中执行：

```bash
cd ~
wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh -O Miniforge3.sh
bash Miniforge3.sh -b -p "$HOME/miniforge3"
rm Miniforge3.sh
source "$HOME/miniforge3/etc/profile.d/conda.sh"
conda init bash
```

重新打开 Ubuntu，或者当前终端执行：

```bash
source "$HOME/miniforge3/etc/profile.d/conda.sh"
```

创建项目环境：

```bash
conda create -n particulate-env python=3.10 -y
conda activate particulate-env
python --version
```

应显示 Python 3.10.x。

## 6. 获取官方 Space 和项目修改

### 6.1 目录建议

本文使用以下目录。组员可以改成自己的路径，但后续命令要保持一致：

```text
/home/<用户名>/projects/ai4d/instruct-particulate
```

创建目录：

```bash
mkdir -p ~/projects/ai4d
cd ~/projects/ai4d
```

### 6.2 下载官方 Space

网络正常时：

```bash
git clone https://huggingface.co/spaces/rayli/instruct-particulate
cd ~/projects/ai4d/instruct-particulate
```

如果完整 clone 因网络或大文件失败，不要反复混装依赖。先检查目录是否已经存在，并使用可用的 Hugging Face 下载方式恢复。

### 6.3 必须同步的本地修改

官方原始 Space 默认使用官方 Gemini/OpenAI provider。当前项目为了接入 OpenAI-compatible 中转站，对官方目录做了两处功能修改：

1. `app.py`：在自动运动学调用处检测 `AI4D_VISION_BASE_URL` 或 `OPENAI_BASE_URL`，存在时转到中转站；
2. `instruct_particulate/utils/vision_relay.py`：发送多模态 `chat/completions` 请求，并解析 JSON 返回值。

组员需要先 clone 本同步仓库，再从中同步以下文件：

```text
official-patch/app.py.relay.patch
instruct_particulate/utils/vision_relay.py
```

同步步骤和补丁应用命令见本仓库根目录 `README.md`。仅仅重新 clone 原始 Hugging Face Space 而不同步这两个代码文件，设置中转站变量也不会生效。

同步后检查：

```bash
grep -n "call_auto_kinematics_model_via_relay" app.py
ls instruct_particulate/utils/vision_relay.py
```

第一条命令应能找到官方 app 中的 relay 分支，第二条命令应能列出文件。

## 7. 安装 Python 依赖

在官方目录和 `particulate-env` 环境中执行：

```bash
cd ~/projects/ai4d/instruct-particulate
conda activate particulate-env
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

当前依赖文件使用 PyTorch CUDA 12.8 wheel。不要再安装旧的 PyTorch 2.4/CUDA 12.4 组合。

如果启动时出现 `pkg_resources` 与 Lightning 相关错误，执行：

```bash
python -m pip install --force-reinstall setuptools==80.9.0
```

验证核心环境：

```bash
python -c "import torch; print('torch:', torch.__version__); print('torch cuda:', torch.version.cuda); print('cuda available:', torch.cuda.is_available()); print('device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

正常结果应包含：

```text
torch: 2.8.0+cu128
torch cuda: 12.8
cuda available: True
```

## 8. 配置网络访问

### 8.1 直接网络

如果以下命令成功，可以不设置代理：

```bash
curl -4 -I --connect-timeout 10 https://huggingface.co
```

### 8.2 通过 Clash Verge

如果 WSL 直连 Hugging Face 解析超时，先在 Clash Verge 确认允许局域网访问，然后在 Ubuntu 中执行：

```bash
WIN_HOST=$(ip route | awk '/default/ {print $3; exit}')

export HTTP_PROXY="http://${WIN_HOST}:7897"
export HTTPS_PROXY="http://${WIN_HOST}:7897"
export ALL_PROXY="http://${WIN_HOST}:7897"
export http_proxy="$HTTP_PROXY"
export https_proxy="$HTTPS_PROXY"
export all_proxy="$ALL_PROXY"
export no_proxy="127.0.0.1,localhost"
```

将 `7897` 替换成 Clash Verge 实际 Mixed Port。验证：

```bash
curl -4 -I --connect-timeout 10 https://huggingface.co
```

出现 `HTTP/2 200` 或 `HTTP/1.1 200` 表示代理链路可用。

如果官方域名仍然不可用，但镜像站可用，可以临时使用：

```bash
export HF_ENDPOINT=https://hf-mirror.com
curl -4 -I --connect-timeout 10 https://hf-mirror.com
```

不要同时设置错误的 `HF_ENDPOINT` 和错误的代理；先用 `curl` 验证路径，再启动应用。

## 9. 配置视觉中转站

当前官方修改后的代码要求中转站支持以下协议：

```text
POST {base_url}/chat/completions
```

其中请求需要支持：

- OpenAI-compatible Chat Completions；
- 多模态 `image_url`；
- 4 张 Blender PNG 图片；
- 返回 JSON 文本，内容符合官方自动运动学解析器要求。

模型返回的 JSON 至少需要包含：

```json
{
  "total_links": 2,
  "links": [
    {
      "id": 0,
      "name": "body",
      "point_prompt": {
        "image_id": 0,
        "x": 500,
        "y": 500
      }
    }
  ],
  "joints": []
}
```

实际字段以官方 `kinematic-inference-system-prompt.md` 和解析器为准。中转站模型名称必须使用服务商实际提供的名称，例如 `gpt-5.6-luna`；不要默认填写 `gemini-3.5-flash`。

在当前终端设置：

```bash
export AI4D_VISION_BASE_URL="https://你的中转站域名/v1"
export AI4D_VISION_MODEL="中转站实际提供的视觉模型名"
read -s AI4D_VISION_API_KEY
export AI4D_VISION_API_KEY
```

输入 API Key 时终端不会显示字符，输入完成后按回车。不要把 Key 写进：

- Python 源码；
- README 或日志；
- 截图；
- Git；
- `.bash_history` 或共享配置文件。

`AI4D_VISION_BASE_URL` 应填写到 `/v1`，不要把 `/chat/completions` 也写进去：

```bash
# 正确
export AI4D_VISION_BASE_URL="https://example.com/v1"

# 错误
export AI4D_VISION_BASE_URL="https://example.com/v1/chat/completions"
```

## 10. 4 GB 显存配置

RTX 3050 4 GB 或类似显卡建议先使用：

```bash
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export INSTRUCT_PARTICULATE_QUERY_BATCH_SIZE=4096
```

这只降低每批 query 的显存峰值，默认总 query 数仍为 `51200`。如果仍然 OOM，再降到：

```bash
export INSTRUCT_PARTICULATE_QUERY_BATCH_SIZE=2048
```

只有在仍无法运行时才减少总 query 数：

```bash
export INSTRUCT_PARTICULATE_NUM_QUERY_POINTS=32768
```

减少总 query 数可能影响分割精度。8 GB 或更多显存可以先不设置这两个参数，使用官方默认值；如仍 OOM，再按实际显存降低 batch。

## 11. 启动官方 7860

建议每次启动前确认在正确环境和目录：

```bash
cd ~/projects/ai4d/instruct-particulate
source "$HOME/miniforge3/etc/profile.d/conda.sh"
conda activate particulate-env
```

然后执行一套完整启动命令。下面示例按 4 GB 显存编写：

```bash
export BLENDER_BIN=/usr/bin/blender
export GRADIO_SERVER_PORT=7860
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export INSTRUCT_PARTICULATE_QUERY_BATCH_SIZE=4096

export AI4D_VISION_BASE_URL="https://你的中转站域名/v1"
export AI4D_VISION_MODEL="中转站实际提供的视觉模型名"
read -s AI4D_VISION_API_KEY
export AI4D_VISION_API_KEY

CUDA_VISIBLE_DEVICES=0 \
  /home/你的Linux用户名/miniforge3/envs/particulate-env/bin/python app.py
```

如果使用当前用户的 `$HOME`，推荐写成更通用的形式：

```bash
CUDA_VISIBLE_DEVICES=0 \
  "$HOME/miniforge3/envs/particulate-env/bin/python" app.py
```

官方启动入口默认监听：

```text
http://localhost:7860/
```

不要同时启动第二个 `app.py`，否则会出现端口占用、重复加载模型或显存互相争用。

停止服务：在运行 `app.py` 的 Ubuntu 终端按：

```text
Ctrl+C
```

如果程序异常退出后显存没有释放，先检查：

```bash
nvidia-smi
```

再结束对应的 Python 进程，确认显存释放后再重启。

## 12. 第一次启动会下载什么

第一次启动可能出现：

```text
Prefetching PartField checkpoint assets
Prefetching CLIP text assets: openai/clip-vit-large-patch14
Downloading bytes: ...
Reconstructing ...
```

这是正常的模型缓存过程，不是重复创建模型。下载内容包括：

- Instruct-Particulate 官方 checkpoint；
- PartField checkpoint 或特征资源；
- `openai/clip-vit-large-patch14` CLIP 文本资源。

缓存通常位于：

```bash
~/.cache/huggingface/hub
```

查看空间：

```bash
du -sh ~/.cache/huggingface 2>/dev/null || true
df -h ~
```

下载被中断时，重新启动通常会复用已经完成的缓存。不要在缓存未完成时强行设置 `HF_HUB_OFFLINE=1`。

## 13. 完整测试步骤

### 13.1 启动检查

终端应出现类似：

```text
Running on local URL: http://127.0.0.1:7860
```

另开一个 Ubuntu 终端检查：

```bash
curl -I http://127.0.0.1:7860/
```

Windows 浏览器打开：

```text
http://localhost:7860/
```

### 13.2 自动运动学测试

1. 在页面上传一个 `.glb` 或 `.obj`；
2. 选择正确的 upright orientation；
3. 点击自动运动学提取；
4. 等待 Blender 完成 4 个视角；
5. 等待中转站返回；
6. 检查页面是否生成部件、关节和点提示；
7. 再运行后续 3D 推理。

成功日志应包含：

```text
Blender quit
Loading auto-kinematics view 1/4 ...
Loading auto-kinematics view 4/4 ...
AI4D vision relay response received: host=..., model=..., views=4
Moving preloaded model weights to CUDA
```

最终应看到预测结果、可视化结果和导出按钮。

## 14. 常见问题

### 14.1 `Could not find Blender`

检查：

```bash
which blender
blender --version
export BLENDER_BIN=/usr/bin/blender
```

如果没有 Blender：

```bash
sudo apt update
sudo apt install -y blender
```

### 14.2 `Missing Gemini API key`

这表示程序没有进入中转站分支，或者没有设置中转站 Key。确认：

```bash
echo "$AI4D_VISION_BASE_URL"
echo "$AI4D_VISION_MODEL"
[ -n "$AI4D_VISION_API_KEY" ] && echo "API key is set" || echo "API key is missing"
```

不要使用 `echo "$AI4D_VISION_API_KEY"` 打印真实 Key。

如果设置了变量仍出现该错误，检查是否同步了修改后的 `app.py` 和 `vision_relay.py`。

### 14.3 `Temporary failure in name resolution`

这是 WSL DNS 或网络路径问题，不是 Python 依赖问题。先执行：

```bash
curl -4 -I --connect-timeout 10 https://huggingface.co
```

如使用 Clash，配置第 8.2 节的代理。确认 `Allow LAN` 和端口正确。

### 14.4 `LocalEntryNotFoundError` 或模型下载失败

先确认 Hugging Face 请求成功：

```bash
curl -4 -I --connect-timeout 10 https://huggingface.co
```

再检查缓存和磁盘：

```bash
du -sh ~/.cache/huggingface 2>/dev/null || true
df -h ~
```

必要时使用：

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

然后重新运行应用。

### 14.5 `CUDA out of memory`

首先停止当前服务，让显存释放：

```text
Ctrl+C
```

检查：

```bash
nvidia-smi
```

重新启动前设置：

```bash
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export INSTRUCT_PARTICULATE_QUERY_BATCH_SIZE=4096
```

仍然失败时改成：

```bash
export INSTRUCT_PARTICULATE_QUERY_BATCH_SIZE=2048
```

不要把 `query_batch_size = 4096` 当成 Bash 命令，也不要在赋值两边加空格。程序读取的是：

```bash
export INSTRUCT_PARTICULATE_QUERY_BATCH_SIZE=4096
```

### 14.6 中转站返回空内容或 JSON 解析失败

确认中转站：

- 支持视觉模型，而不是纯文本模型；
- 支持 `image_url` 多模态格式；
- 支持 `POST /v1/chat/completions`；
- 返回内容在 `choices[0].message.content`；
- 返回的是合法 JSON 文本；
- 模型名称是中转站实际支持的名称。

日志只会打印中转站主机、模型名和视图数量，不会打印 API Key。

### 14.7 端口被占用

检查：

```bash
ss -ltnp | grep ':7860'
```

停止旧服务后再启动。不要为了规避问题改用 `7862`，本部署文档统一使用官方 `7860`。

## 15. 部署完成检查表

- [ ] `nvidia-smi` 能看到 GPU；
- [ ] `blender --version` 能正常运行；
- [ ] `python --version` 为 3.10.x；
- [ ] `torch.cuda.is_available()` 为 `True`；
- [ ] `app.py` 中存在 relay 分支；
- [ ] `instruct_particulate/utils/vision_relay.py` 存在；
- [ ] Hugging Face 或镜像站可访问；
- [ ] 模型资源下载完成或缓存完整；
- [ ] 浏览器可以访问 `http://localhost:7860/`；
- [ ] Blender 能完成 4 个视角；
- [ ] 日志出现 `AI4D vision relay response received`；
- [ ] 自动运动学和后续 3D 推理完成；
- [ ] 没有 CUDA OOM；
- [ ] API Key 未写入文件、日志、截图或 Git。

## 16. 配置说明

每次打开新的 Ubuntu 终端时，Conda 激活、代理环境变量和 API 环境变量都可能需要重新设置。不要把真实 Key 直接写进共享文档或提交到 Git。

建议组员各自维护本地 shell 环境，但只共享以下非敏感内容：

```text
项目源码版本
Python 和 PyTorch 版本
GPU 型号和显存
中转站 base URL 的域名
中转站模型名
query batch 配置
错误日志中去除 Key 的部分
```

本地运行成功后，再进入统一 `Structure JSON`、人工审核和后续 MotionIntent 流程。自动识别结果必须经过人工确认，不能直接作为打印设备参数、磁场强度、电流、PWM 或 G-code 执行。
