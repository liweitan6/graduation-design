# -*- coding: utf-8 -*-
"""
结构化日志解析器 (Structured Log Parser)

将原始的 error_message 文本解析为结构化字段，提取出：
- 错误类型 (error_type): RuntimeError, ValueError, etc.
- 错误分类 (error_category): shape_mismatch, cuda_oom, segfault, timeout, device_mismatch, index_error
- 张量维度 (tensor_shapes): 从日志中提取的维度信息
- 框架源码位置 (source_location): 具体的 .cpp/.py 文件和行号
- 显存信息 (memory_info): OOM 时的显存分配量和总容量
- 设备信息 (device_info): cuda:0, cpu 等
"""

import re
from typing import Dict, List, Any, Optional


class LogParser:
    """将原始错误信息解析为结构化数据"""

    # ==================== 错误分类规则 ====================
    ERROR_PATTERNS = [
        {
            "category": "cuda_oom",
            "keywords": ["cuda out of memory", "out of memory", "oom", "cuda error: out of memory"],
            "description": "CUDA 显存溢出"
        },
        {
            "category": "shape_mismatch",
            "keywords": ["size mismatch", "shape mismatch", "dimension mismatch",
                         "expected.*size", "mat1 and mat2", "incompatible"],
            "description": "张量维度不匹配"
        },
        {
            "category": "segfault",
            "keywords": ["segmentation fault", "core dumped", "sigsegv", "signal 11"],
            "description": "内存段错误"
        },
        {
            "category": "timeout",
            "keywords": ["timeout", "timed out", "exceeded maximum", "deadline"],
            "description": "执行超时"
        },
        {
            "category": "device_mismatch",
            "keywords": ["device mismatch", "expected.*device", "cuda.*cpu", "cpu.*cuda",
                         "expected all tensors to be on the same device"],
            "description": "设备不匹配"
        },
        {
            "category": "index_error",
            "keywords": ["index out of", "out of bounds", "out of range", "indexerror"],
            "description": "索引越界"
        },
        {
            "category": "type_error",
            "keywords": ["type error", "typeerror", "expected.*type", "invalid type"],
            "description": "类型错误"
        },
        {
            "category": "nan_inf",
            "keywords": ["nan", "inf", "not a number", "infinity"],
            "description": "数值异常 (NaN/Inf)"
        },
    ]

    def parse(self, error_message: str) -> Dict[str, Any]:
        """
        主解析入口：将原始错误信息解析为结构化字段

        Returns:
            {
                "error_type": "RuntimeError",
                "error_category": "shape_mismatch",
                "error_description": "张量维度不匹配",
                "tensor_shapes": [{"name": "m1", "shape": [32, 512]}, ...],
                "memory_info": {"requested": "512 MiB", "total": "8.00 GiB"},
                "source_location": {"file": "THTensorMath.cpp", "line": 41, "module": "aten/TH"},
                "device_info": ["cuda:0", "cpu"],
                "raw_message": "..."
            }
        """
        if not error_message:
            return {
                "error_type": None,
                "error_category": "no_error",
                "error_description": "无错误",
                "tensor_shapes": [],
                "memory_info": None,
                "source_location": None,
                "device_info": [],
                "raw_message": ""
            }

        result = {
            "raw_message": error_message,
            "error_type": self._extract_error_type(error_message),
            "error_category": self._classify_error(error_message),
            "error_description": "",
            "tensor_shapes": self.extract_tensor_shapes(error_message),
            "memory_info": self._extract_memory_info(error_message),
            "source_location": self.extract_source_location(error_message),
            "device_info": self._extract_device_info(error_message),
        }

        # 填充描述
        for pattern in self.ERROR_PATTERNS:
            if pattern["category"] == result["error_category"]:
                result["error_description"] = pattern["description"]
                break
        if not result["error_description"]:
            result["error_description"] = "其他错误"

        return result

    def _extract_error_type(self, msg: str) -> Optional[str]:
        """提取错误类型：RuntimeError, ValueError, IndexError 等"""
        # 匹配 Python 异常类型
        match = re.search(r'(\w+Error):', msg)
        if match:
            return match.group(1)
        # 匹配 Timeout
        match = re.search(r'(\w+Timeout\w*)', msg, re.IGNORECASE)
        if match:
            return match.group(1)
        # 匹配 Segmentation fault
        if re.search(r'[Ss]egmentation [Ff]ault', msg):
            return "SegmentationFault"
        return "UnknownError"

    def _classify_error(self, msg: str) -> str:
        """根据关键词匹配，按优先级分类错误"""
        msg_lower = msg.lower()
        for pattern in self.ERROR_PATTERNS:
            for keyword in pattern["keywords"]:
                if re.search(keyword, msg_lower):
                    return pattern["category"]
        return "other"

    def extract_tensor_shapes(self, msg: str) -> List[Dict[str, Any]]:
        """
        提取日志中的张量维度信息

        支持格式：
        - [32 x 512]
        - (32, 512)
        - size(32, 512)
        - m1: [32 x 512], m2: [256 x 10]
        """
        shapes = []

        # 模式1: name: [dim x dim x ...]
        for match in re.finditer(r'(\w+):\s*\[(\d+(?:\s*x\s*\d+)+)\]', msg):
            name = match.group(1)
            dims = [int(d.strip()) for d in match.group(2).split('x')]
            shapes.append({"name": name, "shape": dims})

        # 模式2: [dim x dim] 没有名称
        if not shapes:
            for match in re.finditer(r'\[(\d+(?:\s*x\s*\d+)+)\]', msg):
                dims = [int(d.strip()) for d in match.group(1).split('x')]
                shapes.append({"name": f"tensor_{len(shapes)}", "shape": dims})

        # 模式3: size (dim, dim, ...)
        for match in re.finditer(r'size\s*\((\d+(?:,\s*\d+)*)\)', msg):
            dims = [int(d.strip()) for d in match.group(1).split(',')]
            shapes.append({"name": f"size_{len(shapes)}", "shape": dims})

        return shapes

    def _extract_memory_info(self, msg: str) -> Optional[Dict[str, str]]:
        """提取显存信息"""
        info = {}

        # "Tried to allocate 512 MiB"
        match = re.search(r'[Aa]llocate\s+(\d+\.?\d*\s*[GMK]iB)', msg)
        if match:
            info["requested"] = match.group(1)

        # "8.00 GiB total capacity"
        match = re.search(r'(\d+\.?\d*\s*[GMK]iB)\s*total', msg)
        if match:
            info["total"] = match.group(1)

        # "X MiB already allocated"
        match = re.search(r'(\d+\.?\d*\s*[GMK]iB)\s*(?:already\s+)?allocated', msg)
        if match:
            info["allocated"] = match.group(1)

        return info if info else None

    def extract_source_location(self, msg: str) -> Optional[Dict[str, Any]]:
        """
        提取框架源码位置

        支持格式：
        - at /pytorch/aten/src/TH/generic/THTensorMath.cpp:41
        - File "xxx.py", line 42
        """
        # C++ 源码位置
        match = re.search(r'at\s+.*?/(\w+\.(?:cpp|cu|h|cc)):(\d+)', msg)
        if match:
            filename = match.group(1)
            line = int(match.group(2))
            # 提取模块路径
            module_match = re.search(r'at\s+.*?/((?:\w+/)+)\w+\.(?:cpp|cu|h|cc)', msg)
            module = module_match.group(1).rstrip('/') if module_match else "unknown"
            return {"file": filename, "line": line, "module": module}

        # Python 源码位置
        match = re.search(r'File\s+"([^"]+)",\s*line\s+(\d+)', msg)
        if match:
            filepath = match.group(1)
            filename = filepath.split('/')[-1].split('\\')[-1]
            return {"file": filename, "line": int(match.group(2)), "module": filepath}

        return None

    def _extract_device_info(self, msg: str) -> List[str]:
        """提取设备信息"""
        devices = []
        for match in re.finditer(r'(cuda:\d+|cpu)', msg.lower()):
            device = match.group(1)
            if device not in devices:
                devices.append(device)
        return devices

    def parse_full_log(self, log_content: str) -> Dict[str, Any]:
        """
        解析完整的执行日志（多行），提取时间线和事件序列

        Returns:
            {
                "events": [...],       # 时间线事件列表
                "final_status": "CRASH" / "SUCCESS" / "TIMEOUT",
                "duration": 0.85,
                "error_summary": {...}  # 最终错误的结构化解析
            }
        """
        events = []
        final_status = "UNKNOWN"
        duration = None
        last_error = None

        for line in log_content.split('\n'):
            line = line.strip()
            if not line:
                continue

            # 提取日志级别和时间
            time_match = re.search(r'\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\]', line)
            level_match = re.search(r'\[(INFO|ERROR|WARNING|CRASH|SUCCESS|TIMEOUT)\]', line)

            event = {
                "timestamp": time_match.group(1) if time_match else None,
                "level": level_match.group(1) if level_match else "INFO",
                "message": line
            }

            if level_match:
                level = level_match.group(1)
                if level == "CRASH":
                    final_status = "Crash"
                    # 提取 duration
                    dur_match = re.search(r'(\d+\.?\d*)\s*s', line)
                    if dur_match:
                        duration = float(dur_match.group(1))
                elif level == "SUCCESS":
                    final_status = "Success"
                    dur_match = re.search(r'(\d+\.?\d*)\s*s', line)
                    if dur_match:
                        duration = float(dur_match.group(1))
                elif level == "TIMEOUT":
                    final_status = "Timeout"
                elif level == "ERROR":
                    last_error = line

            events.append(event)

        error_summary = self.parse(last_error) if last_error else None

        return {
            "events": events,
            "final_status": final_status,
            "duration": duration,
            "error_summary": error_summary
        }


# ==================== 便捷函数 ====================

_parser = LogParser()


def parse_error_message(error_message: str) -> Dict[str, Any]:
    """便捷函数：解析单条错误信息"""
    return _parser.parse(error_message)


def parse_full_log(log_content: str) -> Dict[str, Any]:
    """便捷函数：解析完整日志"""
    return _parser.parse_full_log(log_content)
