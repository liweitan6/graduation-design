#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
深度学习模糊测试管理系统 - ETL 数据导入脚本
功能：将测试日志解析后分别存入 MySQL（元数据）和 Milvus（向量）
环境：graduation_design (Python 3.10)
依赖：pymysql, pymilvus, sentence-transformers, numpy, sklearn
"""
#python scripts\import_data.py
import json
import numpy as np
from typing import List, Dict, Any, Tuple
from sentence_transformers import SentenceTransformer
from sklearn.decomposition import PCA
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
import pymysql

# ============================================
# 配置常量
# ============================================
MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "root123456",
    "database": "fuzzing_db",
    "charset": "utf8mb4"
}

MILVUS_CONFIG = {
    "host": "localhost",
    "port": 19530
}

COLLECTION_STRUCTURE = "fuzzing_structure"  # 结构向量集合（用于多样性分析）
COLLECTION_LOG = "fuzzing_logs"              # 日志向量集合（用于错误检索）
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
VECTOR_DIM = 384  # all-MiniLM-L6-v2 输出维度


# ============================================
# Step 0: 生成模拟数据
# ============================================
def generate_mock_data() -> List[Dict[str, Any]]:
    """
    生成高度真实的深度学习模糊测试日志模拟数据
    返回包含 10 条测试用例的列表，每个用例包含：
    - model_structure: 计算图结构（用于结构向量化）
    - error_message: 错误日志（用于日志向量化）
    """
    mock_logs = [
        {
            "case_uid": "fuzz_resnet50_seed_001",
            "status": "Crash",
            "execution_time": 0.85,
            "edge_coverage": 2340,
            "model_structure": {
                "layers": ["Input", "Conv2d", "BatchNorm2d", "ReLU", "MaxPool2d", "Conv2d", "BatchNorm2d", "ReLU", "AdaptiveAvgPool2d", "Linear"],
                "connections": "Input->Conv2d->BatchNorm2d->ReLU->MaxPool2d->Conv2d->BatchNorm2d->ReLU->AdaptiveAvgPool2d->Linear",
                "depth": 10,
                "operators": ["Conv2d", "BatchNorm2d", "ReLU", "MaxPool2d", "AdaptiveAvgPool2d", "Linear"]
            },
            "error_message": "RuntimeError: CUDA out of memory. Tried to allocate 512 MiB (GPU 0; 8.00 GiB total capacity)",
            "parameters": {"model": "resnet50", "lr": 0.001, "optimizer": "Adam", "batch_size": 64, "mutation": "random"}
        },
        {
            "case_uid": "fuzz_vgg16_seed_002",
            "status": "Crash",
            "execution_time": 1.23,
            "edge_coverage": 1890,
            "model_structure": {
                "layers": ["Input", "Conv2d", "ReLU", "Conv2d", "ReLU", "MaxPool2d", "Conv2d", "ReLU", "MaxPool2d", "Linear", "ReLU", "Linear"],
                "connections": "Input->Conv2d->ReLU->Conv2d->ReLU->MaxPool2d->Conv2d->ReLU->MaxPool2d->Linear->ReLU->Linear",
                "depth": 12,
                "operators": ["Conv2d", "ReLU", "MaxPool2d", "Linear"]
            },
            "error_message": "RuntimeError: size mismatch, m1: [32 x 512], m2: [256 x 10] at /pytorch/aten/src/TH/generic/THTensorMath.cpp:41",
            "parameters": {"model": "vgg16", "lr": 0.01, "optimizer": "SGD", "batch_size": 32, "mutation": "guided"}
        },
        {
            "case_uid": "fuzz_bert_seed_003",
            "status": "Timeout",
            "execution_time": 30.00,
            "edge_coverage": 450,
            "model_structure": {
                "layers": ["Embedding", "LayerNorm", "MultiHeadAttention", "Add", "LayerNorm", "Linear", "GELU", "Linear", "Add"],
                "connections": "Embedding->LayerNorm->MultiHeadAttention->Add->LayerNorm->Linear->GELU->Linear->Add",
                "depth": 9,
                "operators": ["Embedding", "LayerNorm", "MultiHeadAttention", "Linear", "GELU", "Add"]
            },
            "error_message": "TimeoutError: Execution exceeded maximum allowed time (30s). Model stuck in infinite loop during forward pass.",
            "parameters": {"model": "bert-base", "lr": 0.0001, "optimizer": "AdamW", "max_length": 512, "mutation": "semantic"}
        },
        {
            "case_uid": "fuzz_mobilenet_seed_004",
            "status": "Success",
            "execution_time": 0.32,
            "edge_coverage": 3120,
            "model_structure": {
                "layers": ["Input", "Conv2d", "BatchNorm2d", "ReLU6", "DepthwiseConv2d", "BatchNorm2d", "ReLU6", "Conv2d", "BatchNorm2d"],
                "connections": "Input->Conv2d->BatchNorm2d->ReLU6->DepthwiseConv2d->BatchNorm2d->ReLU6->Conv2d->BatchNorm2d",
                "depth": 9,
                "operators": ["Conv2d", "BatchNorm2d", "ReLU6", "DepthwiseConv2d"]
            },
            "error_message": None,
            "parameters": {"model": "mobilenet_v2", "lr": 0.005, "optimizer": "Adam", "batch_size": 128, "mutation": "random"}
        },
        {
            "case_uid": "fuzz_densenet_seed_005",
            "status": "Crash",
            "execution_time": 0.67,
            "edge_coverage": 2780,
            "model_structure": {
                "layers": ["Input", "Conv2d", "BatchNorm2d", "ReLU", "MaxPool2d", "DenseBlock", "Transition", "DenseBlock", "Linear"],
                "connections": "Input->Conv2d->BatchNorm2d->ReLU->MaxPool2d->DenseBlock->Transition->DenseBlock->Linear",
                "depth": 9,
                "operators": ["Conv2d", "BatchNorm2d", "ReLU", "MaxPool2d", "DenseBlock", "Transition", "Linear"]
            },
            "error_message": "Segmentation fault (core dumped). Stack trace: libc.so.6 -> libcudnn.so.8 -> model_forward()",
            "parameters": {"model": "densenet121", "lr": 0.002, "optimizer": "RMSprop", "batch_size": 48, "mutation": "gradient"}
        },
        {
            "case_uid": "fuzz_inception_seed_006",
            "status": "Crash",
            "execution_time": 1.89,
            "edge_coverage": 1560,
            "model_structure": {
                "layers": ["Input", "Conv2d", "MaxPool2d", "InceptionA", "InceptionB", "InceptionC", "AdaptiveAvgPool2d", "Dropout", "Linear"],
                "connections": "Input->Conv2d->MaxPool2d->InceptionA->InceptionB->InceptionC->AdaptiveAvgPool2d->Dropout->Linear",
                "depth": 9,
                "operators": ["Conv2d", "MaxPool2d", "InceptionA", "InceptionB", "InceptionC", "AdaptiveAvgPool2d", "Dropout", "Linear"]
            },
            "error_message": "ValueError: Expected input batch_size (16) to match target batch_size (32)",
            "parameters": {"model": "inception_v3", "lr": 0.001, "optimizer": "Adam", "batch_size": 16, "mutation": "crossover"}
        },
        {
            "case_uid": "fuzz_efficientnet_seed_007",
            "status": "Success",
            "execution_time": 0.45,
            "edge_coverage": 4210,
            "model_structure": {
                "layers": ["Input", "Conv2d", "BatchNorm2d", "Swish", "MBConv", "MBConv", "MBConv", "Conv2d", "AdaptiveAvgPool2d", "Linear"],
                "connections": "Input->Conv2d->BatchNorm2d->Swish->MBConv->MBConv->MBConv->Conv2d->AdaptiveAvgPool2d->Linear",
                "depth": 10,
                "operators": ["Conv2d", "BatchNorm2d", "Swish", "MBConv", "AdaptiveAvgPool2d", "Linear"]
            },
            "error_message": None,
            "parameters": {"model": "efficientnet_b0", "lr": 0.003, "optimizer": "Adam", "batch_size": 64, "mutation": "random"}
        },
        {
            "case_uid": "fuzz_transformer_seed_008",
            "status": "Crash",
            "execution_time": 2.10,
            "edge_coverage": 980,
            "model_structure": {
                "layers": ["Embedding", "PositionalEncoding", "TransformerEncoderLayer", "TransformerEncoderLayer", "Linear"],
                "connections": "Embedding->PositionalEncoding->TransformerEncoderLayer->TransformerEncoderLayer->Linear",
                "depth": 5,
                "operators": ["Embedding", "PositionalEncoding", "TransformerEncoderLayer", "Linear"]
            },
            "error_message": "RuntimeError: Expected all tensors to be on the same device, but found at least two devices, cuda:0 and cpu!",
            "parameters": {"model": "transformer", "lr": 0.0001, "optimizer": "AdamW", "num_heads": 8, "mutation": "semantic"}
        },
        {
            "case_uid": "fuzz_yolov5_seed_009",
            "status": "Success",
            "execution_time": 0.78,
            "edge_coverage": 3890,
            "model_structure": {
                "layers": ["Input", "Focus", "Conv2d", "C3", "Conv2d", "C3", "SPP", "C3", "Conv2d", "Upsample", "Concat", "Detect"],
                "connections": "Input->Focus->Conv2d->C3->Conv2d->C3->SPP->C3->Conv2d->Upsample->Concat->Detect",
                "depth": 12,
                "operators": ["Focus", "Conv2d", "C3", "SPP", "Upsample", "Concat", "Detect"]
            },
            "error_message": None,
            "parameters": {"model": "yolov5s", "lr": 0.01, "optimizer": "SGD", "img_size": 640, "mutation": "random"}
        },
        {
            "case_uid": "fuzz_lstm_seed_010",
            "status": "Crash",
            "execution_time": 0.56,
            "edge_coverage": 1120,
            "model_structure": {
                "layers": ["Embedding", "LSTM", "LSTM", "Dropout", "Linear"],
                "connections": "Embedding->LSTM->LSTM->Dropout->Linear",
                "depth": 5,
                "operators": ["Embedding", "LSTM", "Dropout", "Linear"]
            },
            "error_message": "IndexError: index 256 is out of bounds for dimension 1 with size 128. LSTM hidden state corruption detected.",
            "parameters": {"model": "lstm", "lr": 0.005, "optimizer": "Adam", "hidden_size": 128, "mutation": "boundary"}
        }
    ]
    
    print(f"[Step 0] ✅ 生成模拟数据完成，共 {len(mock_logs)} 条测试用例")
    return mock_logs


# ============================================
# Step 1: 向量化 (Embedding) - 双向量策略
# ============================================
def get_vectors(data: List[Dict[str, Any]], model_name: str = EMBEDDING_MODEL) -> Tuple[np.ndarray, np.ndarray, SentenceTransformer]:
    """
    使用 sentence-transformers 生成双向量:
    - structure_vectors: 对 model_structure 进行向量化（用于多样性分析）
    - log_vectors: 对 error_message 进行向量化（用于错误检索）
    
    Args:
        data: 测试用例列表
        model_name: 预训练模型名称
        
    Returns:
        structure_vectors: 形状为 (n_samples, 384) 的结构向量数组
        log_vectors: 形状为 (n_samples, 384) 的日志向量数组
        model: 加载的模型实例（可复用）
    """
    print(f"[Step 1] 🔧 加载 Embedding 模型: {model_name} ...")
    model = SentenceTransformer(model_name)
    
    # 构建结构文本列表（用于多样性分析）
    structure_texts = []
    for item in data:
        structure = item.get("model_structure", {})
        # 将结构 JSON 转换为可读文本，便于语义向量化
        structure_text = f"Model structure: layers={structure.get('layers', [])}, " \
                        f"connections={structure.get('connections', '')}, " \
                        f"depth={structure.get('depth', 0)}, " \
                        f"operators={structure.get('operators', [])}"
        structure_texts.append(structure_text)
    
    # 构建日志文本列表（用于错误检索）
    log_texts = []
    for item in data:
        if item["error_message"]:
            log_texts.append(item["error_message"])
        else:
            # 对于成功的用例，使用状态和参数信息作为语义表示
            log_texts.append(f"Success: {item['status']} - Model {item['parameters'].get('model', 'unknown')} executed without errors")
    
    print(f"[Step 1] 🔄 正在向量化 {len(structure_texts)} 条结构文本...")
    structure_vectors = model.encode(structure_texts, show_progress_bar=True)
    
    print(f"[Step 1] 🔄 正在向量化 {len(log_texts)} 条日志文本...")
    log_vectors = model.encode(log_texts, show_progress_bar=True)
    
    print(f"[Step 1] ✅ 双向量化完成:")
    print(f"         - 结构向量维度: {structure_vectors.shape}")
    print(f"         - 日志向量维度: {log_vectors.shape}")
    
    return np.array(structure_vectors), np.array(log_vectors), model


# ============================================
# Step 2: 降维 (PCA for Visualization)
# ============================================
def reduce_dimension(vectors: np.ndarray, n_components: int = 2) -> np.ndarray:
    """
    使用 PCA 将高维向量降维到 2D，用于前端可视化
    
    注意：由于演示数据量较少，使用 PCA 而非 t-SNE
         t-SNE 的 perplexity 参数要求样本数 > 3 * perplexity
    
    Args:
        vectors: 原始高维向量 (n_samples, 384)
        n_components: 目标维度（默认 2）
        
    Returns:
        降维后的坐标数组 (n_samples, 2)
    """
    print(f"[Step 2] 🔄 执行 PCA 降维: {vectors.shape[1]}D -> {n_components}D ...")
    
    # 确保 n_components 不超过样本数和特征数
    n_samples, n_features = vectors.shape
    n_components = min(n_components, n_samples, n_features)
    
    pca = PCA(n_components=n_components, random_state=42)
    reduced = pca.fit_transform(vectors)
    
    # 归一化到 [-1, 1] 范围，便于前端展示
    reduced = (reduced - reduced.min(axis=0)) / (reduced.max(axis=0) - reduced.min(axis=0) + 1e-8)
    reduced = reduced * 2 - 1  # 转换到 [-1, 1]
    
    print(f"[Step 2] ✅ PCA 降维完成，解释方差比: {pca.explained_variance_ratio_.sum():.2%}")
    return reduced


# ============================================
# Step 3: Milvus 向量入库 - 双集合策略 (兼容 Milvus 2.3.x)
# ============================================
def save_to_milvus(structure_vectors: np.ndarray, log_vectors: np.ndarray) -> Tuple[List[int], List[int]]:
    """
    将双向量数据存入 Milvus 两个独立集合，返回自动生成的向量 IDs
    
    注意：Milvus 2.3.x 不支持多向量字段，因此使用两个独立集合
    
    Args:
        structure_vectors: 结构向量数组 (n_samples, 384) - 用于多样性分析
        log_vectors: 日志向量数组 (n_samples, 384) - 用于错误检索
        
    Returns:
        (structure_ids, log_ids): 两个集合分别返回的主键 ID 列表
    """
    import time
    
    print(f"[Step 3] 🔗 连接 Milvus: {MILVUS_CONFIG['host']}:{MILVUS_CONFIG['port']} ...")
    connections.connect("default", **MILVUS_CONFIG)
    
    def create_collection(name: str, vectors: np.ndarray) -> List[int]:
        """创建单个集合并插入数据"""
        # 如果集合存在则删除
        if utility.has_collection(name):
            print(f"[Step 3] ⚠️  集合 '{name}' 已存在，正在删除...")
            utility.drop_collection(name)
            time.sleep(1)
        
        # 定义 Schema
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=VECTOR_DIM)
        ]
        schema = CollectionSchema(fields, description=f"{name} embeddings")
        
        # 创建集合
        collection = Collection(name=name, schema=schema)
        
        # 插入数据
        insert_result = collection.insert([vectors.tolist()])
        
        # 创建索引
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "COSINE",
            "params": {"nlist": 128}
        }
        collection.create_index(field_name="embedding", index_params=index_params)
        collection.load()
        
        return insert_result.primary_keys
    
    # 创建结构向量集合
    print(f"[Step 3] 🔄 创建结构向量集合 '{COLLECTION_STRUCTURE}'...")
    structure_ids = create_collection(COLLECTION_STRUCTURE, structure_vectors)
    print(f"[Step 3] ✅ 结构向量入库成功，{len(structure_ids)} 条记录")
    
    # 创建日志向量集合
    print(f"[Step 3] 🔄 创建日志向量集合 '{COLLECTION_LOG}'...")
    log_ids = create_collection(COLLECTION_LOG, log_vectors)
    print(f"[Step 3] ✅ 日志向量入库成功，{len(log_ids)} 条记录")
    
    connections.disconnect("default")
    
    return structure_ids, log_ids


# ============================================
# Step 4: MySQL 元数据入库
# ============================================
def save_to_mysql(data: List[Dict[str, Any]], structure_ids: List[int], log_ids: List[int], coords_2d: np.ndarray) -> None:
    """
    将测试用例元数据存入 MySQL，关联 Milvus 双向量 ID 和降维坐标
    
    Args:
        data: 原始测试用例列表
        structure_ids: Milvus 结构向量集合返回的 ID 列表
        log_ids: Milvus 日志向量集合返回的 ID 列表
        coords_2d: PCA 降维后的 2D 坐标数组（基于结构向量）
    """
    print(f"[Step 4] 🔗 连接 MySQL: {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']} ...")
    
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    
    # 清空表（方便调试演示）
    cursor.execute("TRUNCATE TABLE test_case_metadata")
    print(f"[Step 4] ⚠️  已清空 test_case_metadata 表")
    
    # 插入语句 - vector_id 存储结构向量 ID（主要用于多样性分析）
    insert_sql = """
        INSERT INTO test_case_metadata 
        (case_uid, status, edge_coverage, execution_time, error_message, vector_id, parameters)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    
    success_count = 0
    for i, item in enumerate(data):
        # 将降维坐标、模型结构和双向量 ID 添加到 parameters JSON 中
        params = item["parameters"].copy()
        params["vis_x"] = float(coords_2d[i, 0])  # 2D 可视化 X 坐标
        params["vis_y"] = float(coords_2d[i, 1])  # 2D 可视化 Y 坐标
        params["model_structure"] = item.get("model_structure", {})  # 添加模型结构
        params["structure_vector_id"] = structure_ids[i]  # 结构向量 ID
        params["log_vector_id"] = log_ids[i]              # 日志向量 ID
        
        values = (
            item["case_uid"],
            item["status"],
            item["edge_coverage"],
            item["execution_time"],
            item["error_message"],
            structure_ids[i],       # 主 vector_id 使用结构向量 ID（用于多样性分析）
            json.dumps(params)      # JSON 序列化（包含两个向量 ID）
        )
        
        cursor.execute(insert_sql, values)
        success_count += 1
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"[Step 4] ✅ MySQL 入库成功，共插入 {success_count} 条记录")


