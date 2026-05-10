-- ============================================
-- 深度学习模糊测试管理系统 - 数据库初始化脚本
-- 创建时间: 2026-02-06
-- 数据库: fuzzing_db
-- 字符集: utf8mb4
-- ============================================

-- 确保使用正确的数据库
USE fuzzing_db;

-- ============================================
-- 表: test_case_metadata
-- 用途: 存储深度学习模糊测试用例的元数据信息
-- ============================================
CREATE TABLE IF NOT EXISTS `test_case_metadata` (
    -- ========== 主键 ==========
    `id` BIGINT NOT NULL AUTO_INCREMENT 
        COMMENT '主键ID，自增',

-- ========== 业务标识 ==========
`case_uid` VARCHAR(64) NOT NULL COMMENT '测试用例唯一标识（文件名哈希或UUID），用于关联原始文件',

-- ========== 执行状态 ==========
`status` VARCHAR(20) NOT NULL DEFAULT 'Pending' COMMENT '执行状态: Success(成功), Crash(崩溃), Timeout(超时), Pending(待执行)',

-- ========== 覆盖率指标 ==========
`edge_coverage` INT NOT NULL DEFAULT 0 COMMENT '累计覆盖边数（边覆盖率指标），用于评估测试用例质量',

-- ========== 性能指标 ==========
`execution_time` FLOAT NOT NULL DEFAULT 0.0 COMMENT '执行耗时（秒），用于性能分析和超时检测',

-- ========== 错误信息 ==========
`error_message` TEXT NULL COMMENT '错误信息摘要，存储崩溃或超时时的简短报错描述',

-- ========== 向量关联 ==========
`vector_id` BIGINT NULL COMMENT 'Milvus向量ID，用于关联语义向量（支持自然语言检索）',

-- ========== 扩展参数 ==========
`parameters` JSON NULL COMMENT '非结构化参数(JSON格式)，存储变异策略、输入维度、模型名称等扩展信息',

-- ========== 时间戳 ==========
`created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间，记录测试用例入库时间',
`updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间，自动记录最后修改时间',

-- ========== 约束定义 ==========
PRIMARY KEY (`id`),
    UNIQUE KEY `uk_case_uid` (`case_uid`) COMMENT '唯一索引：确保用例标识不重复'
    
) ENGINE=InnoDB 
  DEFAULT CHARSET=utf8mb4 
  COLLATE=utf8mb4_unicode_ci 
  COMMENT='测试用例元数据表 - 存储深度学习模糊测试用例的执行结果和关联信息';

-- ============================================
-- 索引优化
-- ============================================

-- 状态索引：用于 Dashboard 饼图统计（按状态分组聚合）
CREATE INDEX `idx_status` ON `test_case_metadata` (`status`) COMMENT '状态索引：优化按状态统计查询';

-- 覆盖率索引：用于 Top-K 高效能用例筛选（ORDER BY edge_coverage DESC LIMIT K）
CREATE INDEX `idx_coverage` ON `test_case_metadata` (`edge_coverage`) COMMENT '覆盖率索引：优化按覆盖率排序查询';

-- 时间索引：用于时间范围筛选（WHERE created_at BETWEEN ... AND ...）
CREATE INDEX `idx_time` ON `test_case_metadata` (`created_at`) COMMENT '时间索引：优化按时间范围查询';

-- ============================================
-- 初始化示例数据（可选，演示用）
-- ============================================
-- INSERT INTO `test_case_metadata`
--     (`case_uid`, `status`, `edge_coverage`, `execution_time`, `parameters`)
-- VALUES
--     ('demo-case-001', 'Success', 1520, 0.45, '{"mutation": "random", "model": "resnet50"}'),
--     ('demo-case-002', 'Crash', 890, 1.23, '{"mutation": "guided", "model": "vgg16"}'),
--     ('demo-case-003', 'Timeout', 450, 30.00, '{"mutation": "semantic", "model": "bert-base"}');

-- ============================================
-- 查询示例（供参考）
-- ============================================
--
-- 1. Dashboard 饼图统计（按状态分组）
--    SELECT status, COUNT(*) as count FROM test_case_metadata GROUP BY status;
--
-- 2. Top-K 高覆盖率用例
--    SELECT * FROM test_case_metadata ORDER BY edge_coverage DESC LIMIT 10;
--
-- 3. 时间范围查询
--    SELECT * FROM test_case_metadata
--    WHERE created_at BETWEEN '2026-01-01' AND '2026-02-01';
--
-- 4. JSON 参数查询（MySQL 8.0+）
--    SELECT * FROM test_case_metadata
--    WHERE JSON_EXTRACT(parameters, '$.model') = 'resnet50';