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
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;

import java.time.Instant;
import java.util.UUID;

@RestController
@Tag(name = "Audit logs / گزارش حسابرسی", description = "Inspect administrative change attempts. / بررسی تلاش‌های تغییرات مدیریتی.")
@SecurityRequirement(name = "bearerAuth")
@ApiResponses({@ApiResponse(responseCode = "400", description = "Invalid query (Problem Detail)"),
        @ApiResponse(responseCode = "401", description = "Missing or invalid token"),
        @ApiResponse(responseCode = "403", description = "ROLE_ADMIN required"),
        @ApiResponse(responseCode = "404", description = "Audit record not found")})
@RequestMapping("/api/v1/admin/audit-logs")
@RequiredArgsConstructor
public class AuditLogController {

    private final AuditLogQueryService auditLogQueryService;

    @GetMapping
    @Operation(summary = "Search audit logs / جست‌وجوی گزارش حسابرسی", description = "Searches administrative change attempts using optional filters. Results are ordered by creation time and ID descending; targetId requires targetType. Reads do not create audit records.\n\nتلاش‌های تغییرات مدیریتی را با فیلترهای اختیاری جست‌وجو می‌کند. ترتیب بر اساس زمان ایجاد و شناسه به‌صورت نزولی است؛ استفاده از targetId نیازمند targetType است. خواندن، Audit جدید ایجاد نمی‌کند.")
    public AuditLogPageResponse list(
            @Parameter(description = "Administrator UUID / شناسه مدیر") @RequestParam(required = false) UUID administratorId,
            @Parameter(description = "Audited action / نوع عملیات") @RequestParam(required = false) AuditAction action,
            @Parameter(description = "Target type / نوع هدف") @RequestParam(required = false) AuditTargetType targetType,
            @Parameter(description = "Target UUID; requires targetType / شناسه هدف؛ نیازمند targetType") @RequestParam(required = false) UUID targetId,
            @Parameter(description = "PENDING, SUCCESS or FAILURE / وضعیت ثبت") @RequestParam(required = false) AuditResult result,
            @Parameter(description = "Inclusive start time, ISO-8601 / آغاز بازه شامل مرز") @RequestParam(required = false) Instant from,
            @Parameter(description = "Exclusive end time, ISO-8601 / پایان بازه بدون احتساب مرز") @RequestParam(required = false) Instant to,
            @Parameter(description = "Zero-based page / شماره صفحه از صفر") @RequestParam(defaultValue = "0") int page,
            @Parameter(description = "Page size, 1–100 / اندازه صفحه، ۱ تا ۱۰۰") @RequestParam(defaultValue = "20") int size
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
    @Operation(summary = "Get an audit log / دریافت گزارش حسابرسی", description = "Returns one audit attempt, including its action, outcome, correlation ID and available metadata.\n\nجزئیات یک تلاش مدیریتی شامل عملیات، نتیجه، شناسه همبستگی و فراداده موجود را برمی‌گرداند.")
    public AuditLogResponse get(@PathVariable UUID auditId) {
        return auditLogQueryService.get(auditId);
    }
}
