#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
深度学习模糊测试管理系统 - 数据接收服务 (API)
功能：接收后端数据，执行向量化与降维，并存入数据库
运行：uvicorn scripts.data_service:app --host 0.0.0.0 --port 5000 --reload
"""

import json
import logging
import numpy as np
import pymysql
from enum import Enum
from typing import List, Dict, Optional, Any
from fastapi import FastAPI, HTTPException, Body

# 深度分析模块（同目录导入）
from log_parser import LogParser, parse_error_message
from fault_locator import FaultLocator, localize_fault
from boundary_analyzer import analyze_boundary_diff, infer_daikon_invariants
from pydantic import BaseModel

import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
from sentence_transformers import SentenceTransformer
from sklearn.decomposition import PCA
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
import httpx
# =======test=======
#python -c "import requests; print(requests.post('http://localhost:5000/api/ask', json={'query':'帮我找一个包含 Conv2d 算子且导致 Segmentation Fault 的测试用例'}).json()['answer'])"



# ==================== 配置 ====================
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
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
VECTOR_DIM = 384

# DeepSeek API 配置
DEEPSEEK_CONFIG = {
    "base_url": "https://api.deepseek.com/v1",
    "api_key": "sk-c8c52290158040a8b8235db446357fa4",  # 请替换为你的 API Key
    "model": "deepseek-chat"              # 可选: deepseek-chat, deepseek-coder
}

# ==================== 初始化 ====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fuzzing_service")
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """服务启动时加载模型和连接 Milvus"""
    global embedding_model
    logger.info("正在加载 Embedding 模型...")
    # HF_ENDPOINT 已经设置，这里会自动从镜像站下载
    embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    
    logger.info("连接 Milvus...")
    connections.connect("default", **MILVUS_CONFIG)
    init_milvus_collection()
    logger.info("服务启动完毕")
    yield

app = FastAPI(title="Fuzzing Data Service", version="1.0", lifespan=lifespan)

# 配置 CORS
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境请指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局模型缓存
embedding_model = None

# ==================== 数据模型 ====================
class TestCase(BaseModel):
    case_uid: str
    status: str
    execution_time: float
    edge_coverage: int
    model_structure: Optional[Dict[str, Any]] = None  # 计算图结构（用于结构向量化）
    error_message: Optional[str] = None
    parameters: Dict[str, Any] = {}

class IngestResponse(BaseModel):
    success: int
    ids: List[int]
    message: str

class SearchRequest(BaseModel):
    query: str                          # 自然语言查询
    top_k: int = 10                     # 返回结果数量
    search_mode: str = "hybrid"         # 检索模式: "structure", "log", "hybrid"
    structure_weight: float = 0.4       # hybrid 模式下结构向量权重
    log_weight: float = 0.6             # hybrid 模式下日志向量权重

class SearchResult(BaseModel):
    case_uid: str
    status: str
    edge_coverage: int
    execution_time: float
    error_message: Optional[str]
    similarity_score: float             # 相似度分数
    match_source: str                   # 匹配来源: "structure", "log", "hybrid"

class SearchResponse(BaseModel):
    total: int
    results: List[SearchResult]
    query: str
    search_mode: str
    query_intent: Optional[str] = None  # 查询意图类型


# ==================== 查询意图分类 ====================

class QueryIntent(str, Enum):
    """查询意图类型枚举"""
    ERROR_LOOKUP = "error_lookup"           # 错误定位型
    STRUCTURE_QUERY = "structure_query"     # 结构查询型
    HYBRID_QUERY = "hybrid_query"           # 复合条件型
    STATISTICS = "statistics"               # 统计分析型
    COMPARISON = "comparison"               # 对比分析型
    RECOMMENDATION = "recommendation"       # 推荐建议型


class StatisticsResponse(BaseModel):
    """统计分析响应模型"""
    query: str
    query_intent: str = "statistics"
    stat_type: str                          # 统计类型: status_distribution, error_ranking, etc.
    data: List[Dict[str, Any]]              # 统计数据
    summary: str                            # 文字摘要


class RAGResponse(BaseModel):
    """RAG 推荐响应模型"""
    query: str
    query_intent: str = "recommendation"
    answer: str                             # LLM 生成的回答
    context: List[Dict[str, Any]]           # 检索到的上下文
    sources: List[str]                      # 来源用例 ID


# ==================== LLM 调用 ====================

def call_deepseek(prompt: str, system_prompt: str = None) -> str:
    """
    调用 DeepSeek API 生成回答
    兼容 OpenAI API 格式
    """
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_CONFIG['api_key']}",
        "Content-Type": "application/json"
    }
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": DEEPSEEK_CONFIG["model"],
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1024
    }
    
    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{DEEPSEEK_CONFIG['base_url']}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"DeepSeek API 调用失败: {e}")
        return f"LLM 调用失败: {str(e)}"

# ==================== 核心逻辑 ====================

# 已迁移至 lifespan context manager

def init_milvus_collection():
    """确保 Milvus 双集合存在 (兼容 Milvus 2.3.x)"""
    index_params = {"index_type": "IVF_FLAT", "metric_type": "COSINE", "params": {"nlist": 128}}
    
    for collection_name in [COLLECTION_STRUCTURE, COLLECTION_LOG]:
        if not utility.has_collection(collection_name):
            logger.info(f"创建 Milvus 集合: {collection_name}")
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=VECTOR_DIM)
            ]
            schema = CollectionSchema(fields, description=f"{collection_name} embeddings")
            col = Collection(name=collection_name, schema=schema)
            col.create_index(field_name="embedding", index_params=index_params)
        
        # 确保集合加载到内存
        try:
            col = Collection(collection_name)
            col.load()
        except Exception as e:
            logger.warning(f"Milvus 集合 {collection_name} 加载失败: {e}")

def vectorize_batch(texts: List[str]) -> np.ndarray:
    """批量向量化"""
    if not embedding_model:
        raise RuntimeError("Embedding model not loaded")
    return embedding_model.encode(texts)

def reduce_dimension_batch(vectors: np.ndarray) -> np.ndarray:
    """对当前批次进行 PCA 降维 (仅用于当前批次的可视化展示)"""
    n_samples = vectors.shape[0]
    if n_samples < 2:
        # 样本太少无法 PCA，返回默认中心点 (但加上微小随机扰动避免重叠)
        return np.random.rand(n_samples, 2) * 0.01
    
    # 最多降到 2 维，且不能超过样本数
    n_components = min(2, n_samples)
    pca = PCA(n_components=n_components)
    reduced = pca.fit_transform(vectors)
    
    # 如果只有 1 维 (n_samples=2 时可能发生)，补一个 0 维度
    if reduced.shape[1] == 1:
        reduced = np.hstack([reduced, np.zeros((n_samples, 1))])
        
    # 简单归一化到 [-1, 1] 方便展示
    _min, _max = reduced.min(axis=0), reduced.max(axis=0)
    range_span = _max - _min
    range_span[range_span == 0] = 1  # 避免除以零
    
    reduced = (reduced - _min) / range_span
    reduced = reduced * 2 - 1 
    return reduced


# ==================== API 路由 ====================

@app.get("/")
async def root():
    """健康检查和 API 状态"""
    return {
        "status": "ok",
        "service": "Fuzzing Data Service",
        "version": "1.0",
        "endpoints": {
            "/": "健康检查 (GET)",
            "/api/ingest": "数据入库 (POST)",
            "/docs": "API 文档 (Swagger UI)",
            "/redoc": "API 文档 (ReDoc)"
        },
        "milvus_collections": [COLLECTION_STRUCTURE, COLLECTION_LOG]
    }
# ==================== API 接口 ====================

@app.post("/api/ingest", response_model=IngestResponse)
async def ingest_logs(cases: List[TestCase]):
    """
    接收测试用例日志，处理后存入数据库 - 双向量策略
    """
    if not cases:
        return IngestResponse(success=0, ids=[], message="No data received")
    
    try:
        logger.info(f"接收到 {len(cases)} 条数据")
        
        # 1. 准备结构文本（用于多样性分析）
        structure_texts = []
        for case in cases:
            structure = case.model_structure or {}
            structure_text = f"Model structure: layers={structure.get('layers', [])}, " \
                           f"connections={structure.get('connections', '')}, " \
                           f"depth={structure.get('depth', 0)}, " \
                           f"operators={structure.get('operators', [])}"
            structure_texts.append(structure_text)
        
        # 2. 准备日志文本（用于错误检索）
        log_texts = []
        for case in cases:
            if case.error_message:
                log_texts.append(case.error_message)
            else:
                log_texts.append(f"Success: {case.status} - Model executed OK")
        
        # 3. 双向量化
        structure_vectors = vectorize_batch(structure_texts)
        log_vectors = vectorize_batch(log_texts)
        
        # 4. 计算临时降维坐标 (基于结构向量，用于前端多样性展示)
        coords_2d = reduce_dimension_batch(structure_vectors)
        
        # 5. 存入 Milvus（双集合策略）
        structure_collection = Collection(COLLECTION_STRUCTURE)
        log_collection = Collection(COLLECTION_LOG)
        
        structure_insert_res = structure_collection.insert([structure_vectors.tolist()])
        structure_ids = structure_insert_res.primary_keys
        
        log_insert_res = log_collection.insert([log_vectors.tolist()])
        log_ids = log_insert_res.primary_keys
        
        # 6. 存入 MySQL
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        sql = """
            INSERT INTO test_case_metadata 
            (case_uid, status, edge_coverage, execution_time, error_message, vector_id, parameters)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            status=VALUES(status),
            edge_coverage=VALUES(edge_coverage),
            execution_time=VALUES(execution_time),
            error_message=VALUES(error_message),
            vector_id=VALUES(vector_id),
            parameters=VALUES(parameters),
            updated_at=NOW()
        """
        
        rows = []
        for i, case in enumerate(cases):
            # 将坐标、模型结构和双向量 ID 合入 parameters
            params = case.parameters.copy()
            params['vis_x'] = float(coords_2d[i][0])
            params['vis_y'] = float(coords_2d[i][1])
            params['model_structure'] = case.model_structure or {}
            params['structure_vector_id'] = structure_ids[i]
            params['log_vector_id'] = log_ids[i]
            
            rows.append((
                case.case_uid,
                case.status,
                case.edge_coverage,
                case.execution_time,
                case.error_message,
                structure_ids[i],  # 主 vector_id 使用结构向量 ID
                json.dumps(params)
            ))
            
        cursor.executemany(sql, rows)
        conn.commit()
        conn.close()
        
        logger.info(f"成功入库 {len(rows)} 条记录 (双集合)")
        return IngestResponse(
            success=len(rows), 
            ids=structure_ids,  # 返回结构向量 ID 作为主 ID
            message="Data ingestion successful (dual collections)"
        )
        
    except Exception as e:
        logger.error(f"处理失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 语义检索 API ====================

# 关键词库（用于分词）
STRUCTURE_KEYWORDS = [
    "Conv2d", "Conv1d", "Conv3d", "Linear", "Dense", "ReLU", "Sigmoid", "Tanh",
    "BatchNorm", "LayerNorm", "Dropout", "MaxPool", "AvgPool", "Softmax",
    "LSTM", "GRU", "Transformer", "Attention", "Embedding", "Flatten",
    "ResNet", "VGG", "MobileNet", "EfficientNet", "BERT", "GPT", "YOLO",
    "算子", "层", "模型", "网络", "结构", "计算图"
]

LOG_KEYWORDS = [
    "Segmentation fault", "CUDA", "out of memory", "OOM", "RuntimeError",
    "ValueError", "IndexError", "TypeError", "AttributeError", "KeyError",
    "Timeout", "超时", "崩溃", "Crash", "Error", "Exception", "Failed",
    "size mismatch", "dimension", "shape", "NaN", "Inf", "overflow",
    "死循环", "内存", "显存", "GPU"
]


def extract_keywords(query: str) -> tuple:
    """
    从查询中提取结构关键词和日志关键词
    返回: (structure_terms, log_terms)
    """
    query_lower = query.lower()
    
    structure_terms = []
    log_terms = []
    
    for kw in STRUCTURE_KEYWORDS:
        if kw.lower() in query_lower:
            structure_terms.append(kw)
    
    for kw in LOG_KEYWORDS:
        if kw.lower() in query_lower:
            log_terms.append(kw)
    
    return structure_terms, log_terms


# 意图分类关键词
STATISTICS_KEYWORDS = ["多少", "统计", "比例", "最多", "最少", "平均", "趋势", "占比", "数量", "总共"]
COMPARISON_KEYWORDS = ["对比", "区别", "不同", "为什么", "差异", "比较", "相同", "一样"]
RECOMMENDATION_KEYWORDS = ["如何", "怎么", "建议", "推荐", "注意", "避免", "应该", "怎样", "方法"]


def classify_intent(query: str) -> QueryIntent:
    """
    基于规则的意图分类器
    根据查询内容判断用户意图类型
    """
    query_lower = query.lower()
    
    # 1. 统计分析型
    if any(kw in query_lower for kw in STATISTICS_KEYWORDS):
        return QueryIntent.STATISTICS
    
    # 2. 对比分析型
    if any(kw in query_lower for kw in COMPARISON_KEYWORDS):
        return QueryIntent.COMPARISON
    
    # 3. 推荐建议型
    if any(kw in query_lower for kw in RECOMMENDATION_KEYWORDS):
        return QueryIntent.RECOMMENDATION
    
    # 4. 根据结构/日志关键词判断
    struct_terms, log_terms = extract_keywords(query)
    
    if struct_terms and log_terms:
        return QueryIntent.HYBRID_QUERY
    elif struct_terms:
        return QueryIntent.STRUCTURE_QUERY
    elif log_terms:
        return QueryIntent.ERROR_LOOKUP
    else:
        return QueryIntent.HYBRID_QUERY  # 默认走混合检索


# ==================== 统计分析处理器 ====================

def handle_statistics(query: str) -> StatisticsResponse:
    """
    统计分析处理器 - 执行 SQL 聚合查询
    
    支持的统计类型:
    - 状态分布: "多少用例失败/成功"
    - 算子崩溃: "哪种算子最容易崩溃"
    - 错误类型: "常见的错误类型"
    - 时间分析: "平均执行时间"
    """
    query_lower = query.lower()
    
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    try:
        # 判断统计类型
        if any(kw in query_lower for kw in ["状态", "成功", "失败", "崩溃", "通过"]):
            # 状态分布统计
            sql = """
                SELECT status, COUNT(*) as count 
                FROM test_case_metadata 
                GROUP BY status 
                ORDER BY count DESC
            """
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            total = sum(r["count"] for r in rows)
            summary_parts = [f"{r['status']}: {r['count']}条 ({r['count']*100//total if total > 0 else 0}%)" for r in rows]
            
            return StatisticsResponse(
                query=query,
                stat_type="status_distribution",
                data=[dict(r) for r in rows],
                summary=f"共{total}条测试用例。" + "，".join(summary_parts)
            )
        
        elif any(kw in query_lower for kw in ["算子", "层", "模型", "结构"]):
            # 算子/结构相关统计
            sql = """
                SELECT 
                    JSON_EXTRACT(parameters, '$.model_structure.operators') as operators,
                    status,
                    COUNT(*) as count
                FROM test_case_metadata
                WHERE status != 'Success'
                GROUP BY operators, status
                ORDER BY count DESC
                LIMIT 10
            """
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            # 解析算子并统计
            operator_stats = {}
            for r in rows:
                ops = r.get("operators", "[]")
                if ops:
                    try:
                        op_list = json.loads(ops) if isinstance(ops, str) else ops
                        for op in op_list:
                            if op not in operator_stats:
                                operator_stats[op] = 0
                            operator_stats[op] += r["count"]
                    except:
                        pass
            
            sorted_ops = sorted(operator_stats.items(), key=lambda x: x[1], reverse=True)[:5]
            data = [{"operator": op, "crash_count": cnt} for op, cnt in sorted_ops]
            
            if sorted_ops:
                summary = f"最容易导致崩溃的算子: " + ", ".join([f"{op}({cnt}次)" for op, cnt in sorted_ops[:3]])
            else:
                summary = "暂无足够数据进行算子统计"
            
            return StatisticsResponse(
                query=query,
                stat_type="operator_crash_ranking",
                data=data,
                summary=summary
            )
        
        elif any(kw in query_lower for kw in ["错误", "异常", "error", "exception"]):
            # 错误类型统计
            sql = """
                SELECT 
                    CASE 
                        WHEN error_message LIKE '%CUDA%' OR error_message LIKE '%GPU%' THEN 'CUDA/GPU Error'
                        WHEN error_message LIKE '%memory%' OR error_message LIKE '%OOM%' THEN 'Memory Error'
                        WHEN error_message LIKE '%Segmentation%' THEN 'Segmentation Fault'
                        WHEN error_message LIKE '%Timeout%' OR error_message LIKE '%超时%' THEN 'Timeout'
                        WHEN error_message LIKE '%shape%' OR error_message LIKE '%dimension%' THEN 'Shape Mismatch'
                        WHEN error_message IS NULL OR error_message = '' THEN 'Success'
                        ELSE 'Other Error'
                    END as error_type,
                    COUNT(*) as count
                FROM test_case_metadata
                GROUP BY error_type
                ORDER BY count DESC
            """
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            total = sum(r["count"] for r in rows)
            summary_parts = [f"{r['error_type']}: {r['count']}条" for r in rows if r["error_type"] != "Success"]
            
            return StatisticsResponse(
                query=query,
                stat_type="error_type_distribution",
                data=[dict(r) for r in rows],
                summary=f"错误类型分布: " + ", ".join(summary_parts[:5]) if summary_parts else "暂无错误记录"
            )
        
        elif any(kw in query_lower for kw in ["时间", "耗时", "执行", "平均"]):
            # 执行时间统计
            sql = """
                SELECT 
                    status,
                    COUNT(*) as count,
                    ROUND(AVG(execution_time), 3) as avg_time,
                    ROUND(MAX(execution_time), 3) as max_time,
                    ROUND(MIN(execution_time), 3) as min_time
                FROM test_case_metadata
                GROUP BY status
            """
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            summary_parts = [f"{r['status']}: 平均{r['avg_time']}s" for r in rows]
            
            return StatisticsResponse(
                query=query,
                stat_type="execution_time_analysis",
                data=[dict(r) for r in rows],
                summary="执行时间统计: " + ", ".join(summary_parts)
            )
        
        else:
            # 默认: 返回总览统计
            sql = """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'Success' THEN 1 ELSE 0 END) as success_count,
                    SUM(CASE WHEN status != 'Success' THEN 1 ELSE 0 END) as fail_count,
                    ROUND(AVG(execution_time), 3) as avg_time,
                    ROUND(AVG(edge_coverage), 0) as avg_coverage
                FROM test_case_metadata
            """
            cursor.execute(sql)
            row = cursor.fetchone()
            
            return StatisticsResponse(
                query=query,
                stat_type="overview",
                data=[dict(row)] if row else [],
                summary=f"总计{row['total']}条用例，成功{row['success_count']}条，失败{row['fail_count']}条，平均执行时间{row['avg_time']}s"
            )
    
    finally:
        conn.close()


@app.get("/api/statistics")
async def get_statistics(query: str = "总览"):
    """统计分析 API 端点"""
    try:
        return handle_statistics(query)
    except Exception as e:
        logger.error(f"统计查询失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== RAG 推荐处理器 ====================

SYSTEM_PROMPT = """你是一个深度学习模糊测试专家助手。你的任务是根据用户问题和检索到的测试用例上下文，提供专业的分析和建议。

