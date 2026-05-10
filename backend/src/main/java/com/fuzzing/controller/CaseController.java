package com.fuzzing.controller;

import com.fuzzing.entity.TestCaseMetadata;
import com.fuzzing.service.TestCaseService;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/cases")
@RequiredArgsConstructor
public class CaseController {

    private final TestCaseService service;

    /**
     * 分页获取测试用例列表
     * GET /api/cases?page=0&size=10&status=Crash
     */
    @GetMapping
    public ResponseEntity<Page<TestCaseMetadata>> getCases(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String status) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "id"));

        Page<TestCaseMetadata> result;
        if (status != null && !status.isEmpty()) {
            result = service.findByStatus(status, pageable);
        } else {
            result = service.findAll(pageable);
        }

        return ResponseEntity.ok(result);
    }

    /**
     * 获取最近的测试用例（用于 Dashboard）
     * GET /api/cases/recent
     */
    @GetMapping("/recent")
    public ResponseEntity<List<TestCaseMetadata>> getRecentCases() {
        return ResponseEntity.ok(service.findRecent());
    }

    /**
     * 根据 ID 获取单个测试用例
     * GET /api/cases/{id}
     */
    @GetMapping("/{id}")
    public ResponseEntity<TestCaseMetadata> getCaseById(@PathVariable Long id) {
        return service.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    /**
     * 根据 case_uid 获取测试用例
     * GET /api/cases/uid/{caseUid}
     */
    @GetMapping("/uid/{caseUid}")
    public ResponseEntity<TestCaseMetadata> getCaseByCaseUid(@PathVariable String caseUid) {
        return service.findByCaseUid(caseUid)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }
}
