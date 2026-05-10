#!/bin/bash
cd /mnt/e/BUAA/graduation-design/pytorch_gcov/pytorch
source venv_pytorch/bin/activate
export USE_CUDA=0 USE_CUDNN=0 USE_MKLDNN=0 USE_QNNPACK=0 USE_NNPACK=0
export USE_DISTRIBUTED=0 BUILD_TEST=0 BUILD_CAFFE2=0 USE_OPENMP=0
export CFLAGS="-fprofile-arcs -ftest-coverage -O0"
export CXXFLAGS="-fprofile-arcs -ftest-coverage -O0"
export LDFLAGS="-lgcov"
export MAX_JOBS=2
export DEBUG=1
python setup.py develop 2>&1 | tee /mnt/e/BUAA/graduation-design/pytorch_build.log
