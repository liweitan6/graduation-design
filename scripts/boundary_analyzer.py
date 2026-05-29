# -*- coding: utf-8 -*-
"""
故障边界分析器 (Boundary Analyzer)

接收一个失败用例和一个成功用例的参数字典，通过执行张量或算子维度的 Diff (差分) 操作，
提取出引发崩溃的关键变量 Delta。
"""

from typing import Dict, Any, List
import copy
import math
import re

class BoundaryAnalyzer:
    def analyze_boundary(self, failed_params: Dict[str, Any], successful_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        对比失败用例和成功用例的参数字典，提取 Diff。
        """
        diff = {
            "changed_params": {},
            "failed_values": {},
            "successful_values": {}
        }
        
        # 提取模型结构，通常变异的是这些参数
        f_struct = failed_params.get("model_structure", failed_params)
        s_struct = successful_params.get("model_structure", successful_params)
        
        def recursive_diff(dict1, dict2, prefix=""):
            if not isinstance(dict1, dict) or not isinstance(dict2, dict):
                if dict1 != dict2:
                    diff["changed_params"][prefix.strip(".")] = "MODIFIED"
                    diff["failed_values"][prefix.strip(".")] = dict1
                    diff["successful_values"][prefix.strip(".")] = dict2
                return

            for k, v in dict1.items():
                if k not in dict2:
                    diff["changed_params"][f"{prefix}{k}"] = "REMOVED"
                    diff["failed_values"][f"{prefix}{k}"] = v
                    continue
                if isinstance(v, dict) and isinstance(dict2[k], dict):
                    recursive_diff(v, dict2[k], f"{prefix}{k}.")
                elif isinstance(v, list) and isinstance(dict2[k], list):
                    # 简单对比列表是否一致，如果不一致直接标记
                    if v != dict2[k]:
                        diff["changed_params"][f"{prefix}{k}"] = "MODIFIED"
                        diff["failed_values"][f"{prefix}{k}"] = v
                        diff["successful_values"][f"{prefix}{k}"] = dict2[k]
                elif v != dict2[k]:
                    diff["changed_params"][f"{prefix}{k}"] = "MODIFIED"
                    diff["failed_values"][f"{prefix}{k}"] = v
                    diff["successful_values"][f"{prefix}{k}"] = dict2[k]
                    
            for k, v in dict2.items():
                if k not in dict1:
                    diff["changed_params"][f"{prefix}{k}"] = "ADDED"
                    diff["successful_values"][f"{prefix}{k}"] = v

        recursive_diff(f_struct, s_struct)
        
        # 过滤掉可视化坐标和向量 ID 等无关变量
        keys_to_remove = []
        for k in diff["changed_params"].keys():
            if any(ignore_key in k for ignore_key in ["vis_x", "vis_y", "vector_id", "uid", "status", "error", "time", "coverage"]):
                keys_to_remove.append(k)
                
        for k in keys_to_remove:
            diff["changed_params"].pop(k, None)
            diff["failed_values"].pop(k, None)
            diff["successful_values"].pop(k, None)
            
        return diff

# ==================== 便捷函数 ====================

_analyzer = BoundaryAnalyzer()

def analyze_boundary_diff(failed_params: Dict[str, Any], successful_params: Dict[str, Any]) -> Dict[str, Any]:
    return _analyzer.analyze_boundary(failed_params, successful_params)

# ==================== Daikon 动态不变量推断引擎 ====================

class DaikonInvariantEngine:
    """
    借鉴 Daikon 动态不变量推断技术，从多个成功的用例中提取数值约束，
    并寻找失败用例违反了哪条约束，从而精确计算出故障边界公式。

    拓展功能：在得到约束式后，围绕约束式自动生成正/反测试样例，
    供用户在目标执行环境中进一步验证故障边界公式的可信度。
    """
    
    def extract_flat_numeric_params(self, params: Dict[str, Any], prefix="") -> Dict[str, float]:
        """将嵌套的参数字典展平，仅提取数值型参数（int, float）"""
        flat_params = {}
        for k, v in params.items():
            # 过滤无关字段
            if any(ignore in k for ignore in ["vis_x", "vis_y", "vector_id", "uid", "status", "error", "time", "coverage"]):
                continue
                
            full_key = f"{prefix}{k}"
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                flat_params[full_key] = float(v)
            elif isinstance(v, dict):
                flat_params.update(self.extract_flat_numeric_params(v, f"{full_key}."))
            # 对列表类型尝试提取（比如 padding=[1,1]）
            elif isinstance(v, list) and all(isinstance(x, (int, float)) for x in v):
                for i, x in enumerate(v):
                    flat_params[f"{full_key}[{i}]"] = float(x)
        return flat_params

    def infer_violated_invariants(self, failed_params_list: List[Dict[str, Any]], successful_params_list: List[Dict[str, Any]]) -> List[str]:
        """推断在所有成功用例中严格成立，并且在所有失败用例中严格被打破的边界约束"""
        if not successful_params_list or not failed_params_list:
            return []
            
        failed_flats = [self.extract_flat_numeric_params(p.get("model_structure", p)) for p in failed_params_list]
        success_flats = [self.extract_flat_numeric_params(p.get("model_structure", p)) for p in successful_params_list]
        
        # 找出共同键 (需要在至少一个失败样本和一个成功样本中存在，为了严谨，取所有样本的交集)
        common_keys = set(success_flats[0].keys())
        for sf in success_flats:
            common_keys = common_keys.intersection(set(sf.keys()))
        for ff in failed_flats:
            common_keys = common_keys.intersection(set(ff.keys()))
            
        common_keys = list(common_keys)
        n = len(common_keys)
        
        violated_invariants = []
        
        # 1. 单变量约束 (常见常量阈值、奇偶性)
        for x_key in common_keys:
            # 常数边界测试
            for val in [0, 1, -1]:
                if all(sf[x_key] > val for sf in success_flats) and all(not (ff[x_key] > val) for ff in failed_flats):
                    violated_invariants.append(f"{x_key} > {val}")
                if all(sf[x_key] >= val for sf in success_flats) and all(not (ff[x_key] >= val) for ff in failed_flats):
                    violated_invariants.append(f"{x_key} >= {val}")
                if all(sf[x_key] == val for sf in success_flats) and all(not (ff[x_key] == val) for ff in failed_flats):
                    violated_invariants.append(f"{x_key} == {val}")
            
            # 奇偶性测试
            if all(sf[x_key] % 2 == 0 for sf in success_flats) and all(not (ff[x_key] % 2 == 0) for ff in failed_flats):
                violated_invariants.append(f"{x_key} 必须是偶数 ( % 2 == 0 )")
                    
        # 2. 双变量关系约束
        for i in range(n):
            for j in range(n):
                if i == j: continue
                x_key = common_keys[i]
                y_key = common_keys[j]
                
                # 基础等式与不等式
                if all(sf[x_key] == sf[y_key] for sf in success_flats) and all(not (ff[x_key] == ff[y_key]) for ff in failed_flats):
                    violated_invariants.append(f"{x_key} == {y_key}")
                if all(sf[x_key] <= sf[y_key] for sf in success_flats) and all(not (ff[x_key] <= ff[y_key]) for ff in failed_flats):
                    violated_invariants.append(f"{x_key} <= {y_key}")
                if all(sf[x_key] < sf[y_key] for sf in success_flats) and all(not (ff[x_key] < ff[y_key]) for ff in failed_flats):
                    violated_invariants.append(f"{x_key} < {y_key}")

                # 整除关系 (深度学习中极度常见：例如 in_channels 必须被 groups 整除)
                if all(sf[y_key] != 0 and sf[x_key] % sf[y_key] == 0 for sf in success_flats):
                    if all(ff[y_key] == 0 or ff[x_key] % ff[y_key] != 0 for ff in failed_flats):
                        violated_invariants.append(f"{x_key} 必须能被 {y_key} 整除 ( % == 0 )")

                # 带有系数的线性关系探测 (x <= c*y + d)
                for c in [2, 3, 4]:
                    for d in [0, 1, -1]:
                        # 探测上限
                        if all(sf[x_key] <= c * sf[y_key] + d for sf in success_flats) and all(not (ff[x_key] <= c * ff[y_key] + d) for ff in failed_flats):
                            suffix = f" + {d}" if d > 0 else (f" - {-d}" if d < 0 else "")
                            violated_invariants.append(f"{x_key} <= {c} * {y_key}{suffix}")
                        # 探测下限
                        if all(sf[x_key] >= c * sf[y_key] + d for sf in success_flats) and all(not (ff[x_key] >= c * ff[y_key] + d) for ff in failed_flats):
                            suffix = f" + {d}" if d > 0 else (f" - {-d}" if d < 0 else "")
                            violated_invariants.append(f"{x_key} >= {c} * {y_key}{suffix}")

        # 3. 三变量约束 (针对神经网络特有的空间计算公式)
        for i in range(n):
            for j in range(n):
                for k in range(n):
                    if len({i, j, k}) < 3: continue
                    x_key, y_key, z_key = common_keys[i], common_keys[j], common_keys[k]
                    
                    # 探测 CNN 特有的尺寸崩溃公式 (例如: input_size + 2*padding >= kernel_size)
                    if all(sf[x_key] + 2 * sf[y_key] >= sf[z_key] for sf in success_flats) and all(not (ff[x_key] + 2 * ff[y_key] >= ff[z_key]) for ff in failed_flats):
                        violated_invariants.append(f"{x_key} + 2 * {y_key} >= {z_key}")

                    # 探测张量维度乘积相等 (例如: batch * seq_len == total_size)
                    if all(sf[x_key] * sf[y_key] == sf[z_key] for sf in success_flats) and all(not (ff[x_key] * ff[y_key] == ff[z_key]) for ff in failed_flats):
                        violated_invariants.append(f"{x_key} * {y_key} == {z_key}")

        # 优先级排序，优先返回双变量约束
        violated_invariants = list(set(violated_invariants))
        violated_invariants.sort(key=lambda x: " " in x, reverse=True)
        return violated_invariants

    def _set_flat_value(self, params: Dict[str, Any], flat_key: str, value: float) -> None:
        """按 extract_flat_numeric_params 产生的扁平 key 回写到嵌套 dict/list。"""
        target = params.get("model_structure", params)
        parts = flat_key.split(".")
        for part in parts[:-1]:
            match = re.match(r"(.+)\[(\d+)\]$", part)
            if match:
                target = target[match.group(1)][int(match.group(2))]
            else:
                target = target.setdefault(part, {})
        leaf = parts[-1]
        match = re.match(r"(.+)\[(\d+)\]$", leaf)
        cast_value = int(value) if float(value).is_integer() else float(value)
        if match:
            target[match.group(1)][int(match.group(2))] = cast_value
        else:
            target[leaf] = cast_value

    def _evaluate_constraint(self, constraint: str, flat: Dict[str, float]) -> bool:
        """安全求值单条 Daikon 约束。"""
        expr = constraint
        replacements = {}
        for idx, key in enumerate(sorted(flat.keys(), key=len, reverse=True)):
            name = f"v{idx}"
            replacements[name] = flat[key]
            expr = expr.replace(key, name)
        expr = expr.replace("必须能被", "%").replace("整除 ( % == 0 )", "== 0")
        expr = expr.replace("必须是偶数 ( % 2 == 0 )", "% 2 == 0")
        allowed = {"abs": abs, "math": math}
        return bool(eval(expr, {"__builtins__": {}}, {**allowed, **replacements}))

    def _sync_layer_strings(self, params: Dict[str, Any]) -> None:
        struct = params.get("model_structure", params)
        layers = struct.get("layers")
        if not isinstance(layers, list):
            return
        for idx, layer in enumerate(layers):
            if not isinstance(layer, str):
                continue
            updated = layer
            for key in ("in_channels", "out_channels", "kernel_size", "padding", "stride", "groups"):
                if key in struct:
                    updated = re.sub(rf"{key}=[^,\)]+", f"{key}={struct[key]}", updated)
            layers[idx] = updated

    def _format_numeric_value(self, value: float) -> Any:
        return int(value) if float(value).is_integer() else float(value)

    def _build_validation_case(self, candidate: Dict[str, Any], flat: Dict[str, float], constraint: str, should_satisfy: bool, mutations: List[Dict[str, Any]], index: int) -> Dict[str, Any]:
        model_structure = copy.deepcopy(candidate.get("model_structure", candidate))
        sample_values = {k: self._format_numeric_value(v) for k, v in flat.items()}
        return {
            "case_id": f"{'positive' if should_satisfy else 'negative'}_{index + 1:02d}",
            "expected_constraint_satisfied": should_satisfy,
            "expected_execution": "success" if should_satisfy else "runtime_error",
            "mutated_key": mutations[0]["key"] if mutations else None,
            "mutated_value": mutations[0]["to"] if mutations else None,
            "mutations": mutations,
            "sample_values": sample_values,
            "model_structure": model_structure,
            "generated_case": copy.deepcopy(candidate),
            "constraint_satisfied": should_satisfy,
            "validation_status": "pending_manual",
            "generation_method": "deterministic_constraint_mutation",
            "message": "已由约束变异算法生成样例，待用户在目标执行环境中运行验证"
        }

    def validate_invariants(self, invariants: List[str], successful_params_list: List[Dict[str, Any]], samples_per_side: int = 10) -> List[Dict[str, Any]]:
        """为每条约束生成满足/不满足样例，等待用户在目标环境中验证。"""
        if not invariants or not successful_params_list:
            return []
        base = copy.deepcopy(successful_params_list[0])
        base_flat = self.extract_flat_numeric_params(base.get("model_structure", base))
        reports = []

        for inv in invariants[:5]:
            related_keys = [k for k in base_flat if k in inv]
            target_keys = related_keys[:3] or list(base_flat.keys())[:1]
            cases_by_side = {True: [], False: []}
            seen_by_side = {True: set(), False: set()}
            for should_satisfy in (True, False):
                for source in successful_params_list:
                    source_flat = self.extract_flat_numeric_params(source.get("model_structure", source))
                    for key in target_keys:
                        if key not in source_flat:
                            continue
                        original = source_flat[key]
                        min_value = 0 if "padding" in key else 1
                        deltas = [0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 8, -8, 13, -13, 21, -21]
                        for delta in deltas:
                            candidate = copy.deepcopy(source)
                            new_value = max(min_value, original + delta)
                            self._set_flat_value(candidate, key, new_value)
                            self._sync_layer_strings(candidate)
                            flat = self.extract_flat_numeric_params(candidate.get("model_structure", candidate))
                            try:
                                ok_constraint = self._evaluate_constraint(inv, flat)
                            except Exception:
                                continue
                            if ok_constraint != should_satisfy:
                                continue
                            signature = tuple(sorted((k, self._format_numeric_value(v)) for k, v in flat.items()))
                            if signature in seen_by_side[should_satisfy]:
                                continue
                            seen_by_side[should_satisfy].add(signature)
                            mutations = [{
                                "key": key,
                                "from": self._format_numeric_value(original),
                                "to": self._format_numeric_value(flat.get(key, new_value)),
                                "delta": self._format_numeric_value(flat.get(key, new_value) - original)
                            }]
                            cases_by_side[should_satisfy].append(
                                self._build_validation_case(candidate, flat, inv, should_satisfy, mutations, len(cases_by_side[should_satisfy]))
                            )
                            if len(cases_by_side[should_satisfy]) >= samples_per_side:
                                break
                        if len(cases_by_side[should_satisfy]) >= samples_per_side:
                            break
                    if len(cases_by_side[should_satisfy]) >= samples_per_side:
                        break
                if len(cases_by_side[should_satisfy]) < samples_per_side and should_satisfy:
                    for source in successful_params_list:
                        candidate = copy.deepcopy(source)
                        flat = self.extract_flat_numeric_params(candidate.get("model_structure", candidate))
                        try:
                            ok_constraint = self._evaluate_constraint(inv, flat)
                        except Exception:
                            continue
                        if not ok_constraint:
                            continue
                        signature = tuple(sorted((k, self._format_numeric_value(v)) for k, v in flat.items()))
                        if signature in seen_by_side[should_satisfy]:
                            continue
                        seen_by_side[should_satisfy].add(signature)
                        cases_by_side[should_satisfy].append(
                            self._build_validation_case(candidate, flat, inv, should_satisfy, [], len(cases_by_side[should_satisfy]))
                        )
                        if len(cases_by_side[should_satisfy]) >= samples_per_side:
                            break
            reports.append({
                "constraint": inv,
                "positive_cases": cases_by_side[True],
                "negative_cases": cases_by_side[False],
                "target_cases_per_side": samples_per_side,
                "generation_method": "deterministic_constraint_mutation",
                "is_validated": False,
                "validation_status": "pending_manual"
            })
        return reports

_daikon = DaikonInvariantEngine()

def infer_daikon_invariants(failed_params_list: List[Dict[str, Any]], successful_params_list: List[Dict[str, Any]]) -> List[str]:
    return _daikon.infer_violated_invariants(failed_params_list, successful_params_list)

def validate_daikon_invariants(invariants: List[str], successful_params_list: List[Dict[str, Any]], samples_per_side: int = 10) -> List[Dict[str, Any]]:
    return _daikon.validate_invariants(invariants, successful_params_list, samples_per_side)
