package com.fuzzing.controller;

import com.fuzzing.service.PythonServiceClient;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class SearchController {

    private final PythonServiceClient pythonClient;

    /**
     * 语义检索（代理到 Python 服务）
     * POST /api/search
     * Body: { "query": "..." }
     */
    @PostMapping("/search")
    public ResponseEntity<Map<String, Object>> search(@RequestBody Map<String, Object> request) {
        log.info("Proxying search request to Python service: {}", request);
        try {
            Map<String, Object> result = pythonClient.semanticSearch(request);
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            log.error("Python service call failed: {}", e.getMessage());
            return ResponseEntity.internalServerError()
                    .body(Map.of("error", "Python service unavailable: " + e.getMessage()));
        }
    }

    /**
     * RAG 问答（代理到 Python 服务）
     * POST /api/ask
     * Body: { "query": "..." }
     */
    @PostMapping("/ask")
    public ResponseEntity<Map<String, Object>> ask(@RequestBody Map<String, Object> request) {
        log.info("Proxying RAG request to Python service: {}", request);
        try {
            Map<String, Object> result = pythonClient.askRAG(request);
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            log.error("Python service call failed: {}", e.getMessage());
            return ResponseEntity.internalServerError()
                    .body(Map.of("error", "Python service unavailable: " + e.getMessage()));
        }
    }
}
