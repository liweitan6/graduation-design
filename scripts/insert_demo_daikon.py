"""导入用于验证 Daikon 双空间故障边界定界的演示样例。"""

import requests

API_URL = "http://localhost:5000/api/ingest"

payload = []


def add_conv2d_kernel_case(uid, status, height, width, kernel, padding, error_message=None):
    demo_group = "demo_daikon_conv2d_kernel_boundary"
    payload.append({
        "case_uid": uid,
        "status": status,
        "execution_time": 0.04 if status == "SUCCESS" else 0.01,
        "edge_coverage": 220 if status == "SUCCESS" else 45,
        "error_message": error_message,
        "model_structure": {
            "operators": ["Conv2d", "ReLU"],
            "layers": [
                f"Conv2d(in_channels=3, out_channels=8, kernel_size={kernel}, padding={padding})",
                "ReLU()"
            ],
            "batch": 1,
            "in_channels": 3,
            "out_channels": 8,
            "input_height": height,
            "input_width": width,
            "kernel_size": kernel,
            "padding": padding,
            "stride": 1,
            "groups": 1,
            "depth": 2,
            "connections": "Conv2d->ReLU"
        },
        "parameters": {"demo_group": demo_group}
    })


# 成功空间：全部满足 input_height >= kernel_size 且 input_width >= kernel_size。
for index, size in enumerate([3, 4, 5, 6, 7, 8, 10, 12], start=1):
    add_conv2d_kernel_case(
        uid=f"demo_daikon_kernel_success_{index}",
        status="SUCCESS",
        height=size,
        width=size + 1,
        kernel=3,
        padding=0
    )

# 失败空间：打破同一约束，PyTorch Conv2d 会报 kernel size 大于输入尺寸。
for index, (height, width, kernel) in enumerate([(2, 4, 3), (1, 5, 3), (2, 2, 5)], start=1):
    add_conv2d_kernel_case(
        uid=f"demo_daikon_kernel_failed_{index}",
        status="FAILED",
        height=height,
        width=width,
        kernel=kernel,
        padding=0,
        error_message=(
            f"RuntimeError: Calculated padded input size per channel: ({height} x {width}). "
            f"Kernel size: ({kernel} x {kernel}). Kernel size can't be greater than actual input size"
        )
    )


def add_conv2d_groups_case(uid, status, in_channels, groups, error_message=None):
    demo_group = "demo_daikon_conv2d_groups_boundary"
    payload.append({
        "case_uid": uid,
        "status": status,
        "execution_time": 0.05 if status == "SUCCESS" else 0.01,
        "edge_coverage": 240 if status == "SUCCESS" else 50,
        "error_message": error_message,
        "model_structure": {
            "operators": ["Conv2d", "BatchNorm2d"],
            "layers": [
                f"Conv2d(in_channels={in_channels}, out_channels=24, kernel_size=3, groups={groups})",
                "BatchNorm2d(24)"
            ],
            "batch": 1,
            "in_channels": in_channels,
            "out_channels": 24,
            "input_height": 8,
            "input_width": 8,
            "kernel_size": 3,
            "padding": 0,
            "stride": 1,
            "groups": groups,
            "depth": 2,
            "connections": "Conv2d->BatchNorm2d"
        },
        "parameters": {"demo_group": demo_group}
    })


# 成功空间：全部满足 in_channels % groups == 0。
for index, (in_channels, groups) in enumerate([(4, 1), (4, 2), (6, 3), (8, 2), (8, 4), (12, 3), (12, 4), (16, 8)], start=1):
    add_conv2d_groups_case(
        uid=f"demo_daikon_groups_success_{index}",
        status="SUCCESS",
        in_channels=in_channels,
        groups=groups
    )

# 失败空间：打破整除关系。
for index, (in_channels, groups) in enumerate([(5, 2), (7, 3), (10, 4)], start=1):
    add_conv2d_groups_case(
        uid=f"demo_daikon_groups_failed_{index}",
        status="FAILED",
        in_channels=in_channels,
        groups=groups,
        error_message="ValueError: in_channels must be divisible by groups"
    )

print(f"准备导入 {len(payload)} 条 Daikon 双空间验证样例...")
print("建议在前端搜索失败用例 ID: demo_daikon_kernel_failed_1 或 demo_daikon_groups_failed_1")
try:
    response = requests.post(API_URL, json=payload, timeout=120)
    response.raise_for_status()
    print("导入成功！")
    print("API 响应:", response.json())
except Exception as e:
    print(f"导入失败: {e}")
