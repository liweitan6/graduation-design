package com.fuzzing.service;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;

import java.util.Map;

@FeignClient(name = "python-service", url = "${python-service.url}")
public interface PythonServiceClient {

    @PostMapping("/api/search")
    Map<String, Object> semanticSearch(@RequestBody Map<String, Object> request);

    @PostMapping("/api/ask")
    Map<String, Object> askRAG(@RequestBody Map<String, Object> request);
}
