package ir.nextminds.admin.audit.service;

import ir.nextminds.admin.audit.AuditLogNotFoundException;
import ir.nextminds.admin.audit.InvalidAuditQueryException;
import ir.nextminds.admin.audit.domain.AdminAuditLog;
import ir.nextminds.admin.audit.dto.AuditLogPageResponse;
import ir.nextminds.admin.audit.dto.AuditLogResponse;
import ir.nextminds.admin.audit.query.AuditLogFilter;
import ir.nextminds.admin.audit.query.AuditLogSpecifications;
import ir.nextminds.admin.audit.repository.AdminAuditLogRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class AuditLogQueryService {

    static final int DEFAULT_PAGE = 0;
    static final int DEFAULT_SIZE = 20;
    static final int MAX_SIZE = 100;

    private final AdminAuditLogRepository auditLogRepository;

    public AuditLogPageResponse list(AuditLogFilter filter) {
        validate(filter);
        Page<AdminAuditLog> page = auditLogRepository.search(
                AuditLogSpecifications.matching(filter),
                PageRequest.of(filter.page(), filter.size())
        );
        List<AuditLogResponse> content = page.getContent().stream()
                .map(AuditLogResponse::from)
                .toList();
        return new AuditLogPageResponse(
                content,
                page.getNumber(),
                page.getSize(),
                page.getTotalElements(),
                page.getTotalPages()
        );
    }

    public AuditLogResponse get(UUID auditId) {
        return auditLogRepository.findById(auditId)
                .map(AuditLogResponse::from)
                .orElseThrow(() -> new AuditLogNotFoundException(auditId));
    }

    private void validate(AuditLogFilter filter) {
        List<InvalidAuditQueryException.Violation> violations = new ArrayList<>();
        if (filter.page() < DEFAULT_PAGE) {
            violations.add(new InvalidAuditQueryException.Violation("page", "audit.query.page.min"));
        }
        if (filter.size() < 1 || filter.size() > MAX_SIZE) {
            violations.add(new InvalidAuditQueryException.Violation("size", "audit.query.size.range"));
        }
        if (filter.targetId() != null && filter.targetType() == null) {
            violations.add(new InvalidAuditQueryException.Violation("targetType", "audit.query.targetType.required"));
        }
        if (filter.from() != null && filter.to() != null && filter.from().isAfter(filter.to())) {
            violations.add(new InvalidAuditQueryException.Violation("from", "audit.query.range.invalid"));
        }
        if (filter.page() >= DEFAULT_PAGE && filter.size() >= 1 && filter.size() <= MAX_SIZE) {
            long offset = (long) filter.page() * filter.size();
            if (offset > Integer.MAX_VALUE) {
                violations.add(new InvalidAuditQueryException.Violation("page", "audit.query.page.min"));
            }
        }
        if (!violations.isEmpty()) {
            throw new InvalidAuditQueryException(violations);
        }
    }
}
