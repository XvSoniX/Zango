package ir.nextminds.admin.audit.query;

import ir.nextminds.admin.audit.domain.AuditAction;
import ir.nextminds.admin.audit.domain.AuditResult;
import ir.nextminds.admin.audit.domain.AuditTargetType;

import java.time.Instant;
import java.util.UUID;

public record AuditLogFilter(
        UUID administratorId,
        AuditAction action,
        AuditTargetType targetType,
        UUID targetId,
        AuditResult result,
        Instant from,
        Instant to,
        int page,
        int size
) {
}
