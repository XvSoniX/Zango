package ir.nextminds.admin.audit.domain;

import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

class AdminAuditLogTest {

    private final UUID administratorId = UUID.fromString("bb9e9a5c-54ac-4d4f-8799-ad02539ac1bf");
    private final Instant createdAt = Instant.parse("2026-11-24T12:00:00Z");

    @Test
    void roleCreationStartsPendingWithoutATarget() {
        AdminAuditLog auditLog = AdminAuditLog.pending(
                administratorId,
                AuditAction.ROLE_CREATED,
                AuditTargetType.ROLE,
                null,
                "  ",
                null,
                null,
                createdAt
        );

        assertEquals(AuditResult.PENDING, auditLog.getResult());
        assertNull(auditLog.getTargetId());
        assertNull(auditLog.getReason());
        assertNull(auditLog.getCompletedAt());
    }

    @Test
    void assignRequiresANonBlankReason() {
        assertThrows(IllegalArgumentException.class, () -> AdminAuditLog.pending(
                administratorId,
                AuditAction.ROLE_ASSIGNED,
                AuditTargetType.USER,
                UUID.randomUUID(),
                " \t\n ",
                null,
                null,
                createdAt
        ));
    }

    @Test
    void successfulRoleCreationStoresTheReturnedRoleId() {
        AdminAuditLog auditLog = pendingCreate();
        UUID roleId = UUID.randomUUID();

        auditLog.complete(
                AuditResult.SUCCESS,
                roleId,
                Map.of("downstreamOutcome", "CONFIRMED"),
                createdAt.plusSeconds(1)
        );

        assertEquals(AuditResult.SUCCESS, auditLog.getResult());
        assertEquals(roleId, auditLog.getTargetId());
        assertEquals(createdAt.plusSeconds(1), auditLog.getCompletedAt());
        assertEquals("CONFIRMED", auditLog.getMetadata().get("downstreamOutcome"));
    }

    @Test
    void successfulRoleCreationWithoutARoleIdIsRejected() {
        AdminAuditLog auditLog = pendingCreate();

        assertThrows(AuditFinalizationException.class, () -> auditLog.complete(
                AuditResult.SUCCESS,
                null,
                Map.of("downstreamOutcome", "UNKNOWN"),
                createdAt.plusSeconds(1)
        ));
        assertEquals(AuditResult.PENDING, auditLog.getResult());
        assertNull(auditLog.getTargetId());
    }

    @Test
    void failureCanRemainWithoutATargetAndCannotBeFinalizedTwice() {
        AdminAuditLog auditLog = pendingCreate();

        auditLog.complete(
                AuditResult.FAILURE,
                null,
                Map.of("downstreamOutcome", "UNKNOWN", "failureType", "TIMEOUT"),
                createdAt.plusSeconds(1)
        );

        assertEquals(AuditResult.FAILURE, auditLog.getResult());
        assertNull(auditLog.getTargetId());
        assertThrows(AuditFinalizationException.class, () -> auditLog.complete(
                AuditResult.SUCCESS,
                UUID.randomUUID(),
                Map.of("downstreamOutcome", "CONFIRMED"),
                createdAt.plusSeconds(2)
        ));
    }

    @Test
    void otherActionsRequireATargetAndDoNotReplaceIt() {
        UUID userId = UUID.randomUUID();
        AdminAuditLog auditLog = AdminAuditLog.pending(
                administratorId,
                AuditAction.ROLE_REVOKED,
                AuditTargetType.USER,
                userId,
                "Remove access",
                null,
                null,
                createdAt
        );

        assertThrows(AuditFinalizationException.class, () -> auditLog.complete(
                AuditResult.SUCCESS,
                UUID.randomUUID(),
                null,
                createdAt.plusSeconds(1)
        ));
        assertEquals(userId, auditLog.getTargetId());
        assertEquals(AuditResult.PENDING, auditLog.getResult());
    }

    private AdminAuditLog pendingCreate() {
        return AdminAuditLog.pending(
                administratorId,
                AuditAction.ROLE_CREATED,
                AuditTargetType.ROLE,
                null,
                null,
                null,
                null,
                createdAt
        );
    }
}