# ============================================
# 主函数：ETL Pipeline - 双集合策略
# ============================================
def main():
    """
    ETL 主流程：生成数据 -> 双向量化 -> 降维 -> Milvus双集合入库 -> MySQL入库
    """
    print("=" * 60)
    print("🚀 深度学习模糊测试数据导入 ETL Pipeline 启动 (双集合策略)")
    print("=" * 60)
    
    # Step 0: 生成模拟数据
    mock_data = generate_mock_data()
    
    # Step 1: 双向量化（结构向量 + 日志向量）
    structure_vectors, log_vectors, _ = get_vectors(mock_data)
    
    # Step 2: PCA 降维（基于结构向量，用于多样性可视化）
    coords_2d = reduce_dimension(structure_vectors)
    
    # Step 3: 存入 Milvus（双集合入库，分别获取向量 ID）
    structure_ids, log_ids = save_to_milvus(structure_vectors, log_vectors)
    
    # Step 4: 存入 MySQL（关联双向量 ID 和降维坐标）
    save_to_mysql(mock_data, structure_ids, log_ids, coords_2d)
    
    print("=" * 60)
    print("🎉 ETL Pipeline 执行完成！")
    print("=" * 60)
    
    # 打印数据摘要
    print("\n📊 数据摘要:")
    print(f"   - 总用例数: {len(mock_data)}")
    print(f"   - 结构向量维度: {structure_vectors.shape}")
    print(f"   - 日志向量维度: {log_vectors.shape}")
    print(f"   - Milvus 集合: {COLLECTION_STRUCTURE}, {COLLECTION_LOG}")
    print(f"   - MySQL 表: test_case_metadata")


if __name__ == "__main__":
    main()