请遵循以下原则:
1. 基于提供的测试用例数据给出具体建议
2. 如果问题涉及错误分析，解释可能的根因
3. 如果问题涉及优化建议，给出可行的改进方案
4. 保持回答简洁专业，使用中文回答"""


async def handle_recommendation(query: str, top_k: int = 3) -> RAGResponse:
    """
    推荐建议处理器 - RAG 流程 (增强版：双路混合检索)
    1. 意图识别 & 关键词提取
    2. 双路向量检索 (Structure + Log)
    3. 加权融合
    4. 构建上下文
    5. 调用 LLM 生成回答
    """
    logger.info(f"RAG 处理: query='{query}'")
    
    # 1. 关键词提取 & 向量化
    structure_terms, log_terms = extract_keywords(query)
    
    structure_query = " ".join(structure_terms) if structure_terms else query
    log_query = " ".join(log_terms) if log_terms else query
    
    # 向量化
    vectors = vectorize_batch([structure_query, log_query])
    structure_vector = vectors[0].tolist()
    log_vector = vectors[1].tolist()
    
    search_params = {"metric_type": "COSINE", "params": {"nprobe": 16}}
    
    # 2. 双路检索
    # 结构集合检索
    structure_collection = Collection(COLLECTION_STRUCTURE)
    struct_res = structure_collection.search(
        data=[structure_vector],
        anns_field="embedding",
        param=search_params,
        limit=top_k * 3,
        output_fields=["id"]
    )
    structure_scores = {hit.id: hit.score for hit in struct_res[0]}
    
    # 日志集合检索
    log_collection = Collection(COLLECTION_LOG)
    log_res = log_collection.search(
        data=[log_vector],
        anns_field="embedding",
        param=search_params,
        limit=top_k * 3,
        output_fields=["id"]
    )
    log_scores = {hit.id: hit.score for hit in log_res[0]}
    
    # 3. 动态权重融合
    if structure_terms and log_terms:
        struct_weight = 0.5
        log_weight = 0.5
    elif structure_terms:
        struct_weight = 0.8
        log_weight = 0.2
    elif log_terms:
        struct_weight = 0.2
        log_weight = 0.8
    else:
        struct_weight = 0.5
        log_weight = 0.5
        
    all_ids = set(structure_scores.keys()) | set(log_scores.keys())
    merged_scores = {}
    
    for vid in all_ids:
        s_score = structure_scores.get(vid, 0)
        l_score = log_scores.get(vid, 0)
        final_score = s_score * struct_weight + l_score * log_weight
        merged_scores[vid] = final_score
    
    # 获取 Top K 向量 ID
    sorted_ids = sorted(merged_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
    vector_ids = [vid for vid, _ in sorted_ids]
    
    if not vector_ids:
        return RAGResponse(
            query=query,
            answer="未找到相关测试用例，无法提供具体建议。",
            context=[],
            sources=[]
        )
    
    # 2. 从 MySQL 查询完整数据
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    placeholders = ",".join(["%s"] * len(vector_ids))
    sql = f"""
        SELECT case_uid, status, edge_coverage, execution_time, error_message, parameters, created_at
        FROM test_case_metadata 
        WHERE vector_id IN ({placeholders})
           OR JSON_EXTRACT(parameters, '$.log_vector_id') IN ({placeholders})
        LIMIT {top_k}
    """
    cursor.execute(sql, vector_ids + vector_ids)
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return RAGResponse(
            query=query,
            answer="未找到相关测试用例数据。",
            context=[],
            sources=[]
        )
    
    # 3. 构建上下文
    context_parts = []
    sources = []
    context_data = []
    
    for i, row in enumerate(rows):
        sources.append(row["case_uid"])
        params = json.loads(row["parameters"]) if row["parameters"] else {}
        model_struct = params.get("model_structure", {})
        
        context_parts.append(f"""
