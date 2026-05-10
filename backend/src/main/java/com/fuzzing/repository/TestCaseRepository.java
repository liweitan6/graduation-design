package com.fuzzing.repository;

import com.fuzzing.entity.TestCaseMetadata;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Map;
import java.util.Optional;

@Repository
public interface TestCaseRepository extends JpaRepository<TestCaseMetadata, Long> {

    Optional<TestCaseMetadata> findByCaseUid(String caseUid);

    Page<TestCaseMetadata> findByStatus(String status, Pageable pageable);

    // 统计总数、成功数、失败数
    @Query(value = """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'Success' THEN 1 ELSE 0 END) as successCount,
                SUM(CASE WHEN status != 'Success' THEN 1 ELSE 0 END) as failCount,
                ROUND(AVG(execution_time), 3) as avgTime,
                ROUND(AVG(edge_coverage), 0) as avgCoverage
            FROM test_case_metadata
            """, nativeQuery = true)
    Map<String, Object> getOverviewStatistics();

    // 状态分布
    @Query(value = """
            SELECT status, COUNT(*) as count
            FROM test_case_metadata
            GROUP BY status
            ORDER BY count DESC
            """, nativeQuery = true)
    List<Map<String, Object>> getStatusDistribution();

    // 错误类型分布
    @Query(value = """
            SELECT
                CASE
                    WHEN error_message LIKE '%CUDA%' OR error_message LIKE '%GPU%' THEN 'CUDA/GPU Error'
                    WHEN error_message LIKE '%memory%' OR error_message LIKE '%OOM%' THEN 'Memory Error'
                    WHEN error_message LIKE '%Segmentation%' THEN 'Segmentation Fault'
                    WHEN error_message LIKE '%Timeout%' THEN 'Timeout'
                    WHEN error_message LIKE '%shape%' OR error_message LIKE '%dimension%' THEN 'Shape Mismatch'
                    WHEN error_message IS NULL OR error_message = '' THEN 'No Error'
                    ELSE 'Other'
                END as errorType,
                COUNT(*) as count
            FROM test_case_metadata
            GROUP BY errorType
            ORDER BY count DESC
            """, nativeQuery = true)
    List<Map<String, Object>> getErrorDistribution();

    // 最近的测试用例
    List<TestCaseMetadata> findTop10ByOrderByIdDesc();
}
