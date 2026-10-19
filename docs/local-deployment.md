# Instruct-Particulate 本地部署

> 目标：在 Windows + WSL2 中启动官方应用，并通过视觉中转站完成自动运动学提取。
>
> 完成后访问：`http://localhost:7860/`

## 开始前

需要：WSL2 Ubuntu 22.04、NVIDIA GPU、至少 4 GB 显存、已准备好的视觉中转站API Key。4 GB 显存电脑按本文的 `4096` 配置运行；8 GB 以上通常可以去掉显存限制变量。

本文只发布适配器和补丁，不包含模型权重。首次启动会自动下载模型，可能需要数 GB 磁盘空间。

如果 WSL 已经能访问 Hugging Face，直接继续。如果访问超时，先配置 Clash 代理：

```bash
WIN_HOST=$(ip route | awk '/default/ {print $3; exit}')
export HTTPS_PROXY="http://${WIN_HOST}:7897"
export HTTP_PROXY="http://${WIN_HOST}:7897"
export https_proxy="$HTTPS_PROXY"
export http_proxy="$HTTP_PROXY"
```

其中 `7897` 换成 Clash Verge 的实际 Mixed Port，并确认已打开 `Allow LAN`。

## 1. 安装基础工具并获取代码

先安装 Git LFS 和 Blender，再 clone 官方 Space。顺序不要调换：

```bash
sudo apt update
sudo apt install -y blender git git-lfs curl
git lfs install

mkdir -p ~/projects/ai4d
cd ~/projects/ai4d
git clone https://huggingface.co/spaces/rayli/instruct-particulate
git clone https://github.com/zhangshaojieee-hash/-particulate-.git particulate-adapter-release

cp particulate-adapter-release/instruct_particulate/utils/vision_relay.py \
  instruct-particulate/instruct_particulate/utils/vision_relay.py
cd instruct-particulate
git apply ../particulate-adapter-release/official-patch/app.py.relay.patch
```

如果官方目录已经存在，只需 clone 适配器仓库，再执行复制和 `git apply` 两步。补丁重复应用会报错，遇到这种情况先检查：

```bash
grep -n "call_auto_kinematics_model_via_relay" app.py
ls instruct_particulate/utils/vision_relay.py
```

## 2. 安装环境

如果已经有 `particulate-env`，直接激活即可：

```bash
source "$HOME/miniforge3/etc/profile.d/conda.sh"
conda activate particulate-env
```

没有 Miniforge 时先安装并创建环境：

```bash
cd ~
wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh -O Miniforge3.sh
bash Miniforge3.sh -b -p "$HOME/miniforge3"
rm Miniforge3.sh
source "$HOME/miniforge3/etc/profile.d/conda.sh"
conda create -n particulate-env python=3.10 -y
conda activate particulate-env
```

安装系统依赖和 Python 依赖：

```bash
sudo apt update
sudo apt install -y blender git git-lfs curl
cd ~/projects/ai4d/instruct-particulate
git lfs install
python -m pip install -r requirements.txt
```

验证 GPU 和 Blender：

```bash
nvidia-smi
blender --version
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

应看到 GPU、Blender 版本，以及类似 `2.8.0+cu128 True` 的输出。

## 3. 配置并启动

把下面三项替换成中转站实际信息。API Key 只存在当前终端，不要写入文件或发到群里：

```bash
cd ~/projects/ai4d/instruct-particulate

export AI4D_VISION_BASE_URL="https://你的中转站域名/v1"
export AI4D_VISION_MODEL="中转站实际提供的视觉模型名"
read -s AI4D_VISION_API_KEY
export AI4D_VISION_API_KEY

export BLENDER_BIN=/usr/bin/blender
export GRADIO_SERVER_PORT=7860
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export INSTRUCT_PARTICULATE_QUERY_BATCH_SIZE=4096

CUDA_VISIBLE_DEVICES=0 \
  "$HOME/miniforge3/envs/particulate-env/bin/python" app.py
```

中转站必须支持：

```text
POST {base_url}/chat/completions
多模态 image_url
JSON 文本返回
```

`AI4D_VISION_BASE_URL` 填到 `/v1`，不要加 `/chat/completions`。模型名使用中转站实际提供的视觉模型名。

启动成功后打开：

```text
http://localhost:7860/
```

首次启动下载模型属于正常现象。完成自动运动学测试时，日志应出现：

```text
AI4D vision relay response received: host=..., model=..., views=4
```

## 网络和显存提示

如果 Hugging Face 访问超时，而电脑使用 Clash Verge，在 Clash 中打开 `Allow LAN`，然后在 WSL 执行：

```bash
WIN_HOST=$(ip route | awk '/default/ {print $3; exit}')
export HTTPS_PROXY="http://${WIN_HOST}:7897"
export HTTP_PROXY="http://${WIN_HOST}:7897"
```

`7897` 换成 Clash 的实际 Mixed Port。也可以临时使用：

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

如果出现 `CUDA out of memory`，先停止程序，再把 batch 改小：

```bash
export INSTRUCT_PARTICULATE_QUERY_BATCH_SIZE=2048
```

如果出现 `Could not find Blender`，执行：

```bash
sudo apt update && sudo apt install -y blender
export BLENDER_BIN=/usr/bin/blender
```

其他错误请把去除 API Key 后的完整日志发给 AI 分析。自动识别结果仍需人工确认，不能直接用于设备电流、PWM、磁场或 G-code 执行。
