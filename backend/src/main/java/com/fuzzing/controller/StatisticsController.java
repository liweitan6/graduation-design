package com.fuzzing.controller;

import com.fuzzing.service.TestCaseService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/statistics")
@RequiredArgsConstructor
public class StatisticsController {

    private final TestCaseService service;

    /**
     * 总览统计
     * GET /api/statistics/overview
     * 返回: { total, successCount, failCount, avgTime, avgCoverage }
     */
    @GetMapping("/overview")
    public ResponseEntity<Map<String, Object>> getOverview() {
        return ResponseEntity.ok(service.getOverviewStatistics());
    }

    /**
     * 状态分布
     * GET /api/statistics/status
     * 返回: [{ status: "Success", count: 850 }, ...]
     */
    @GetMapping("/status")
    public ResponseEntity<List<Map<String, Object>>> getStatusDistribution() {
        return ResponseEntity.ok(service.getStatusDistribution());
    }

    /**
     * 错误类型分布
     * GET /api/statistics/errors
     * 返回: [{ errorType: "CUDA Error", count: 45 }, ...]
     */
    @GetMapping("/errors")
    public ResponseEntity<List<Map<String, Object>>> getErrorDistribution() {
        return ResponseEntity.ok(service.getErrorDistribution());
    }
}
