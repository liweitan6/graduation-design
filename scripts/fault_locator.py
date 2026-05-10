# -*- coding: utf-8 -*-
"""
自动故障定位引擎 (Fault Locator)

将解析后的错误信息映射回测试用例的 DAG 结构，定位出最可能导致错误的"嫌疑算子"。

定位策略：
1. Shape Mismatch → 定位维度变换算子 (Linear, Conv2d, etc.)
2. CUDA OOM → 定位高显存消耗算子
3. Device Mismatch → 定位设备切换点
4. Index Error → 定位索引操作算子
5. 通过连接链分析，进一步定位到具体位置
"""

from typing import Dict, List, Any, Optional


# 算子能力标注：哪些算子会改变张量形状
SHAPE_CHANGING_OPS = {
    "Linear", "Conv2d", "Conv1d", "Conv3d", "ConvTranspose2d",
    "MaxPool2d", "AvgPool2d", "AdaptiveAvgPool2d", "AdaptiveMaxPool2d",
    "Flatten", "Reshape", "Upsample",
    "Embedding", "Linear",
}

# 高显存消耗算子
MEMORY_HEAVY_OPS = {
    "Conv2d", "Conv3d", "ConvTranspose2d",
    "Linear",
    "MultiHeadAttention", "TransformerEncoderLayer",
    "LSTM", "GRU",
    "Embedding",
}

# 涉及索引操作的算子
INDEX_OPS = {
    "Embedding", "LSTM", "GRU", "RNN",
    "Concat", "Add",
}

# 需要特定设备的算子
DEVICE_SENSITIVE_OPS = {
    "Conv2d", "Conv1d", "Conv3d",
    "Linear",
    "LSTM", "GRU",
    "MultiHeadAttention",
    "BatchNorm2d", "BatchNorm1d",
}


