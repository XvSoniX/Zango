package ir.nextminds.admin.audit;

import ir.nextminds.admin.audit.domain.AuditAction;
import ir.nextminds.admin.audit.domain.AuditResult;
import ir.nextminds.admin.audit.domain.AuditTargetType;
import ir.nextminds.admin.audit.dto.AuditLogPageResponse;
import ir.nextminds.admin.audit.dto.AuditLogResponse;
import ir.nextminds.admin.audit.query.AuditLogFilter;
import ir.nextminds.admin.audit.service.AuditLogQueryService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/admin/audit-logs")
@RequiredArgsConstructor
public class AuditLogController {

    private final AuditLogQueryService auditLogQueryService;

    @GetMapping
    public AuditLogPageResponse list(
            @RequestParam(required = false) UUID administratorId,
            @RequestParam(required = false) AuditAction action,
            @RequestParam(required = false) AuditTargetType targetType,
            @RequestParam(required = false) UUID targetId,
            @RequestParam(required = false) AuditResult result,
            @RequestParam(required = false) Instant from,
            @RequestParam(required = false) Instant to,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size
    ) {
        return auditLogQueryService.list(new AuditLogFilter(
                administratorId,
                action,
                targetType,
                targetId,
                result,
                from,
                to,
                page,
                size
        ));
    }

    @GetMapping("/{auditId}")
    public AuditLogResponse get(@PathVariable UUID auditId) {
        return auditLogQueryService.get(auditId);
    }
}
