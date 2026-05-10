package com.fuzzing.service;

import com.fuzzing.entity.TestCaseMetadata;
import com.fuzzing.repository.TestCaseRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class TestCaseService {

    private final TestCaseRepository repository;

    public Page<TestCaseMetadata> findAll(Pageable pageable) {
        return repository.findAll(pageable);
    }

    public Page<TestCaseMetadata> findByStatus(String status, Pageable pageable) {
        return repository.findByStatus(status, pageable);
    }

    public Optional<TestCaseMetadata> findById(Long id) {
        return repository.findById(id);
    }

    public Optional<TestCaseMetadata> findByCaseUid(String caseUid) {
        return repository.findByCaseUid(caseUid);
    }

    public List<TestCaseMetadata> findRecent() {
        return repository.findTop10ByOrderByIdDesc();
    }

    public Map<String, Object> getOverviewStatistics() {
        return repository.getOverviewStatistics();
    }

    public List<Map<String, Object>> getStatusDistribution() {
        return repository.getStatusDistribution();
    }

    public List<Map<String, Object>> getErrorDistribution() {
        return repository.getErrorDistribution();
    }

    public long count() {
        return repository.count();
    }
}
