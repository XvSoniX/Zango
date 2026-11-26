package ir.nextminds.admin.audit.service;

import ir.nextminds.admin.audit.AuditLogNotFoundException;
import ir.nextminds.admin.audit.domain.AdminAuditLog;
import ir.nextminds.admin.audit.domain.AuditAction;
import ir.nextminds.admin.audit.domain.AuditResult;
import ir.nextminds.admin.audit.domain.AuditTargetType;
import ir.nextminds.admin.audit.repository.AdminAuditLogRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.json.JsonMapper;

import java.time.Instant;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class AuditLogServiceImpl implements AuditLogService {

    static final int MAX_METADATA_BYTES = 4096;

    private final AdminAuditLogRepository auditLogRepository;
    private final JsonMapper jsonMapper;

    @Override
    @Transactional
    public AdminAuditLog recordAttempt(
            UUID administratorId,
            AuditAction action,
            AuditTargetType targetType,
            UUID targetId,
            String reason,
            String sourceIp,
            UUID correlationId
    ) {
        AdminAuditLog auditLog = AdminAuditLog.pending(
                administratorId,
                action,
                targetType,
                targetId,
                reason,
                sourceIp,
                correlationId,
                Instant.now()
        );
        return auditLogRepository.save(auditLog);
    }

    @Override
    @Transactional
    public AdminAuditLog finalizeSuccess(UUID auditLogId, UUID createdTargetId, Map<String, Object> metadata) {
        return finalize(auditLogId, AuditResult.SUCCESS, createdTargetId, metadata);
    }

    @Override
    @Transactional
    public AdminAuditLog finalizeFailure(UUID auditLogId, UUID createdTargetId, Map<String, Object> metadata) {
        return finalize(auditLogId, AuditResult.FAILURE, createdTargetId, metadata);
    }

    @Override
    @Transactional(readOnly = true)
    public Optional<AdminAuditLog> findById(UUID auditLogId) {
        return auditLogRepository.findById(auditLogId);
    }

    private AdminAuditLog finalize(
            UUID auditLogId,
            AuditResult outcome,
            UUID createdTargetId,
            Map<String, Object> metadata
    ) {
        requireMetadataSize(metadata);
        AdminAuditLog auditLog = auditLogRepository.findById(auditLogId)
                .orElseThrow(() -> new AuditLogNotFoundException(auditLogId));
        auditLog.complete(outcome, createdTargetId, metadata, Instant.now());
        return auditLog;
    }

    private void requireMetadataSize(Map<String, Object> metadata) {
        if (metadata == null || metadata.isEmpty()) {
            return;
        }
        try {
            byte[] encoded = jsonMapper.writeValueAsBytes(metadata);
            if (encoded.length > MAX_METADATA_BYTES) {
                throw new IllegalArgumentException("metadata exceeds 4 KiB");
            }
        } catch (JacksonException exception) {
            throw new IllegalArgumentException("metadata cannot be stored", exception);
        }
    }
}