用例 {i+1}: {row['case_uid']}
- 状态: {row['status']}
- 执行时间: {row['execution_time']}s
- 边覆盖: {row['edge_coverage']}
- 错误信息: {row['error_message'] or '无'}
- 模型结构: {json.dumps(model_struct.get('operators', []), ensure_ascii=False)}
""")
        # 返回完整数据供前端详情页使用
        created_at_str = row["created_at"].isoformat() if row.get("created_at") else None
        context_data.append({
            "case_uid": row["case_uid"],
            "status": row["status"],
            "error_message": row["error_message"],
            "execution_time": row["execution_time"],
            "edge_coverage": row["edge_coverage"],
            "parameters": row["parameters"],  # 包含 model_structure 和 log_content
            "created_at": created_at_str,
            "similarity_score": merged_scores.get(row.get("vector_id"), 0.5),
            "match_source": "hybrid"
        })
    
    context_text = "\n".join(context_parts)
    
    # 4. 调用 LLM
    prompt = f"""用户问题: {query}

相关测试用例上下文:
{context_text}

请根据以上信息回答用户问题:"""
    
    answer = call_deepseek(prompt, SYSTEM_PROMPT)
    
    return RAGResponse(
        query=query,
        answer=answer,
        context=context_data,
        sources=sources
    )


@app.post("/api/ask")
async def ask_question(query: str = Body(..., embed=True)):
    """RAG 问答端点 - 支持推荐建议类问题"""
    try:
        return await handle_recommendation(query)
    except Exception as e:
        logger.error(f"RAG 查询失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/recent_cases")
async def get_recent_cases(limit: int = 10):
    """获取最近的测试用例"""
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        # 修改: 确保按照 ID 倒序排列（模拟最新）
        sql = """
            SELECT case_uid, status, edge_coverage, execution_time, 
                   COALESCE(error_message, '') as error_message,
                   DATE_FORMAT(NOW(), '%%Y-%%m-%%d %%H:%%i:%%s') as created_at 
            FROM test_case_metadata 
            ORDER BY id DESC 
            LIMIT %s
        """
        cursor.execute(sql, (limit,))
        rows = cursor.fetchall()
        return rows
    except Exception as e:
        logger.error(f"获取最近用例失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/search", response_model=SearchResponse)
async def semantic_search(request: SearchRequest):
    """
    智能语义检索接口 - 意图分类 + 分词检索 + 加权求和
    
    处理流程:
    1. 意图分类：判断查询类型
    2. 从查询中提取结构关键词和日志关键词
    3. 分别构建结构查询向量和日志查询向量
    4. 在对应集合中检索
    5. 加权求和融合分数
    6. 返回 Top K 结果
    
    示例查询:
    - 错误定位: "CUDA OOM 的用例"
    - 结构查询: "包含 Conv2d 的用例"
    - 复合条件: "Conv2d 导致 Segmentation Fault"
    """
    TOP_K = 3  # 固定返回 Top 3
    
    try:
        logger.info(f"收到检索请求: query='{request.query}'")
        
        # 0. 意图分类
        intent = classify_intent(request.query)
        logger.info(f"查询意图: {intent.value}")
        
        # 统计分析型：走 SQL 聚合（暂返回提示）
        if intent == QueryIntent.STATISTICS:
            return SearchResponse(
                total=0,
                results=[],
                query=request.query,
                search_mode="statistics",
                query_intent=intent.value
            )
        
        # 推荐建议型：需要 LLM 支持（暂返回提示）
        if intent == QueryIntent.RECOMMENDATION:
            return SearchResponse(
                total=0,
                results=[],
                query=request.query,
                search_mode="recommendation",
                query_intent=intent.value
            )
        
        # 1. 分词：提取结构关键词和日志关键词
        structure_terms, log_terms = extract_keywords(request.query)
        logger.info(f"分词结果 - 结构关键词: {structure_terms}, 日志关键词: {log_terms}")
        
        # 2. 构建分词后的查询文本
        structure_query = " ".join(structure_terms) if structure_terms else request.query
        log_query = " ".join(log_terms) if log_terms else request.query
        
        # 3. 分别向量化
        structure_vector = vectorize_batch([structure_query])[0].tolist()
        log_vector = vectorize_batch([log_query])[0].tolist()
        
        # 4. 构建搜索参数
        search_params = {"metric_type": "COSINE", "params": {"nprobe": 16}}
        
        # 5. 分别检索两个集合
        structure_collection = Collection(COLLECTION_STRUCTURE)
        log_collection = Collection(COLLECTION_LOG)
        
        # 结构集合检索
        struct_res = structure_collection.search(
            data=[structure_vector],
            anns_field="embedding",
            param=search_params,
            limit=TOP_K * 3,
            output_fields=["id"]
        )
        structure_scores = {hit.id: hit.score for hit in struct_res[0]}
        logger.info(f"结构检索: query='{structure_query}', 返回 {len(structure_scores)} 条")
        
        # 日志集合检索
        log_res = log_collection.search(
            data=[log_vector],
            anns_field="embedding",
            param=search_params,
            limit=TOP_K * 3,
            output_fields=["id"]
        )
        log_scores = {hit.id: hit.score for hit in log_res[0]}
        logger.info(f"日志检索: query='{log_query}', 返回 {len(log_scores)} 条")
        
        # 6. 根据意图动态调整权重
        if intent == QueryIntent.STRUCTURE_QUERY:
            struct_weight = 0.9
            log_weight = 0.1
        elif intent == QueryIntent.ERROR_LOOKUP:
            struct_weight = 0.1
            log_weight = 0.9
        elif structure_terms and log_terms:
            struct_weight = request.structure_weight
            log_weight = request.log_weight
        elif structure_terms:
            struct_weight = 0.8
            log_weight = 0.2
        elif log_terms:
            struct_weight = 0.2
            log_weight = 0.8
        else:
            struct_weight = 0.5
            log_weight = 0.5
        
        logger.info(f"权重: structure={struct_weight}, log={log_weight}")
        
        # 合并所有候选 ID
        all_ids = set(structure_scores.keys()) | set(log_scores.keys())
        merged_scores = {}
        
        for vid in all_ids:
            s_score = structure_scores.get(vid, 0)
            l_score = log_scores.get(vid, 0)
            final_score = s_score * struct_weight + l_score * log_weight
            
            # 判断来源
            if vid in structure_scores and vid in log_scores:
                source = "hybrid"
            elif vid in structure_scores:
                source = "structure"
            else:
                source = "log"
            
            merged_scores[vid] = (final_score, source)
        
        # 7. 排序取 Top K
        sorted_results = sorted(merged_scores.items(), key=lambda x: x[1][0], reverse=True)[:TOP_K]
        
        if not sorted_results:
            return SearchResponse(total=0, results=[], query=request.query, search_mode=intent.value, query_intent=intent.value)
        
        # 8. 从 MySQL 查询完整元数据
        vector_ids = [vid for vid, _ in sorted_results]
        score_map = {vid: (score, source) for vid, (score, source) in sorted_results}
        
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        placeholders = ",".join(["%s"] * len(vector_ids))
        sql = f"""
            SELECT case_uid, status, edge_coverage, execution_time, error_message, vector_id, parameters
            FROM test_case_metadata 
            WHERE vector_id IN ({placeholders})
               OR JSON_EXTRACT(parameters, '$.log_vector_id') IN ({placeholders})
        """
        cursor.execute(sql, vector_ids + vector_ids)
        rows = cursor.fetchall()
        conn.close()
        
        # 9. 构建返回结果
        results = []
        seen_uids = set()
        for row in rows:
            if row["case_uid"] in seen_uids:
                continue
            seen_uids.add(row["case_uid"])
            
            vid = row["vector_id"]
            params = json.loads(row["parameters"]) if row["parameters"] else {}
            log_vid = params.get("log_vector_id")
            
            score, source = 0.0, "unknown"
            if vid in score_map:
                score, source = score_map[vid]
            elif log_vid in score_map:
                score, source = score_map[log_vid]
            
            results.append(SearchResult(
                case_uid=row["case_uid"],
                status=row["status"],
                edge_coverage=row["edge_coverage"],
                execution_time=row["execution_time"],
                error_message=row["error_message"],
                similarity_score=round(score, 4),
                match_source=source
            ))
        
        # 按分数重新排序
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        results = results[:TOP_K]
        
        logger.info(f"检索完成，返回 {len(results)} 条结果")
        return SearchResponse(
            total=len(results),
            results=results,
            query=request.query,
            search_mode=intent.value,
            query_intent=intent.value
        )
        
    except Exception as e:
        logger.error(f"检索失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 覆盖率缺口分析 ====================

# 已知的 DL 算子全集（常见底层算子）
KNOWN_OPERATORS = [
    "Conv2d", "Conv1d", "Conv3d", "ConvTranspose2d",
    "BatchNorm2d", "BatchNorm1d", "LayerNorm", "GroupNorm", "InstanceNorm2d",
    "ReLU", "ReLU6", "LeakyReLU", "GELU", "Swish", "Sigmoid", "Tanh", "Softmax",
    "MaxPool2d", "AvgPool2d", "AdaptiveAvgPool2d", "AdaptiveMaxPool2d",
    "Linear", "Embedding",
    "LSTM", "GRU", "RNN",
    "MultiHeadAttention", "TransformerEncoderLayer",
    "Dropout", "Add", "Concat", "Reshape", "Flatten",
    "Upsample", "DepthwiseConv2d", "MatMul",
]

# 算子复杂度权重（用于 CEI 计算）
OPERATOR_WEIGHTS = {
    "Conv2d": 3, "Conv1d": 2, "Conv3d": 4, "ConvTranspose2d": 3,
    "BatchNorm2d": 1, "BatchNorm1d": 1, "LayerNorm": 1, "GroupNorm": 1, "InstanceNorm2d": 1,
    "ReLU": 1, "ReLU6": 1, "LeakyReLU": 1, "GELU": 1, "Swish": 1, "Sigmoid": 1, "Tanh": 1, "Softmax": 1,
    "MaxPool2d": 1, "AvgPool2d": 1, "AdaptiveAvgPool2d": 1, "AdaptiveMaxPool2d": 1,
    "Linear": 2, "Embedding": 2,
    "LSTM": 4, "GRU": 4, "RNN": 3,
    "MultiHeadAttention": 4, "TransformerEncoderLayer": 5,
    "Dropout": 1, "Add": 1, "Concat": 1, "Reshape": 1, "Flatten": 1,
    "Upsample": 1, "DepthwiseConv2d": 2, "MatMul": 3,
}


def _get_all_cases_with_structure():
    """获取所有测试用例及其模型结构"""
    conn = pymysql.connect(**MYSQL_CONFIG)
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute("""
            SELECT case_uid, status, edge_coverage, execution_time, 
                   error_message, parameters
            FROM test_case_metadata
        """)
        rows = cursor.fetchall()
        results = []
        for row in rows:
            params = json.loads(row["parameters"]) if row["parameters"] else {}
            structure = params.get("model_structure", {})
            row["operators"] = structure.get("operators", [])
            row["layers"] = structure.get("layers", [])
            row["connections"] = structure.get("connections", "")
            row["depth"] = structure.get("depth", 0)
            results.append(row)
        return results
    finally:
        conn.close()


@app.get("/api/analysis/coverage-gaps")
async def get_coverage_gaps():
    """
    覆盖率缺口分析 - 识别哪些算子/算子对尚未被测试覆盖
    返回：已覆盖的算子对、未覆盖的算子对、热力图矩阵数据
    """
    try:
        cases = _get_all_cases_with_structure()
        
        # 1. 收集所有出现的算子
        all_seen_operators = set()
        operator_pair_counts = {}  # (op_a, op_b) -> count
        
        for case in cases:
            ops = case["operators"]
            all_seen_operators.update(ops)
            
            # 统计相邻算子对（从 connections 提取）
            conn_str = case["connections"]
            if conn_str:
                parts = [p.strip() for p in conn_str.replace("->", "→").replace("→", "|").split("|")]
                for i in range(len(parts) - 1):
                    pair = (parts[i], parts[i+1])
                    operator_pair_counts[pair] = operator_pair_counts.get(pair, 0) + 1
        
        # 2. 构建热力图：用已见过和已知的算子集合
        heatmap_ops = sorted(all_seen_operators | set(KNOWN_OPERATORS[:20]))  # 限制大小
        
        heatmap_data = []
        covered_pairs = []
        uncovered_pairs = []
        
        for i, op_a in enumerate(heatmap_ops):
            for j, op_b in enumerate(heatmap_ops):
                count = operator_pair_counts.get((op_a, op_b), 0)
                heatmap_data.append([i, j, count])
                if count > 0:
                    covered_pairs.append({"from": op_a, "to": op_b, "count": count})
                elif op_a != op_b and op_a in all_seen_operators and op_b in all_seen_operators:
                    uncovered_pairs.append({"from": op_a, "to": op_b})
        
        # 3. 单算子覆盖情况
        operator_coverage = []
        for op in sorted(KNOWN_OPERATORS):
            case_count = sum(1 for c in cases if op in c["operators"])
            crash_count = sum(1 for c in cases if op in c["operators"] and c["status"] == "Crash")
            operator_coverage.append({
                "operator": op,
                "total_cases": case_count,
                "crash_cases": crash_count,
                "covered": case_count > 0
            })
        
        total_known = len(KNOWN_OPERATORS)
        covered_count = sum(1 for oc in operator_coverage if oc["covered"])
        
        return {
            "heatmap_operators": heatmap_ops,
            "heatmap_data": heatmap_data,
            "covered_pairs": covered_pairs[:50],
            "uncovered_pairs": uncovered_pairs[:50],
            "operator_coverage": operator_coverage,
            "summary": {
                "total_known_operators": total_known,
                "covered_operators": covered_count,
                "coverage_rate": round(covered_count / total_known * 100, 1) if total_known else 0,
                "total_pairs_tested": len(covered_pairs),
                "total_pairs_untested": len(uncovered_pairs)
            }
        }
    except Exception as e:
        logger.error(f"覆盖率缺口分析失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 测试效能指标 (CEI) ====================

@app.get("/api/analysis/efficiency")
async def get_efficiency_analysis():
    """
    测试效能分析 - 计算每个用例的 CEI (Coverage Efficiency Index)
    CEI = edge_coverage / complexity
    complexity = Σ(operator_weight × count)
    """
    try:
        cases = _get_all_cases_with_structure()
        
        efficiency_data = []
        for case in cases:
            ops = case["operators"]
            # 计算复杂度
            complexity = sum(OPERATOR_WEIGHTS.get(op, 2) for op in ops)
            complexity = max(complexity, 1)  # 避免除零
            
            # 计算 CEI
            cei = round(case["edge_coverage"] / complexity, 2)
            
            efficiency_data.append({
                "case_uid": case["case_uid"],
                "status": case["status"],
                "edge_coverage": case["edge_coverage"],
                "execution_time": case["execution_time"],
                "complexity": complexity,
                "cei": cei,
                "operators": ops,
                "operator_count": len(ops)
            })
        
        # 排序：CEI 从高到低
        efficiency_data.sort(key=lambda x: x["cei"], reverse=True)
        
        # 统计摘要
        if efficiency_data:
            cei_values = [d["cei"] for d in efficiency_data]
            avg_cei = round(sum(cei_values) / len(cei_values), 2)
            max_cei = max(cei_values)
            min_cei = min(cei_values)
        else:
            avg_cei = max_cei = min_cei = 0
        
        return {
            "cases": efficiency_data,
            "summary": {
                "total_cases": len(efficiency_data),
                "avg_cei": avg_cei,
                "max_cei": max_cei,
                "min_cei": min_cei,
                "top_efficient": efficiency_data[:5] if efficiency_data else [],
                "least_efficient": efficiency_data[-5:] if efficiency_data else []
            }
        }
    except Exception as e:
        logger.error(f"效能分析失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 错误模式聚类 ====================

@app.get("/api/analysis/error-patterns")
async def get_error_patterns():
    """
    错误模式分析 - 将错误按算子类型和错误类型交叉分析
    发现 "哪些算子组合容易触发哪类错误"
    """
    try:
        cases = _get_all_cases_with_structure()
        
        # 错误分类规则
        def classify_error(msg):
            if not msg:
                return "No Error"
            msg_lower = msg.lower()
            if "cuda" in msg_lower or "gpu" in msg_lower or "out of memory" in msg_lower:
                return "CUDA/Memory Error"
            if "size mismatch" in msg_lower or "shape" in msg_lower or "dimension" in msg_lower:
                return "Shape Mismatch"
            if "segmentation" in msg_lower or "core dumped" in msg_lower:
                return "Segmentation Fault"
            if "timeout" in msg_lower:
                return "Timeout"
            if "index" in msg_lower or "bounds" in msg_lower:
                return "Index Error"
            if "device" in msg_lower:
                return "Device Mismatch"
            return "Other Error"
        
        # 构建 算子 × 错误类型 矩阵
        error_types = set()
        operator_error_matrix = {}  # op -> {error_type -> count}
        patterns = []  # 具体模式列表
        
        for case in cases:
            if case["status"] == "Success":
                continue
            error_type = classify_error(case["error_message"])
            error_types.add(error_type)
            
            for op in case["operators"]:
                if op not in operator_error_matrix:
                    operator_error_matrix[op] = {}
                operator_error_matrix[op][error_type] = operator_error_matrix[op].get(error_type, 0) + 1
        
        # 发现高风险模式
        for op, errors in operator_error_matrix.items():
            for etype, count in errors.items():
                if count >= 1:
                    total_cases_with_op = sum(1 for c in cases if op in c["operators"])
                    fail_rate = round(count / total_cases_with_op * 100, 1) if total_cases_with_op else 0
                    patterns.append({
                        "operator": op,
                        "error_type": etype,
                        "count": count,
                        "total_cases": total_cases_with_op,
                        "fail_rate": fail_rate,
                        "risk_level": "high" if fail_rate > 50 else ("medium" if fail_rate > 25 else "low")
                    })
        
        patterns.sort(key=lambda x: x["fail_rate"], reverse=True)
        
        return {
            "patterns": patterns,
            "error_types": sorted(error_types),
            "operator_error_matrix": operator_error_matrix,
            "summary": {
                "total_error_cases": sum(1 for c in cases if c["status"] != "Success"),
                "unique_error_types": len(error_types),
                "high_risk_patterns": len([p for p in patterns if p["risk_level"] == "high"]),
                "top_patterns": patterns[:5]
            }
        }
    except Exception as e:
        logger.error(f"错误模式分析失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== AI 变异建议 ====================

SUGGEST_SYSTEM_PROMPT = """你是一个深度学习框架测试专家。你的任务是根据历史测试数据中的错误模式，为测试人员提供测试用例的变异建议。

