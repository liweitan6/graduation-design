#!/bin/bash
set -e

# 进入 PyTorch 源目录
cd /mnt/e/BUAA/graduation-design/pytorch_gcov/pytorch
source venv_pytorch/bin/activate
cd /mnt/e/BUAA/graduation-design

echo "=========================================="
echo "      Phase 1: BASELINE (200 cases)      "
echo "=========================================="

# 1. 彻底清空残留数据
lcov --zerocounters --directory /mnt/e/BUAA/graduation-design/pytorch_gcov/pytorch/build/

# 2. 不加任何 CEI 精简，跑完全局大图
python scripts/real_cei_executor.py --mode baseline --count 200

# 3. 收集并抽取 C++ 覆盖率！
echo "Gathering lcov trace for baseline..."
lcov --capture --directory /mnt/e/BUAA/graduation-design/pytorch_gcov/pytorch/build/ --output-file baseline_200.info

echo ""
echo "=========================================="
echo "     Phase 2: CEI FILTERED (优选子集)     "
echo "=========================================="

# 4. 清掉所有的探针记忆，我们要看看只依靠高价值向量能跑到多少！
lcov --zerocounters --directory /mnt/e/BUAA/graduation-design/pytorch_gcov/pytorch/build/

# 5. 打开过滤开关！
python scripts/real_cei_executor.py --mode filtered --count 200

# 6. 捞取数据！
echo "Gathering lcov trace for CEI filtered..."
lcov --capture --directory /mnt/e/BUAA/graduation-design/pytorch_gcov/pytorch/build/ --output-file filtered_200.info

echo ""
echo "=========================================="
echo "          最终 C++ 级底层大比拼           "
echo "=========================================="
echo "【BASELINE 覆盖率】"
lcov --summary baseline_200.info

echo ""
echo "【CEI FILTERED 覆盖率】"
lcov --summary filtered_200.info
echo "=========================================="
