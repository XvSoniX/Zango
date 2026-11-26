package ir.nextminds.admin.audit.service;

import ir.nextminds.admin.audit.domain.AdminAuditLog;
import ir.nextminds.admin.audit.domain.AuditAction;
import ir.nextminds.admin.audit.domain.AuditTargetType;

import java.util.Map;
import java.util.Optional;
import java.util.UUID;

public interface AuditLogService {

    AdminAuditLog recordAttempt(
            UUID administratorId,
            AuditAction action,
            AuditTargetType targetType,
            UUID targetId,
            String reason,
            String sourceIp,
            UUID correlationId
    );

    AdminAuditLog finalizeSuccess(UUID auditLogId, UUID createdTargetId, Map<String, Object> metadata);

    AdminAuditLog finalizeFailure(UUID auditLogId, UUID createdTargetId, Map<String, Object> metadata);

    Optional<AdminAuditLog> findById(UUID auditLogId);
}