请遵循以下原则:
1. 基于已知的错误模式和覆盖缺口，给出具体的测试用例变异方向
2. 每条建议应包含：目标算子、变异策略、预期效果
3. 建议应具有可操作性，能直接指导测试用例生成
4. 解释为什么这样变异可能发现新的 bug
5. 使用中文回答，保持简洁专业"""


@app.post("/api/suggest")
async def suggest_mutations(query: str = Body(..., embed=True)):
    """
    AI 变异建议 - 基于历史数据分析生成测试用例优化建议
    
    与"直接用 AI 生成测试"的区别：
    - 基于历史数据的错误模式分析，建议有据可查
    - 可解释、可追溯
    - 知识积累：越多数据，建议越准
    """
    try:
        cases = _get_all_cases_with_structure()
        
        # 收集统计数据
        total_cases = len(cases)
        crash_cases = [c for c in cases if c["status"] == "Crash"]
        
        # 算子出现频率
        op_freq = {}
        op_crash_freq = {}
        for case in cases:
            for op in case["operators"]:
                op_freq[op] = op_freq.get(op, 0) + 1
            if case["status"] == "Crash":
                for op in case["operators"]:
                    op_crash_freq[op] = op_crash_freq.get(op, 0) + 1
        
        # 深层关联分析（用结构化解析替代原始文本）
        correlation_patterns = []
        for c in crash_cases:
            parsed = parse_error_message(c.get("error_message", ""))
            fault = localize_fault(
                {"operators": c["operators"], "connections": c["connections"]},
                parsed
            )
            if fault["suspect_operators"]:
                top_suspect = fault["suspect_operators"][0]
                correlation_patterns.append({
                    "case_uid": c["case_uid"],
                    "error_category": parsed["error_category"],
                    "suspect": top_suspect["operator"],
                    "confidence": top_suspect["confidence"],
                    "reason": top_suspect["reason"]
                })

        # 构建上下文（增强版：含结构化关联分析）
        context = f"""历史测试数据摘要:
