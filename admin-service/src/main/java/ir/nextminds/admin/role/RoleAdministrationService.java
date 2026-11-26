package ir.nextminds.admin.role;

import ir.nextminds.admin.audit.domain.AdminAuditLog;
import ir.nextminds.admin.audit.domain.AuditAction;
import ir.nextminds.admin.audit.domain.AuditTargetType;
import ir.nextminds.admin.audit.service.AuditLogService;
import ir.nextminds.admin.integration.CallerContext;
import ir.nextminds.admin.integration.DownstreamCaller;
import ir.nextminds.admin.integration.auth.AuthRoleClient;
import ir.nextminds.admin.integration.auth.DownstreamCallException;
import ir.nextminds.admin.role.dto.AssignRoleRequest;
import ir.nextminds.admin.role.dto.CreateRoleRequest;
import ir.nextminds.admin.role.dto.RoleResponse;
import ir.nextminds.admin.role.dto.UpdateRoleRequest;
import ir.nextminds.admin.role.dto.UserRolesResponse;
import io.micrometer.core.instrument.MeterRegistry;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.function.Function;

@Service
@RequiredArgsConstructor
@Slf4j
public class RoleAdministrationService {

    private static final String DOWNSTREAM = "auth-service";

    private final AuditLogService auditLogService;
    private final AuthRoleClient authRoleClient;
    private final CallerContext callerContext;
    private final MeterRegistry meterRegistry;

    public List<RoleResponse> listRoles() {
        return authRoleClient.listRoles(callerContext.current());
    }

    public UserRolesResponse findUserRoles(UUID userId) {
        return authRoleClient.findUserRoles(userId, callerContext.current());
    }

    public RoleResponse createRole(CreateRoleRequest request) {
        return mutate(
                AuditAction.ROLE_CREATED,
                AuditTargetType.ROLE,
                null,
                request.reason(),
                caller -> authRoleClient.createRole(request.name(), request.description(), caller),
                created -> new Finalization(
                        created.id(),
                        metadata("CONFIRMED", created.id(), created.name(), null)
                )
        );
    }

    public RoleResponse updateRole(UUID roleId, UpdateRoleRequest request) {
        return mutate(
                AuditAction.ROLE_UPDATED,
                AuditTargetType.ROLE,
                roleId,
                request.reason(),
                caller -> authRoleClient.updateRole(roleId, request.name(), request.description(), caller),
                updated -> new Finalization(
                        null,
                        metadata(
                                "CONFIRMED",
                                updated == null || updated.id() == null ? roleId : updated.id(),
                                updated == null ? null : updated.name(),
                                updated == null ? null : updated.description()
                        )
                )
        );
    }

    public void deleteRole(UUID roleId, String reason) {
        mutate(
                AuditAction.ROLE_DELETED,
                AuditTargetType.ROLE,
                roleId,
                reason,
                caller -> {
                    authRoleClient.deleteRole(roleId, caller);
                    return null;
                },
                ignored -> new Finalization(null, metadata("CONFIRMED", roleId, null, null))
        );
    }

    public void assignRole(UUID userId, AssignRoleRequest request) {
        mutate(
                AuditAction.ROLE_ASSIGNED,
                AuditTargetType.USER,
                userId,
                request.reason(),
                caller -> {
                    authRoleClient.assignRole(userId, request.roleId(), caller);
                    return null;
                },
                ignored -> new Finalization(null, metadata("CONFIRMED", request.roleId(), null, null))
        );
    }

    public void revokeRole(UUID userId, UUID roleId, String reason) {
        mutate(
                AuditAction.ROLE_REVOKED,
                AuditTargetType.USER,
                userId,
                reason,
                caller -> {
                    authRoleClient.revokeRole(userId, roleId, caller);
                    return null;
                },
                ignored -> new Finalization(null, metadata("CONFIRMED", roleId, null, null))
        );
    }

    private <T> T mutate(
            AuditAction action,
            AuditTargetType targetType,
            UUID targetId,
            String reason,
            Function<DownstreamCaller, T> authCall,
            Function<T, Finalization> success
    ) {
        DownstreamCaller caller = callerContext.current();
        AdminAuditLog auditLog = auditLogService.recordAttempt(
                caller.administratorId(),
                action,
                targetType,
                targetId,
                reason,
                null,
                caller.correlationId()
        );
        T result;
        try {
            result = authCall.apply(caller);
        } catch (DownstreamCallException exception) {
            finalizeFailure(auditLog, caller, action, exception);
            throw exception;
        }
        Finalization finalization = success.apply(result);
        try {
            auditLogService.finalizeSuccess(auditLog.getId(), finalization.targetId(), finalization.metadata());
        } catch (RuntimeException exception) {
            meterRegistry.counter("admin.audit.finalization.failures", "outcome", "success").increment();
            log.error(
                    "Audit finalization failed after Auth success. auditId={}, correlationId={}, action={}",
                    auditLog.getId(),
                    caller.correlationId(),
                    action,
                    exception
            );
        }
        return result;
    }

    private void finalizeFailure(
            AdminAuditLog auditLog,
            DownstreamCaller caller,
            AuditAction action,
            DownstreamCallException exception
    ) {
        try {
            auditLogService.finalizeFailure(auditLog.getId(), null, failureMetadata(exception));
        } catch (RuntimeException failure) {
            meterRegistry.counter("admin.audit.finalization.failures", "outcome", "failure").increment();
            log.error(
                    "Audit finalization failed after Auth outcome. auditId={}, correlationId={}, action={}",
                    auditLog.getId(),
                    caller.correlationId(),
                    action,
                    failure
            );
        }
    }

    private Map<String, Object> failureMetadata(DownstreamCallException exception) {
        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("downstream", DOWNSTREAM);
        if (exception.kind() == DownstreamCallException.Kind.REJECTED) {
            metadata.put("downstreamOutcome", "REJECTED");
            if (exception.status() != null) {
                metadata.put("httpStatus", exception.status().value());
            }
            if (exception.errorCode() != null) {
                metadata.put("errorCode", exception.errorCode());
            }
            return metadata;
        }
        metadata.put(
                "downstreamOutcome",
                exception.kind() == DownstreamCallException.Kind.UNAVAILABLE ? "NOT_SENT" : "UNKNOWN"
        );
        if (exception.failureType() != null) {
            metadata.put("failureType", exception.failureType());
        }
        return metadata;
    }

    private Map<String, Object> metadata(String outcome, UUID roleId, String roleName, String description) {
        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("downstream", DOWNSTREAM);
        metadata.put("downstreamOutcome", outcome);
        if (roleId != null) {
            metadata.put("roleId", roleId.toString());
        }
        if (roleName != null) {
            metadata.put("roleName", roleName);
        }
        if (description != null) {
            metadata.put("description", description);
        }
        return metadata;
    }

    private record Finalization(UUID targetId, Map<String, Object> metadata) {
    }
}
