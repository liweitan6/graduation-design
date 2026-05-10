package com.fuzzing.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "test_case_metadata")
public class TestCaseMetadata {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "case_uid", unique = true, nullable = false, length = 64)
    private String caseUid;

    @Column(name = "status", nullable = false, length = 20)
    private String status;

    @Column(name = "edge_coverage", nullable = false)
    private Integer edgeCoverage;

    @Column(name = "execution_time", nullable = false)
    private Float executionTime;

    @Column(name = "error_message", columnDefinition = "TEXT")
    private String errorMessage;

    @Column(name = "vector_id")
    private Long vectorId;

    @Column(name = "parameters", columnDefinition = "JSON")
    private String parameters;

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }
}