- 总测试用例: {total_cases}
- 崩溃用例: {len(crash_cases)} ({round(len(crash_cases)/total_cases*100,1) if total_cases else 0}%)

算子出现频率 (所有用例):
{json.dumps(op_freq, indent=2, ensure_ascii=False)}

算子崩溃频率 (仅崩溃用例):
{json.dumps(op_crash_freq, indent=2, ensure_ascii=False)}

结构化故障定位分析（关键发现）:
"""
        for p in correlation_patterns[:8]:
            context += f"\n- {p['case_uid']}: 嫌疑算子={p['suspect']}(置信度{p['confidence']:.0%}), 错误类型={p['error_category']}, 原因={p['reason']}"
        
        prompt = f"""用户查询: {query}

{context}

请基于以上历史数据，给出 3-5 条具体的测试用例变异建议。每条建议格式:
1. **目标**: 要测试什么
2. **变异方向**: 如何变异现有用例
3. **依据**: 为什么这样建议（关联历史数据）
4. **预期收益**: 可能发现什么类型的 bug"""

        answer = call_deepseek(prompt, SUGGEST_SYSTEM_PROMPT)
        
        return {
            "query": query,
            "suggestions": answer,
            "data_summary": {
                "total_cases": total_cases,
                "crash_rate": round(len(crash_cases)/total_cases*100, 1) if total_cases else 0,
                "operators_tested": len(op_freq),
                "high_risk_operators": sorted(
                    op_crash_freq.items(), key=lambda x: x[1], reverse=True
                )[:5]
            }
        }
    except Exception as e:
        logger.error(f"AI 建议生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 单用例联合分析 ====================

@app.post("/api/analyze-case")
async def analyze_case(case_uid: str = Body(..., embed=True)):
    """
    对单个测试用例做 结构(DAG) + 日志(Error) 的联合分析
    返回：结构化错误解析 + 故障定位结果
    """
    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        try:
            cursor.execute(
                "SELECT case_uid, status, edge_coverage, execution_time, error_message, parameters FROM test_case_metadata WHERE case_uid = %s",
                (case_uid,)
            )
            row = cursor.fetchone()
        finally:
            conn.close()

        if not row:
            raise HTTPException(status_code=404, detail=f"Case {case_uid} not found")

        params = json.loads(row["parameters"]) if row["parameters"] else {}
        structure = params.get("model_structure", {})
        error_msg = row.get("error_message", "")

        # Phase 1: 结构化日志解析
        parsed_error = parse_error_message(error_msg)

        # Phase 2: 故障定位
        fault_result = localize_fault(structure, parsed_error)

        return {
            "case_uid": case_uid,
            "status": row["status"],
            "edge_coverage": row["edge_coverage"],
            "model_structure": structure,
            "parsed_error": parsed_error,
            "fault_localization": fault_result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用例分析失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 深层关联分析 ====================

@app.get("/api/analysis/correlations")
async def get_correlations():
    """
    算子-错误深层关联分析
    不是简单统计"Conv2d出现在几个Crash中"，而是分析因果关系：
    - 算子对 × 错误类型
    - 哪些相邻算子组合最危险
    """
    try:
        cases = _get_all_cases_with_structure()
        
        # 对每个错误用例做结构化解析 + 故障定位
        pair_error_stats = {}   # (op_a, op_b) -> {error_category -> count}
        op_fault_stats = {}     # operator -> {error_category -> {count, confidence_sum}}
        detailed_cases = []     # 带定位结果的详细用例
        
        for case in cases:
            if case["status"] == "Success":
                continue
            
            parsed = parse_error_message(case.get("error_message", ""))
            fault = localize_fault(
                {"operators": case["operators"], "connections": case["connections"]},
                parsed
            )
            
            category = parsed["error_category"]
            
            # 算子对关联
            conn_str = case.get("connections", "")
            if conn_str:
                parts = [p.strip() for p in conn_str.replace("->", "→").replace("→", "|").split("|")]
                for i in range(len(parts) - 1):
                    pair = f"{parts[i]}→{parts[i+1]}"
                    if pair not in pair_error_stats:
                        pair_error_stats[pair] = {}
                    pair_error_stats[pair][category] = pair_error_stats[pair].get(category, 0) + 1
            
            # 算子故障关联
            for suspect in fault.get("suspect_operators", []):
                op = suspect["operator"]
                if op not in op_fault_stats:
                    op_fault_stats[op] = {}
                if category not in op_fault_stats[op]:
                    op_fault_stats[op][category] = {"count": 0, "total_confidence": 0}
                op_fault_stats[op][category]["count"] += 1
                op_fault_stats[op][category]["total_confidence"] += suspect["confidence"]
            
            # 记录详细信息
            detailed_cases.append({
                "case_uid": case["case_uid"],
                "error_category": category,
                "error_description": parsed["error_description"],
                "suspect_operators": fault.get("suspect_operators", [])[:3],
                "suggestion": fault.get("suggestion", "")
            })
        
        # 构建高危算子对排行
        dangerous_pairs = []
        for pair, errors in pair_error_stats.items():
            total = sum(errors.values())
            dominant_error = max(errors, key=errors.get)
            dangerous_pairs.append({
                "pair": pair,
                "total_errors": total,
                "dominant_error": dominant_error,
                "error_breakdown": errors
            })
        dangerous_pairs.sort(key=lambda x: x["total_errors"], reverse=True)
        
        # 构建算子故障概况
        operator_fault_summary = []
        for op, categories in op_fault_stats.items():
            total = sum(c["count"] for c in categories.values())
            avg_conf = sum(c["total_confidence"] for c in categories.values()) / total if total else 0
            operator_fault_summary.append({
                "operator": op,
                "total_faults": total,
                "avg_confidence": round(avg_conf, 2),
                "error_categories": {k: v["count"] for k, v in categories.items()}
            })
        operator_fault_summary.sort(key=lambda x: x["total_faults"], reverse=True)
        
        return {
            "dangerous_pairs": dangerous_pairs[:20],
            "operator_fault_summary": operator_fault_summary,
            "detailed_cases": detailed_cases,
            "summary": {
                "total_error_cases": len(detailed_cases),
                "unique_dangerous_pairs": len(dangerous_pairs),
                "top_suspect_operator": operator_fault_summary[0]["operator"] if operator_fault_summary else None
            }
        }
    except Exception as e:
        logger.error(f"关联分析失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 覆盖盲区自动补盲（闭环） ====================

COVERAGE_PROMPT = """你是一个深度学习框架模糊测试专家。根据以下未被覆盖的算子对组合，生成针对性的 PyTorch 测试用例代码片段。

