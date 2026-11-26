package ir.nextminds.admin.audit.dto;

import ir.nextminds.admin.audit.domain.AdminAuditLog;
import ir.nextminds.admin.audit.domain.AuditAction;
import ir.nextminds.admin.audit.domain.AuditResult;
import ir.nextminds.admin.audit.domain.AuditTargetType;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

public record AuditLogResponse(
        UUID id,
        UUID administratorId,
        AuditAction action,
        AuditTargetType targetType,
        UUID targetId,
        String reason,
        AuditResult result,
        String sourceIp,
        UUID correlationId,
        Map<String, Object> metadata,
        Instant createdAt,
        Instant completedAt
) {

    public static AuditLogResponse from(AdminAuditLog auditLog) {
        Map<String, Object> metadata = auditLog.getMetadata();
        return new AuditLogResponse(
                auditLog.getId(),
                auditLog.getAdministratorId(),
                auditLog.getAction(),
                auditLog.getTargetType(),
                auditLog.getTargetId(),
                auditLog.getReason(),
                auditLog.getResult(),
                auditLog.getSourceIp(),
                auditLog.getCorrelationId(),
                metadata == null ? null : new LinkedHashMap<>(metadata),
                auditLog.getCreatedAt(),
                auditLog.getCompletedAt()
        );
    }
}
