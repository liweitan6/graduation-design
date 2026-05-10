#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
一键导入全部展示数据（用于毕业论文截图）
包含：
  1. 2000 条真实模糊测试数据 (real_fuzzing_data.json)
  2. 22 条 Daikon 边界分析演示数据
用法：conda run -n dl_fuzz_env python scripts/import_all_demo_data.py
"""

import json
import time
import requests

API_URL = "http://localhost:5000/api/ingest"
BATCH_SIZE = 50  # 每批 50 条，避免一次性向量化 OOM

def post_batch(batch, batch_num, total_batches):
    """发送一批数据到 ingest API"""
    try:
        resp = requests.post(API_URL, json=batch, timeout=120)
        resp.raise_for_status()
        result = resp.json()
        print(f"  [Batch {batch_num}/{total_batches}] ✅ 成功入库 {result['success']} 条")
        return result["success"]
    except Exception as e:
        print(f"  [Batch {batch_num}/{total_batches}] ❌ 失败: {e}")
        return 0


def import_real_fuzzing_data():
    """导入 2000 条真实模糊测试数据"""
    print("=" * 60)
    print("📦 [Part 1/2] 导入真实模糊测试数据 (real_fuzzing_data.json)")
    print("=" * 60)

    with open("scripts/real_fuzzing_data.json", "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # 转换字段名：execution_time_ms → execution_time (秒)
    cases = []
    for item in raw_data:
        case = {
            "case_uid": item["case_uid"],
            "status": item["status"],
            "execution_time": round(item.get("execution_time_ms", 0) / 1000.0, 4),
            "edge_coverage": item.get("edge_coverage", 0),
            "model_structure": item.get("model_structure", {}),
            "error_message": item.get("error_message"),
            "parameters": item.get("parameters", {})
        }
        cases.append(case)

    print(f"  总计 {len(cases)} 条记录，分 {(len(cases) + BATCH_SIZE - 1) // BATCH_SIZE} 批导入...")

    total_success = 0
    total_batches = (len(cases) + BATCH_SIZE - 1) // BATCH_SIZE
    for i in range(0, len(cases), BATCH_SIZE):
        batch = cases[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_success += post_batch(batch, batch_num, total_batches)
        time.sleep(0.5)  # 给服务喘息时间

    print(f"\n  📊 真实数据导入完成: {total_success}/{len(cases)} 条成功\n")
    return total_success


def import_daikon_demo_data():
    """导入 Daikon 边界分析演示数据"""
    print("=" * 60)
    print("📦 [Part 2/2] 导入 Daikon 边界分析演示数据")
    print("=" * 60)

    payload = []

    # ---- 组 1: input_size + 2*padding >= kernel_size 规律 ----
    successful_data = [
        (10, 1, 3), (5, 2, 5), (8, 0, 3), (4, 1, 5), (7, 2, 7),
        (20, 0, 7), (6, 1, 3), (12, 0, 5), (3, 1, 3), (9, 2, 5)
    ]
    for i, (input_size, padding, kernel_size) in enumerate(successful_data):
        payload.append({
            "case_uid": f"demo_daikon_success_{i+1}",
            "status": "Success",
            "execution_time": 0.05 + (i * 0.01),
            "edge_coverage": 120 + i,
            "model_structure": {
                "operators": ["Conv1d", "ReLU"],
                "layers": [f"Conv1d(in_channels=3, out_channels=16, kernel_size={kernel_size}, padding={padding})", "ReLU()"],
                "input_size": input_size, "padding": padding, "kernel_size": kernel_size,
                "depth": 2, "connections": "Conv1d->ReLU"
            },
            "parameters": {"demo_group": "daikon_conv1d_boundary"}
        })

    # 1 条失败（打破 input_size + 2*padding >= kernel_size）
    payload.append({
        "case_uid": "demo_daikon_failed_1",
        "status": "Crash",
        "execution_time": 0.01,
        "edge_coverage": 45,
        "error_message": "RuntimeError: Calculated padded input size per channel: (2). Kernel size: (5). Kernel size can't be greater than actual input size",
        "model_structure": {
            "operators": ["Conv1d", "ReLU"],
            "layers": ["Conv1d(in_channels=3, out_channels=16, kernel_size=5, padding=0)", "ReLU()"],
            "input_size": 2, "padding": 0, "kernel_size": 5,
            "depth": 2, "connections": "Conv1d->ReLU"
        },
        "parameters": {"demo_group": "daikon_conv1d_boundary"}
    })

    # ---- 组 2: in_channels % groups == 0 规律 ----
    groups_success = [
        (16, 2), (16, 4), (16, 8), (16, 16),
        (8, 2), (8, 4), (8, 8),
        (32, 2), (32, 4), (32, 8)
    ]
    for i, (in_channels, groups) in enumerate(groups_success):
        payload.append({
            "case_uid": f"demo_groups_success_{i+1}",
            "status": "Success",
            "execution_time": 0.06,
            "edge_coverage": 130,
            "model_structure": {
                "operators": ["Conv2d", "BatchNorm2d"],
                "layers": [f"Conv2d(in_channels={in_channels}, out_channels=32, groups={groups})", "BatchNorm2d(32)"],
                "in_channels": in_channels, "groups": groups, "kernel_size": 3,
                "depth": 2, "connections": "Conv2d->BatchNorm2d"
            },
            "parameters": {"demo_group": "daikon_groups_divisibility"}
        })

    # 1 条失败（打破 in_channels % groups == 0）
    payload.append({
        "case_uid": "demo_groups_failed_1",
        "status": "Crash",
        "execution_time": 0.01,
        "edge_coverage": 30,
        "error_message": "ValueError: in_channels must be divisible by groups",
        "model_structure": {
            "operators": ["Conv2d", "BatchNorm2d"],
            "layers": ["Conv2d(in_channels=16, out_channels=32, groups=3)", "BatchNorm2d(32)"],
            "in_channels": 16, "groups": 3, "kernel_size": 3,
            "depth": 2, "connections": "Conv2d->BatchNorm2d"
        },
        "parameters": {"demo_group": "daikon_groups_divisibility"}
    })

    print(f"  总计 {len(payload)} 条 Daikon 演示记录...")
    total_success = post_batch(payload, 1, 1)
    print(f"\n  📊 Daikon 演示数据导入完成: {total_success}/{len(payload)} 条成功\n")
    return total_success


if __name__ == "__main__":
    print("\n🚀 毕业论文展示数据一键导入工具")
    print("=" * 60)

    # 检查 API 是否可达
    try:
        r = requests.get("http://localhost:5000/", timeout=5)
        print(f"✅ Python API 服务已就绪 (status={r.status_code})\n")
    except Exception:
        print("❌ 无法连接 Python API (http://localhost:5000)，请先启动服务！")
        exit(1)

    t0 = time.time()
    n1 = import_real_fuzzing_data()
    n2 = import_daikon_demo_data()
    elapsed = time.time() - t0

    print("=" * 60)
    print(f"🎉 全部数据导入完成！")
    print(f"   - 真实模糊测试数据: {n1} 条")
    print(f"   - Daikon 演示数据:  {n2} 条")
    print(f"   - 总计: {n1 + n2} 条")
    print(f"   - 耗时: {elapsed:.1f}s")
    print("=" * 60)