class FaultLocator:
    """将解析后的错误映射到测试用例中的具体算子"""

    def localize(self, model_structure: Dict[str, Any],
                 parsed_error: Dict[str, Any]) -> Dict[str, Any]:
        """
        核心定位方法

        Args:
            model_structure: 测试用例的模型结构
                {
                    "operators": ["Conv2d", "BatchNorm2d", "ReLU", "Linear"],
                    "connections": "Conv2d->BatchNorm2d->ReLU->Linear",
                    "layers": [...],
                    "depth": 4
                }
            parsed_error: LogParser 解析后的结构化错误
                {
                    "error_category": "shape_mismatch",
                    "tensor_shapes": [...],
                    "memory_info": {...},
                    ...
                }

        Returns:
            {
                "suspect_operators": [
                    {"operator": "Linear", "index": 3, "confidence": 0.9, "reason": "..."}
                ],
                "error_category": "shape_mismatch",
                "analysis": "...",  # 整体分析说明
                "suggestion": "..." # 修复建议
            }
        """
        if not parsed_error or not model_structure:
            return self._empty_result()

        category = parsed_error.get("error_category", "other")
        operators = model_structure.get("operators", [])
        connections = model_structure.get("connections", "")

        # 解析连接链为有序算子列表
        op_chain = self._parse_connection_chain(connections, operators)

        # 根据错误类别分派定位策略
        if category == "shape_mismatch":
            return self._localize_shape_mismatch(op_chain, operators, parsed_error)
        elif category == "cuda_oom":
            return self._localize_oom(op_chain, operators, parsed_error)
        elif category == "device_mismatch":
            return self._localize_device_mismatch(op_chain, operators, parsed_error)
        elif category == "index_error":
            return self._localize_index_error(op_chain, operators, parsed_error)
        elif category == "segfault":
            return self._localize_segfault(op_chain, operators, parsed_error)
        elif category == "timeout":
            return self._localize_timeout(op_chain, operators, parsed_error)
        else:
            return self._localize_generic(op_chain, operators, parsed_error)

    def _parse_connection_chain(self, connections: str, operators: List[str]) -> List[Dict]:
        """将连接字符串解析为带索引的算子链"""
        chain = []
        if connections:
            parts = [p.strip() for p in connections.replace("->", "→").replace("→", "|").split("|")]
            for i, part in enumerate(parts):
                chain.append({"operator": part, "index": i})
        elif operators:
            for i, op in enumerate(operators):
                chain.append({"operator": op, "index": i})
        return chain

    def _localize_shape_mismatch(self, op_chain, operators, parsed_error):
        """Shape Mismatch 定位：找维度变换算子"""
        suspects = []
        tensor_shapes = parsed_error.get("tensor_shapes", [])

        # 在连接链中找到所有会改变形状的算子
        for item in op_chain:
            op = item["operator"]
            if op in SHAPE_CHANGING_OPS:
                confidence = 0.85
                reason = f"{op} 是维度变换算子，Shape Mismatch 通常发生在此类算子的输入/输出维度不匹配处"

                # 如果有具体的维度信息，进一步提高置信度
                if tensor_shapes and op in ("Linear", "Conv2d"):
                    confidence = 0.95
                    dims_str = ", ".join(
                        f"{t['name']}={t['shape']}" for t in tensor_shapes
                    )
                    reason = f"{op} 的输入/输出维度与前一层输出不匹配。检测到维度冲突: {dims_str}"

                suspects.append({
                    "operator": op,
                    "index": item["index"],
                    "confidence": confidence,
                    "reason": reason
                })

        # 特殊规则：如果两个 Shape 变换算子直接相连（没有中间的 Flatten），更可疑
        for i in range(len(op_chain) - 1):
            curr = op_chain[i]["operator"]
            nxt = op_chain[i + 1]["operator"]
            if curr in ("Conv2d", "Conv1d", "Conv3d") and nxt == "Linear":
                # Conv 直连 Linear 是经典 Shape Mismatch 场景
                for s in suspects:
                    if s["operator"] == "Linear" and s["index"] == op_chain[i + 1]["index"]:
                        s["confidence"] = min(s["confidence"] + 0.05, 1.0)
                        s["reason"] += "。注意：Conv 层直接连接 Linear 层时需要 Flatten/Reshape 过渡"

        analysis = self._build_analysis("Shape Mismatch", suspects, parsed_error)
        suggestion = "建议在维度变换算子之间插入 Flatten 或 Reshape 层，确保张量维度正确对齐"

        return {
            "suspect_operators": sorted(suspects, key=lambda x: x["confidence"], reverse=True),
            "error_category": "shape_mismatch",
            "analysis": analysis,
            "suggestion": suggestion
        }

    def _localize_oom(self, op_chain, operators, parsed_error):
        """CUDA OOM 定位：找高显存消耗算子"""
        suspects = []
        memory_info = parsed_error.get("memory_info", {})

        for item in op_chain:
            op = item["operator"]
            if op in MEMORY_HEAVY_OPS:
                confidence = 0.7
                reason = f"{op} 是高计算/显存消耗算子"

                if op in ("Conv2d", "Conv3d"):
                    confidence = 0.85
                    reason = f"{op} 进行卷积运算，需要大量显存存储特征图和梯度"
                elif op == "MultiHeadAttention":
                    confidence = 0.9
                    reason = f"{op} 的注意力矩阵大小为 O(n²)，长序列时显存消耗急剧增长"

                if memory_info:
                    mem_str = memory_info.get("requested", "unknown")
                    reason += f"。当前尝试分配 {mem_str}"

                suspects.append({
                    "operator": op,
                    "index": item["index"],
                    "confidence": confidence,
                    "reason": reason
                })

        analysis = self._build_analysis("CUDA OOM", suspects, parsed_error)
        suggestion = "建议减小 batch_size、使用梯度累积、或降低模型参数量（如减小 kernel_size、channel 数）"

        return {
            "suspect_operators": sorted(suspects, key=lambda x: x["confidence"], reverse=True),
            "error_category": "cuda_oom",
            "analysis": analysis,
            "suggestion": suggestion
        }

    def _localize_device_mismatch(self, op_chain, operators, parsed_error):
        """Device Mismatch 定位：找设备切换点"""
        suspects = []
        devices = parsed_error.get("device_info", [])

        for item in op_chain:
            op = item["operator"]
            if op in DEVICE_SENSITIVE_OPS:
                confidence = 0.6
                reason = f"{op} 需要特定设备（GPU/CPU），可能是设备不一致的触发点"

                if devices:
                    reason += f"。检测到涉及设备: {', '.join(devices)}"
                    confidence = 0.8

                suspects.append({
                    "operator": op,
                    "index": item["index"],
                    "confidence": confidence,
                    "reason": reason
                })

        analysis = self._build_analysis("Device Mismatch", suspects, parsed_error)
        suggestion = "建议确保所有张量和模型参数在同一设备上，在算子链入口处统一 .to(device)"

        return {
            "suspect_operators": sorted(suspects, key=lambda x: x["confidence"], reverse=True),
            "error_category": "device_mismatch",
            "analysis": analysis,
            "suggestion": suggestion
        }

    def _localize_index_error(self, op_chain, operators, parsed_error):
        """Index Error 定位"""
        suspects = []
        for item in op_chain:
            op = item["operator"]
            if op in INDEX_OPS:
                suspects.append({
                    "operator": op,
                    "index": item["index"],
                    "confidence": 0.75,
                    "reason": f"{op} 涉及索引/查表操作，可能因输入索引超出词表或序列长度导致越界"
                })

        analysis = self._build_analysis("Index Error", suspects, parsed_error)
        suggestion = "建议检查 Embedding 层的 num_embeddings 参数和输入索引范围"

        return {
            "suspect_operators": sorted(suspects, key=lambda x: x["confidence"], reverse=True),
            "error_category": "index_error",
            "analysis": analysis,
            "suggestion": suggestion
        }

    def _localize_segfault(self, op_chain, operators, parsed_error):
        """Segmentation Fault 定位"""
        suspects = []
        source = parsed_error.get("source_location")

        for item in op_chain:
            op = item["operator"]
            if op in MEMORY_HEAVY_OPS:
                confidence = 0.5
                reason = f"{op} 调用底层 C++ 内核，可能因非法内存访问导致 Segfault"
                if source:
                    reason += f"。错误发生在框架源码 {source.get('file', '?')}:{source.get('line', '?')}"
                    confidence = 0.7
                suspects.append({
                    "operator": op,
                    "index": item["index"],
                    "confidence": confidence,
                    "reason": reason
                })

        analysis = self._build_analysis("Segmentation Fault", suspects, parsed_error)
        suggestion = "这通常是框架底层的 C++ 代码 bug，建议收集完整 core dump 和最小复现用例提交给框架维护者"

        return {
            "suspect_operators": sorted(suspects, key=lambda x: x["confidence"], reverse=True),
            "error_category": "segfault",
            "analysis": analysis,
            "suggestion": suggestion
        }

    def _localize_timeout(self, op_chain, operators, parsed_error):
        """Timeout 定位"""
        suspects = []
        for item in op_chain:
            op = item["operator"]
            if op in ("MultiHeadAttention", "TransformerEncoderLayer", "LSTM", "GRU", "RNN"):
                suspects.append({
                    "operator": op,
                    "index": item["index"],
                    "confidence": 0.7,
                    "reason": f"{op} 在长序列/大模型时计算量极大，可能导致执行超时"
                })

        analysis = self._build_analysis("Timeout", suspects, parsed_error)
        suggestion = "建议缩短输入序列长度、减少模型层数、或增加超时阈值"

        return {
            "suspect_operators": sorted(suspects, key=lambda x: x["confidence"], reverse=True),
            "error_category": "timeout",
            "analysis": analysis,
            "suggestion": suggestion
        }

    def _localize_generic(self, op_chain, operators, parsed_error):
        """通用定位：无法精确分类时的兜底策略"""
        suspects = []
        for item in op_chain:
            op = item["operator"]
            if op in SHAPE_CHANGING_OPS | MEMORY_HEAVY_OPS:
                suspects.append({
                    "operator": op,
                    "index": item["index"],
                    "confidence": 0.3,
                    "reason": f"{op} 是复杂算子，可能与错误相关"
                })

        return {
            "suspect_operators": sorted(suspects, key=lambda x: x["confidence"], reverse=True)[:3],
            "error_category": parsed_error.get("error_category", "other"),
            "analysis": f"无法精确定位错误源，但以下算子具有较高复杂度，值得重点排查",
            "suggestion": "建议逐一隔离测试各算子，定位具体触发条件"
        }

    def _build_analysis(self, error_name: str, suspects: List[Dict], parsed_error: Dict) -> str:
        """构建分析说明文本"""
        if not suspects:
            return f"在当前用例的算子链中未找到与 {error_name} 直接相关的嫌疑算子"

        top = suspects[0] if suspects else None
        analysis = f"检测到 {error_name} 错误。"
        analysis += f"在当前用例的 {len(suspects)} 个相关算子中，"
        if top:
            analysis += f"**{top['operator']}**（位置 #{top['index']}）置信度最高 ({top['confidence']:.0%})"
        return analysis

    def _empty_result(self):
        return {
            "suspect_operators": [],
            "error_category": "unknown",
            "analysis": "无法进行故障定位：缺少错误信息或模型结构",
            "suggestion": ""
        }


# ==================== 便捷函数 ====================

_locator = FaultLocator()


def localize_fault(model_structure: Dict[str, Any],
                   parsed_error: Dict[str, Any]) -> Dict[str, Any]:
    """便捷函数：定位故障"""
    return _locator.localize(model_structure, parsed_error)
