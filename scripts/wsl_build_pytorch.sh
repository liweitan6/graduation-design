#!/bin/bash
set -e

echo "=========================================="
echo " Starting PyTorch GCOV Compilation Script "
echo "=========================================="

# 挂载目录切换 (进入 Windows E 盘)
TARGET_DIR="/mnt/e/BUAA/graduation-design/pytorch_gcov"
mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR"

if [ ! -d "pytorch" ]; then
    echo "[*] Cloning PyTorch..."
    # 浅克隆加快速度，去掉冗余的历史记录
    git clone --recursive --depth 1 https://github.com/pytorch/pytorch
else
    echo "[*] PyTorch directory exists."
fi

cd pytorch

echo "[*] Setting up Python virtual environment for PyTorch build..."
if [ ! -d "venv_pytorch" ]; then
    python3 -m venv venv_pytorch
fi
source venv_pytorch/bin/activate

# 升级 pip 并安装框架底层编译必须的 Python 工具包
pip install --upgrade pip
pip install -r requirements.txt || true
pip install typing_extensions sympy networkx jinja2 pyyaml ninja

echo "[*] Setting compilation flags for Gcov and disabling extra modules..."
export USE_CUDA=0
export USE_CUDNN=0
export USE_MKLDNN=0
export USE_QNNPACK=0
export USE_NNPACK=0
export USE_DISTRIBUTED=0
export BUILD_TEST=0
export BUILD_CAFFE2=0
export USE_OPENMP=0

# 最核心：注入真理之火 (Gcov Flags)
export CFLAGS="-fprofile-arcs -ftest-coverage -O0"
export CXXFLAGS="-fprofile-arcs -ftest-coverage -O0"
export LDFLAGS="-lgcov"
# 限制 Ninja 最大并行核心数，防机器卡死 (保留两颗核用来画图或者上网)
export MAX_JOBS=$(( $(nproc) > 2 ? $(nproc) - 2 : 1 ))

echo "[*] Starting PyTorch build with MAX_JOBS = $MAX_JOBS ..."
echo "    (This will take 1.5 ~ 3 hours depending on your CPU!)"

python setup.py clean
# 这里使用 develop 模式编译，生成的文件挂在原目录
python setup.py develop

echo "[*]"
echo "[*] ========================================="
echo "[*] S U C C E S S !"
echo "[*] PyTorch is now compiled with Gcov support."
echo "[*] ========================================="
