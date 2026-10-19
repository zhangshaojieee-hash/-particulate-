# Instruct-Particulate 本地部署

> 目标：在 Windows + WSL2 中启动官方应用，并通过视觉中转站完成自动运动学提取。
>
> 完成后访问：`http://localhost:7860/`

## 开始前

本文所有命令都在 **WSL Ubuntu 终端** 中执行，不是在 Windows PowerShell 中执行。

需要：WSL2 Ubuntu 22.04、NVIDIA GPU、至少 4 GB 显存、已准备好的视觉中转站 API Key，以及至少数 GB 可用磁盘空间。4 GB 显存电脑按本文的 `4096` 配置运行；8 GB 以上通常可以去掉显存限制变量。

如果还没有 WSL2 Ubuntu，请先在 Windows PowerShell（管理员）中执行 `wsl --install -d Ubuntu-22.04`，重启后首次打开 Ubuntu 完成 Linux 用户创建。NVIDIA 驱动应安装在 Windows 中；WSL 内不要安装 Linux NVIDIA 驱动或系统级 CUDA Toolkit。

本文只发布适配器和补丁，不包含模型权重。首次启动会自动下载模型，可能需要数 GB 磁盘空间。

先检查 GPU 是否可见：

```bash
nvidia-smi
```

如果提示找不到命令，先不要继续安装项目，需先让 Windows NVIDIA 驱动和 WSL GPU 支持正常工作。

再检查 Hugging Face 是否可访问。全新 Ubuntu 如果还没有 `curl`，先安装它：

```bash
command -v curl >/dev/null || { sudo apt update && sudo apt install -y curl; }
curl -4 -I --connect-timeout 10 https://huggingface.co
```

如果返回 `HTTP/2 200` 或类似成功响应，直接继续。如果解析超时、连接超时或失败，先配置 Clash 代理：

```bash
WIN_HOST=$(ip route | awk '/default/ {print $3; exit}')
export HTTPS_PROXY="http://${WIN_HOST}:7897"
export HTTP_PROXY="http://${WIN_HOST}:7897"
export https_proxy="$HTTPS_PROXY"
export http_proxy="$HTTP_PROXY"
```

其中 `7897` 换成 Clash Verge 的实际 Mixed Port，并确认已打开 `Allow LAN`。配置后重新测试：

```bash
curl -4 -I --connect-timeout 10 https://huggingface.co
```

代理测试仍失败时先不要继续 clone；确认 Clash 正在运行、端口正确，并把这条命令和输出发给 AI。

## 1. 安装基础工具并获取代码

先安装 Git LFS 和 Blender，再 clone 官方 Space。顺序不要调换：

```bash
sudo apt update
sudo apt install -y blender git git-lfs curl wget
git lfs install

mkdir -p ~/projects/ai4d
cd ~/projects/ai4d
git clone https://huggingface.co/spaces/rayli/instruct-particulate
git clone https://github.com/zhangshaojieee-hash/-particulate-.git particulate-adapter-release

cd instruct-particulate
# 补丁按这个官方版本生成，固定版本可避免上游更新造成不兼容。
git checkout --detach 290fe6cbd47b1e8db5386160d61b2272ca2773a2
git lfs pull
test -z "$(git status --porcelain)" || { echo "官方目录不是干净状态，请先处理本地修改"; exit 1; }

cd ..
cp particulate-adapter-release/instruct_particulate/utils/vision_relay.py \
  instruct-particulate/instruct_particulate/utils/vision_relay.py
cd instruct-particulate
git apply --check ../particulate-adapter-release/official-patch/app.py.relay.patch
git apply ../particulate-adapter-release/official-patch/app.py.relay.patch

grep -n "call_auto_kinematics_model_via_relay" app.py
ls instruct_particulate/utils/vision_relay.py
```

最后两条命令应能找到 relay 代码。若 `git apply --check` 失败，先不要继续启动，通常是官方 Space 版本不同或目录有本地修改；把完整错误日志发给 AI。如果官方目录已经存在，先确认它是上面固定的官方提交，再 clone 适配器仓库并执行复制、检查和 `git apply` 步骤。若提示补丁已应用，先检查：

```bash
grep -n "call_auto_kinematics_model_via_relay" app.py
ls instruct_particulate/utils/vision_relay.py
```

## 2. 安装环境

如果已经有 `particulate-env`，直接激活即可：

```bash
source "$HOME/miniforge3/etc/profile.d/conda.sh"
conda activate particulate-env
python --version
```

应显示 Python 3.10.x。若 `conda` 或环境路径不存在，按下面的 Miniforge 安装步骤执行。

如果没有 Miniforge，先安装它：

```bash
cd ~
wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh -O Miniforge3.sh
bash Miniforge3.sh -b -p "$HOME/miniforge3"
rm Miniforge3.sh
```

然后创建并激活项目环境。若环境已经存在，`conda create` 会提示；此时跳过创建，直接执行激活命令：

```bash
source "$HOME/miniforge3/etc/profile.d/conda.sh"
conda create -n particulate-env python=3.10 -y
conda activate particulate-env
```

安装系统依赖和 Python 依赖：

```bash
sudo apt update
sudo apt install -y blender git git-lfs curl wget
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
read -r -s -p "API Key: " AI4D_VISION_API_KEY; echo
export AI4D_VISION_API_KEY

export BLENDER_BIN=/usr/bin/blender
export GRADIO_SERVER_PORT=7860
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export INSTRUCT_PARTICULATE_QUERY_BATCH_SIZE=4096

CUDA_VISIBLE_DEVICES=0 python app.py
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
