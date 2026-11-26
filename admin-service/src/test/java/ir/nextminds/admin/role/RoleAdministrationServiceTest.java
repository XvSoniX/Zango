package ir.nextminds.admin.role;

import ir.nextminds.admin.audit.domain.AdminAuditLog;
import ir.nextminds.admin.audit.domain.AuditAction;
import ir.nextminds.admin.audit.domain.AuditTargetType;
import ir.nextminds.admin.audit.service.AuditLogService;
import ir.nextminds.admin.integration.CallerContext;
import ir.nextminds.admin.integration.DownstreamCaller;
import ir.nextminds.admin.integration.auth.AuthRoleClient;
import ir.nextminds.admin.integration.auth.DownstreamCallException;
import ir.nextminds.admin.role.dto.CreateRoleRequest;
import ir.nextminds.admin.role.dto.RoleResponse;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InOrder;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class RoleAdministrationServiceTest {

    private final UUID administratorId = UUID.fromString("bb9e9a5c-54ac-4d4f-8799-ad02539ac1bf");
    private final UUID correlationId = UUID.fromString("4401740b-20f9-4866-aa25-83f9eae7b9fe");
    private final DownstreamCaller caller = new DownstreamCaller(
            administratorId,
            correlationId,
            "Bearer secret-token",
            "en"
    );

    @Mock
    private AuditLogService auditLogService;

    @Mock
    private AuthRoleClient authRoleClient;

    @Mock
    private CallerContext callerContext;

    @InjectMocks
    private RoleAdministrationService service;

    @BeforeEach
    void setUp() {
        when(callerContext.current()).thenReturn(caller);
    }

    @Test
    void createPersistsTheAttemptBeforeCallingAuth() {
        AdminAuditLog pending = pendingCreate();
        RoleResponse created = new RoleResponse(UUID.randomUUID(), "ROLE_SUPPORT", "Support team role");
        when(auditLogService.recordAttempt(
                eq(administratorId),
                eq(AuditAction.ROLE_CREATED),
                eq(AuditTargetType.ROLE),
                isNull(),
                eq("Required for the support team"),
                isNull(),
                eq(correlationId)
        )).thenReturn(pending);
        when(authRoleClient.createRole("ROLE_SUPPORT", "Support team role", caller)).thenReturn(created);

        RoleResponse response = service.createRole(new CreateRoleRequest(
                "ROLE_SUPPORT",
                "Support team role",
                "Required for the support team"
        ));

        assertSame(created, response);
        InOrder order = inOrder(auditLogService, authRoleClient);
        order.verify(auditLogService).recordAttempt(any(), any(), any(), any(), any(), any(), any());
        order.verify(authRoleClient).createRole("ROLE_SUPPORT", "Support team role", caller);
        order.verify(auditLogService).finalizeSuccess(eq(pending.getId()), eq(created.id()), any());
    }

    @Test
    void authIsNotCalledWhenTheAttemptCannotBeStored() {
        when(auditLogService.recordAttempt(any(), any(), any(), any(), any(), any(), any()))
                .thenThrow(new IllegalStateException("database unavailable"));

        assertThrows(IllegalStateException.class, () -> service.createRole(
                new CreateRoleRequest("ROLE_SUPPORT", null, null)
        ));
        verify(authRoleClient, never()).createRole(any(), any(), any());
    }

    @Test
    void confirmedRejectionIsStoredAsFailure() {
        when(auditLogService.recordAttempt(any(), any(), any(), any(), any(), any(), any())).thenReturn(pendingCreate());
        when(authRoleClient.createRole(any(), any(), any())).thenThrow(DownstreamCallException.rejected(
                HttpStatus.CONFLICT,
                "http://localhost/problems/role-conflict",
                "Role already exists",
                "This role name is already registered.",
                "ROLE_CONFLICT",
                java.util.List.of()
        ));

        assertThrows(DownstreamCallException.class, () -> service.createRole(
                new CreateRoleRequest("ROLE_SUPPORT", null, null)
        ));

        ArgumentCaptor<Map<String, Object>> metadata = ArgumentCaptor.captor();
        verify(auditLogService).finalizeFailure(any(), isNull(), metadata.capture());
        assertEquals("REJECTED", metadata.getValue().get("downstreamOutcome"));
        assertEquals(409, metadata.getValue().get("httpStatus"));
        assertEquals("ROLE_CONFLICT", metadata.getValue().get("errorCode"));
    }

    @Test
    void connectionFailureBeforeSendIsNotSent() {
        when(auditLogService.recordAttempt(any(), any(), any(), any(), any(), any(), any())).thenReturn(pendingCreate());
        when(authRoleClient.createRole(any(), any(), any()))
                .thenThrow(DownstreamCallException.unavailable("CONNECTION_FAILED"));

        DownstreamCallException failure = assertThrows(DownstreamCallException.class, () -> service.createRole(
                new CreateRoleRequest("ROLE_SUPPORT", null, null)
        ));

        assertEquals(DownstreamCallException.Kind.UNAVAILABLE, failure.kind());
        ArgumentCaptor<Map<String, Object>> metadata = ArgumentCaptor.captor();
        verify(auditLogService).finalizeFailure(any(), isNull(), metadata.capture());
        assertEquals("NOT_SENT", metadata.getValue().get("downstreamOutcome"));
        assertEquals("CONNECTION_FAILED", metadata.getValue().get("failureType"));
    }

    @Test
    void unknownOutcomeIsNotDescribedAsRejection() {
        when(auditLogService.recordAttempt(any(), any(), any(), any(), any(), any(), any())).thenReturn(pendingCreate());
        when(authRoleClient.createRole(any(), any(), any()))
                .thenThrow(DownstreamCallException.unknown("TIMEOUT"));

        DownstreamCallException failure = assertThrows(DownstreamCallException.class, () -> service.createRole(
                new CreateRoleRequest("ROLE_SUPPORT", null, null)
        ));

        assertEquals(DownstreamCallException.Kind.UNKNOWN, failure.kind());
        ArgumentCaptor<Map<String, Object>> metadata = ArgumentCaptor.captor();
        verify(auditLogService).finalizeFailure(any(), isNull(), metadata.capture());
        assertEquals("UNKNOWN", metadata.getValue().get("downstreamOutcome"));
        assertEquals("TIMEOUT", metadata.getValue().get("failureType"));
        verify(authRoleClient).createRole(any(), any(), any());
    }

    @Test
    void authSuccessIsReturnedWhenAuditFinalizationFails() {
        RoleResponse created = new RoleResponse(UUID.randomUUID(), "ROLE_SUPPORT", null);
        when(auditLogService.recordAttempt(any(), any(), any(), any(), any(), any(), any())).thenReturn(pendingCreate());
        when(authRoleClient.createRole(any(), any(), any())).thenReturn(created);
        when(auditLogService.finalizeSuccess(any(), any(), any())).thenThrow(new IllegalStateException("audit update failed"));

        RoleResponse response = service.createRole(new CreateRoleRequest("ROLE_SUPPORT", null, null));

        assertSame(created, response);
        verify(authRoleClient).createRole(any(), any(), any());
    }

    @Test
    void readsDoNotWriteAuditRecords() {
        service.listRoles();

        verify(authRoleClient).listRoles(caller);
        verify(auditLogService, never()).recordAttempt(any(), any(), any(), any(), any(), any(), any());
    }

    private AdminAuditLog pendingCreate() {
        return AdminAuditLog.pending(
                administratorId,
                AuditAction.ROLE_CREATED,
                AuditTargetType.ROLE,
                null,
                null,
                null,
                correlationId,
                Instant.parse("2026-11-24T12:00:00Z")
        );
    }
}
