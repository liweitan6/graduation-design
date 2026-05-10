import requests
import json
import time

API_URL = "http://localhost:5000/api/ingest"

# 准备 10 个成功用例，全部满足 input_size + 2 * padding >= kernel_size
successful_data = [
    (10, 1, 3),
    (5, 2, 5),
    (8, 0, 3),
    (4, 1, 5),
    (7, 2, 7),
    (20, 0, 7),
    (6, 1, 3),
    (12, 0, 5),
    (3, 1, 3),
    (9, 2, 5)
]

payload = []

# 生成成功用例
for i, (input_size, padding, kernel_size) in enumerate(successful_data):
    case = {
        "case_uid": f"demo_daikon_success_{i+1}",
        "status": "SUCCESS",
        "execution_time": 0.05 + (i * 0.01),
        "edge_coverage": 120 + i,
        "model_structure": {
            "operators": ["Conv1d", "ReLU"],
            "layers": [f"Conv1d(in_channels=3, out_channels=16, kernel_size={kernel_size}, padding={padding})", "ReLU()"],
            "input_size": input_size,
            "padding": padding,
            "kernel_size": kernel_size,
            "depth": 2,
            "connections": "Conv1d->ReLU"
        },
        "parameters": {}
    }
    payload.append(case)

# 生成 1 个失败用例，打破 input_size + 2 * padding >= kernel_size (2 + 0 < 5)
failed_case = {
    "case_uid": "demo_daikon_failed_1",
    "status": "FAILED",
    "execution_time": 0.01,
    "edge_coverage": 45,
    "error_message": "RuntimeError: Calculated padded input size per channel: (2). Kernel size: (5). Kernel size can't be greater than actual input size",
    "model_structure": {
        "operators": ["Conv1d", "ReLU"],
        "layers": ["Conv1d(in_channels=3, out_channels=16, kernel_size=5, padding=0)", "ReLU()"],
        "input_size": 2,
        "padding": 0,
        "kernel_size": 5,
        "depth": 2,
        "connections": "Conv1d->ReLU"
    },
    "parameters": {}
}
payload.append(failed_case)

# 另外再造一组测试 in_channels % groups == 0 的用例
# 成功用例
groups_success = [
    (16, 2), (16, 4), (16, 8), (16, 16),
    (8, 2), (8, 4), (8, 8),
    (32, 2), (32, 4), (32, 8)
]

for i, (in_channels, groups) in enumerate(groups_success):
    case = {
        "case_uid": f"demo_groups_success_{i+1}",
        "status": "SUCCESS",
        "execution_time": 0.06,
        "edge_coverage": 130,
        "model_structure": {
            "operators": ["Conv2d", "BatchNorm2d"],
            "layers": [f"Conv2d(in_channels={in_channels}, out_channels=32, groups={groups})", "BatchNorm2d(32)"],
            "in_channels": in_channels,
            "groups": groups,
            "kernel_size": 3,
            "depth": 2,
            "connections": "Conv2d->BatchNorm2d"
        },
        "parameters": {}
    }
    payload.append(case)

# 失败用例，打破 in_channels % groups == 0
failed_groups_case = {
    "case_uid": "demo_groups_failed_1",
    "status": "FAILED",
    "execution_time": 0.01,
    "edge_coverage": 30,
    "error_message": "ValueError: in_channels must be divisible by groups",
    "model_structure": {
        "operators": ["Conv2d", "BatchNorm2d"],
        "layers": ["Conv2d(in_channels=16, out_channels=32, groups=3)", "BatchNorm2d(32)"],
        "in_channels": 16,
        "groups": 3,
        "kernel_size": 3,
        "depth": 2,
        "connections": "Conv2d->BatchNorm2d"
    },
    "parameters": {}
}
payload.append(failed_groups_case)

print(f"准备导入 {len(payload)} 条测试数据...")
try:
    response = requests.post(API_URL, json=payload, timeout=30)
    response.raise_for_status()
    print("导入成功！")
    print("API 响应:", response.json())
except Exception as e:
    print(f"导入失败: {e}")