要求：
1. 每个测试用例应包含指定的算子对组合，通过 nn.Sequential 或自定义 nn.Module 串联
2. 给出合理的输入张量维度
3. 代码应能直接在 PyTorch 中运行
4. 重点关注那些可能导致维度冲突、显存溢出或设备不一致的边界情况
5. 使用中文注释说明每个用例的测试目标
6. 每个用例输出完整可运行的 Python 代码块"""


@app.post("/api/auto-generate-from-gaps")
async def auto_generate_from_gaps(max_pairs: int = Body(default=5, embed=True)):
    """
    覆盖盲区自动补盲闭环：
    1. 从 coverage-gaps 接口提取 uncovered_pairs
    2. 构建定向 Prompt
    3. 调用 DeepSeek 生成补盲测试代码
    4. 返回生成的测试用例建议
    """
    try:
        # 1. 获取覆盖盲区数据
        cases = _get_all_cases_with_structure()

        all_seen_operators = set()
        operator_pair_counts = {}

        for case in cases:
            ops = case["operators"]
            all_seen_operators.update(ops)
            conn_str = case["connections"]
            if conn_str:
                parts = [p.strip() for p in conn_str.replace("->", "→").replace("→", "|").split("|")]
                for i in range(len(parts) - 1):
                    pair = (parts[i], parts[i + 1])
                    operator_pair_counts[pair] = operator_pair_counts.get(pair, 0) + 1

        # 提取未覆盖算子对
        uncovered = []
        for op_a in all_seen_operators:
            for op_b in all_seen_operators:
                if op_a != op_b and (op_a, op_b) not in operator_pair_counts:
                    uncovered.append({"from": op_a, "to": op_b})

        if not uncovered:
            return {
                "status": "complete",
                "message": "当前所有已知算子对组合均已覆盖，无需补盲",
                "generated_cases": [],
                "uncovered_pairs_used": []
            }

        # 2. 选取优先级最高的未覆盖对（优先选择含高复杂度算子的组合）
        def pair_priority(pair):
            w1 = OPERATOR_WEIGHTS.get(pair["from"], 1)
            w2 = OPERATOR_WEIGHTS.get(pair["to"], 1)
            return w1 + w2

        uncovered.sort(key=pair_priority, reverse=True)
        selected_pairs = uncovered[:max_pairs]

        # 3. 构建 Prompt
        pairs_desc = "\n".join(
            f"  {i + 1}. {p['from']} → {p['to']}"
            for i, p in enumerate(selected_pairs)
        )

        prompt = f"""当前模糊测试系统中，以下 {len(selected_pairs)} 组算子连接组合尚未被任何测试用例覆盖：

