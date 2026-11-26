package ir.nextminds.admin.audit.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.annotations.UuidGenerator;
import org.hibernate.type.SqlTypes;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@Entity
@Table(name = "admin_audit_logs")
public class AdminAuditLog {

    private static final int REASON_MAX_LENGTH = 500;
    private static final int SOURCE_IP_MAX_LENGTH = 45;

    @Id
    @GeneratedValue
    @UuidGenerator
    @Column(name = "id", nullable = false, updatable = false)
    private UUID id;

    @Column(name = "administrator_id", nullable = false, updatable = false)
    private UUID administratorId;

    @Enumerated(EnumType.STRING)
    @Column(name = "action", nullable = false, updatable = false, length = 64)
    private AuditAction action;

    @Enumerated(EnumType.STRING)
    @Column(name = "target_type", nullable = false, updatable = false, length = 32)
    private AuditTargetType targetType;

    @Column(name = "target_id")
    private UUID targetId;

    @Column(name = "reason", updatable = false, length = REASON_MAX_LENGTH)
    private String reason;

    @Enumerated(EnumType.STRING)
    @Column(name = "result", nullable = false, length = 16)
    private AuditResult result;

    @Column(name = "source_ip", updatable = false, length = SOURCE_IP_MAX_LENGTH)
    private String sourceIp;

    @Column(name = "correlation_id", updatable = false)
    private UUID correlationId;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "metadata", columnDefinition = "jsonb")
    private Map<String, Object> metadata;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @Column(name = "completed_at")
    private Instant completedAt;

    public static AdminAuditLog pending(
            UUID administratorId,
            AuditAction action,
            AuditTargetType targetType,
            UUID targetId,
            String reason,
            String sourceIp,
            UUID correlationId,
            Instant createdAt
    ) {
        if (administratorId == null) {
            throw new IllegalArgumentException("administratorId is required");
        }
        if (action == null) {
            throw new IllegalArgumentException("action is required");
        }
        if (targetType == null) {
            throw new IllegalArgumentException("targetType is required");
        }
        if (action.targetType() != targetType) {
            throw new IllegalArgumentException("targetType does not match action");
        }
        if (createdAt == null) {
            throw new IllegalArgumentException("createdAt is required");
        }
        if (targetId == null && action != AuditAction.ROLE_CREATED) {
            throw new IllegalArgumentException("targetId is required");
        }

        AdminAuditLog auditLog = new AdminAuditLog();
        auditLog.administratorId = administratorId;
        auditLog.action = action;
        auditLog.targetType = targetType;
        auditLog.targetId = targetId;
        auditLog.reason = normalizeReason(action, reason);
        auditLog.result = AuditResult.PENDING;
        auditLog.sourceIp = normalizeSourceIp(sourceIp);
        auditLog.correlationId = correlationId;
        auditLog.createdAt = createdAt;
        return auditLog;
    }

    /**
     * Moves a pending attempt to a terminal result. This is the only mutation the domain allows.
     */
    public void complete(AuditResult outcome, UUID createdTargetId, Map<String, Object> metadata, Instant completedAt) {
        if (result != AuditResult.PENDING) {
            throw new AuditFinalizationException("audit record is already finalized");
        }
        if (outcome != AuditResult.SUCCESS && outcome != AuditResult.FAILURE) {
            throw new AuditFinalizationException("audit result must be SUCCESS or FAILURE");
        }
        if (completedAt == null) {
            throw new AuditFinalizationException("completedAt is required");
        }
        if (this.metadata != null) {
            throw new AuditFinalizationException("audit metadata is already set");
        }
        if (this.completedAt != null) {
            throw new AuditFinalizationException("completedAt is already set");
        }

        UUID resolvedTargetId = resolveTargetId(outcome, createdTargetId);
        this.targetId = resolvedTargetId;
        this.metadata = copyMetadata(metadata);
        this.completedAt = completedAt;
        this.result = outcome;
    }

    private UUID resolveTargetId(AuditResult outcome, UUID createdTargetId) {
        if (action == AuditAction.ROLE_CREATED) {
            if (outcome == AuditResult.SUCCESS && createdTargetId == null) {
                throw new AuditFinalizationException("successful role creation requires the role id");
            }
            if (targetId == null) {
                return createdTargetId;
            }
            if (createdTargetId != null && !targetId.equals(createdTargetId)) {
                throw new AuditFinalizationException("targetId cannot change");
            }
            return targetId;
        }
        if (createdTargetId != null && !targetId.equals(createdTargetId)) {
            throw new AuditFinalizationException("targetId cannot change");
        }
        return targetId;
    }

    private static Map<String, Object> copyMetadata(Map<String, Object> metadata) {
        if (metadata == null || metadata.isEmpty()) {
            return null;
        }
        return new LinkedHashMap<>(metadata);
    }

    private static String normalizeReason(AuditAction action, String reason) {
        String normalized = reason == null ? null : reason.trim();
        if (normalized != null && normalized.isBlank()) {
            normalized = null;
        }
        if (action.reasonRequired() && normalized == null) {
            throw new IllegalArgumentException("reason is required");
        }
        if (normalized != null && normalized.length() > REASON_MAX_LENGTH) {
            throw new IllegalArgumentException("reason is too long");
        }
        return normalized;
    }

    private static String normalizeSourceIp(String sourceIp) {
        if (sourceIp == null || sourceIp.isBlank()) {
            return null;
        }
        String normalized = sourceIp.trim();
        if (normalized.length() > SOURCE_IP_MAX_LENGTH) {
            throw new IllegalArgumentException("sourceIp is too long");
        }
        return normalized;
    }
}