{pairs_desc}

已有测试用例总数: {len(cases)}
已覆盖的算子对组合数: {len(operator_pair_counts)}

请为以上每一组未覆盖的算子对，各生成 1 个针对性的 PyTorch 测试用例代码。"""

        # 4. 调用 LLM
        answer = call_deepseek(prompt, COVERAGE_PROMPT)

        return {
            "status": "generated",
            "message": f"已基于 {len(selected_pairs)} 组未覆盖算子对生成定向测试建议",
            "generated_cases": answer,
            "uncovered_pairs_used": selected_pairs,
            "total_uncovered": len(uncovered),
            "data_summary": {
                "total_cases": len(cases),
                "covered_pairs": len(operator_pair_counts),
                "operators_seen": len(all_seen_operators)
            }
        }
    except Exception as e:
        logger.error(f"自动补盲生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CEI 自动筛选与清退 ====================

@app.post("/api/analysis/efficiency/prune")
async def prune_low_efficiency_cases(
    cei_threshold: float = Body(default=0, embed=False),
    dry_run: bool = Body(default=True, embed=False)
):
    """
    CEI 自动清退机制：
    - 根据 CEI 阈值自动识别低效能用例
    - dry_run=True 时仅预览（不实际删除）
    - dry_run=False 时执行实际清退

    参数：
      cei_threshold: CEI 低于此值的用例将被标记/清退。
                     传 0 时自动使用中位数的 50% 作为阈值。
      dry_run: 是否为预览模式（默认 True，安全模式）
    """
    try:
        cases = _get_all_cases_with_structure()

        # 计算每个用例的 CEI
        efficiency_data = []
        for case in cases:
            ops = case["operators"]
            complexity = sum(OPERATOR_WEIGHTS.get(op, 2) for op in ops)
            complexity = max(complexity, 1)
            cei = round(case["edge_coverage"] / complexity, 2)
            efficiency_data.append({
                "case_uid": case["case_uid"],
                "status": case["status"],
                "edge_coverage": case["edge_coverage"],
                "complexity": complexity,
                "cei": cei,
                "operator_count": len(ops)
            })

        if not efficiency_data:
            return {"message": "无测试用例数据", "pruned": [], "kept": []}

        # 自动计算阈值：取中位数的 50%
        cei_values = sorted([d["cei"] for d in efficiency_data])
        median_cei = cei_values[len(cei_values) // 2]
        if cei_threshold <= 0:
            cei_threshold = round(median_cei * 0.5, 2)

        # 分类
        to_prune = [d for d in efficiency_data if d["cei"] < cei_threshold]
        to_keep = [d for d in efficiency_data if d["cei"] >= cei_threshold]

        # 执行清退
        actually_deleted = 0
        if not dry_run and to_prune:
            conn = pymysql.connect(**MYSQL_CONFIG)
            cursor = conn.cursor()
            try:
                prune_uids = [d["case_uid"] for d in to_prune]
                placeholders = ",".join(["%s"] * len(prune_uids))
                cursor.execute(
                    f"DELETE FROM test_case_metadata WHERE case_uid IN ({placeholders})",
                    prune_uids
                )
                actually_deleted = cursor.rowcount
                conn.commit()
            finally:
                conn.close()

        return {
            "mode": "预览" if dry_run else "执行",
            "cei_threshold": cei_threshold,
            "auto_threshold_source": "中位数×50%" if cei_threshold == round(median_cei * 0.5, 2) else "用户指定",
            "median_cei": median_cei,
            "summary": {
                "total_cases": len(efficiency_data),
                "to_prune": len(to_prune),
                "to_keep": len(to_keep),
                "prune_rate": f"{round(len(to_prune) / len(efficiency_data) * 100, 1)}%",
                "actually_deleted": actually_deleted
            },
            "pruned_cases": sorted(to_prune, key=lambda x: x["cei"])[:20],
            "kept_sample": sorted(to_keep, key=lambda x: x["cei"], reverse=True)[:10],
            "efficiency_improvement": {
                "avg_cei_before": round(sum(d["cei"] for d in efficiency_data) / len(efficiency_data), 2),
                "avg_cei_after": round(sum(d["cei"] for d in to_keep) / len(to_keep), 2) if to_keep else 0,
                "coverage_retained": f"{round(sum(d['edge_coverage'] for d in to_keep) / max(sum(d['edge_coverage'] for d in efficiency_data), 1) * 100, 1)}%"
            }
        }
    except Exception as e:
        logger.error(f"CEI 清退失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 差分调试与故障边界分析 ====================

class FaultBoundaryRequest(BaseModel):
    failed_case_uid: str

@app.post("/api/analysis/fault-boundary")
async def analyze_fault_boundary(request: FaultBoundaryRequest):
    """
    基于对比实验的故障边界分析
    找出距离最近的成功用例，进行张量 Diff，并用大模型倒推边界规则。
    """
    try:
        # 1. 从 MySQL 获取失败用例详情
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        cursor.execute("SELECT * FROM test_case_metadata WHERE case_uid = %s", (request.failed_case_uid,))
        failed_case = cursor.fetchone()
        
        if not failed_case:
            conn.close()
            raise HTTPException(status_code=404, detail="未找到目标失败用例")
            
        vector_id = failed_case.get('vector_id')
        if not vector_id:
            conn.close()
            raise HTTPException(status_code=400, detail="目标用例没有特征向量，无法进行对比实验")
            
        failed_params = json.loads(failed_case.get('parameters', '{}'))
        failed_status = failed_case.get('status', '').upper()
        failed_error = failed_case.get('error_message')
        
        if failed_status in ('SUCCESS', 'PASSED'):
            conn.close()
            raise HTTPException(status_code=400, detail="目标用例为成功状态，请选择一个崩溃用例")

        # 2. 从 Milvus 获取该用例的结构特征向量
        col = Collection(COLLECTION_STRUCTURE)
        res = col.query(expr=f"id == {vector_id}", output_fields=["embedding"])
        if not res:
            conn.close()
            raise HTTPException(status_code=500, detail="Milvus 库中未找到对应的特征向量")
            
        target_embedding = res[0]['embedding']
        
        # 3. 在 Milvus 中召回距离最近的对照样本 (Top 20)
        search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
        search_res = col.search(
            data=[target_embedding],
            anns_field="embedding",
            param=search_params,
            limit=20,
            output_fields=["id"]
        )
        
        nearest_ids = []
        if search_res and len(search_res) > 0:
            for hit in search_res[0]:
                if hit.id != vector_id: # 排除自身
                    nearest_ids.append(hit.id)
                    
        if not nearest_ids:
            conn.close()
            raise HTTPException(status_code=404, detail="未能找到相似的对照用例")

        # 4. 在 MySQL 中分别捞出同拓扑下的成功组和崩溃组
        query_ids = [vector_id] + nearest_ids
        placeholders = ",".join(["%s"] * len(query_ids))
        args = tuple(query_ids) + tuple(query_ids)
        
        # 捞取成功组（向量邻居）
        query_success = f"""
            SELECT * FROM test_case_metadata 
            WHERE vector_id IN ({placeholders}) 
            AND UPPER(status) IN ('SUCCESS', 'PASSED')
            ORDER BY FIELD(vector_id, {placeholders})
            LIMIT 10
        """
        cursor.execute(query_success, args)
        successful_cases = cursor.fetchall()
        
        # 捞取崩溃组（向量邻居）
        query_failed = f"""
            SELECT * FROM test_case_metadata 
            WHERE vector_id IN ({placeholders}) 
            AND UPPER(status) IN ('FAILED', 'ERROR', 'CRASH', 'TIMEOUT')
            ORDER BY FIELD(vector_id, {placeholders})
            LIMIT 10
        """
        cursor.execute(query_failed, args)
        failed_cases = cursor.fetchall()
        
        # 4.5 补充召回：按相同 demo_group 精确匹配（确保 Daikon 演示用例能找到同组对照）
        demo_group = failed_params.get("demo_group")
        if demo_group:
            cursor.execute("""
                SELECT * FROM test_case_metadata
                WHERE parameters LIKE %s AND UPPER(status) IN ('SUCCESS', 'PASSED')
                LIMIT 20
            """, (f'%"demo_group": "{demo_group}"%',))
            group_success = cursor.fetchall()
            if group_success:
                existing_uids = {c['case_uid'] for c in successful_cases}
                for c in group_success:
                    if c['case_uid'] not in existing_uids:
                        successful_cases.append(c)
            
            cursor.execute("""
                SELECT * FROM test_case_metadata
                WHERE parameters LIKE %s AND UPPER(status) IN ('FAILED', 'ERROR', 'CRASH', 'TIMEOUT')
                LIMIT 20
            """, (f'%"demo_group": "{demo_group}"%',))
            group_failed = cursor.fetchall()
            if group_failed:
                existing_uids = {c['case_uid'] for c in failed_cases}
                for c in group_failed:
                    if c['case_uid'] not in existing_uids:
                        failed_cases.append(c)
        
        conn.close()
        
        if not successful_cases:
            raise HTTPException(status_code=404, detail="未能在相似结构中找到执行成功的对照组用例")
            
        successful_params_list = [json.loads(c.get('parameters', '{}')) for c in successful_cases]
        failed_params_list = [json.loads(c.get('parameters', '{}')) for c in failed_cases]
        
        if not failed_params_list:
            failed_params_list = [failed_params]
        
        # 挑选最接近的一个用于 Diff 对比呈现（优先同组用例）
        if demo_group and successful_cases:
            group_successes = [c for c in successful_cases if demo_group in (c.get('parameters') or '')]
            if group_successes:
                successful_case = group_successes[0]
                successful_params = json.loads(group_successes[0].get('parameters', '{}'))
            else:
                successful_case = successful_cases[0]
                successful_params = successful_params_list[0]
        else:
            successful_case = successful_cases[0]
            successful_params = successful_params_list[0]
        
        # 5. 计算张量参数 Diff
        diff_result = analyze_boundary_diff(failed_params, successful_params)
        
        # 6. 使用 Daikon 算法推断被打破的数学不变量 (严格分离成功空间与失败空间)
        # 当有 demo_group 时，仅用同组数据做 Daikon（避免异构参数集污染 common_keys）
        daikon_success_params = successful_params_list
        daikon_failed_params = failed_params_list
        if demo_group:
            daikon_success_params = [json.loads(c.get('parameters', '{}')) for c in successful_cases if demo_group in (c.get('parameters') or '')]
            daikon_failed_params = [json.loads(c.get('parameters', '{}')) for c in failed_cases if demo_group in (c.get('parameters') or '')]
            if not daikon_failed_params:
                daikon_failed_params = [failed_params]
        daikon_violations = infer_daikon_invariants(daikon_failed_params, daikon_success_params)
        
        # 7. 利用 DeepSeek 提取边界规则
        daikon_context = ""
        if daikon_violations:
            daikon_context = f"\n【算法推断的数学越界规律 (Daikon Invariants)】\n系统已通过底层算法测算发现，崩溃用例恰好打破了以下原本在所有成功用例中都绝对成立的数学约束：\n{json.dumps(daikon_violations, ensure_ascii=False)}\n请你务必在回答中采纳并解释这一算法发现的公式关系。\n"

        prompt = f"""
你是一个深度学习框架（如 PyTorch）的底层排障专家。我们需要找出导致算子崩溃的“故障安全边界 (Fault Boundary)”。

【背景信息】
这是由差分调试（Delta Debugging）找到的对照参数。它们具有几乎一样的算子拓扑，但一组成功执行，另一组发生了严重的底层崩溃。

【失败用例的报错日志】
{failed_error}

【控制变量的 Diff 差异 (最近邻比对)】
成功的参数值为: {json.dumps(diff_result['successful_values'], ensure_ascii=False)}
失败的参数值为: {json.dumps(diff_result['failed_values'], ensure_ascii=False)}
{daikon_context}
【任务】
请你根据上述报错、发生变动的关键张量参数，以及 Daikon 算法推断出的数学越界规律，直接输出一句严谨的“故障边界规则”（即导致此算子不再能正常运行的参数红线或数学关系限制）。
请直接输出规则本身，无需解释过多废话。如果存在明确的数学公式，请直接写出公式限制。例如：“当包含 Conv2d 且无 Padding 过渡时，空间维度需满足 Input_size >= kernel_size，否则导致计算崩溃。”
"""
        boundary_rule = call_deepseek(prompt, system_prompt="你是一个深度学习框架底层的张量分析专家，说话精简严谨，擅长用一句话总结控制变量间的数学约束公式。")
        
        return {
            "failed_case": {
                "uid": failed_case['case_uid'],
                "error": failed_error
            },
            "successful_case": {
                "uid": successful_case['case_uid']
            },
            "diff": diff_result,
            "daikon_violations": daikon_violations,
            "boundary_rule": boundary_rule
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"故障边界分析失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 启动入口 ====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
