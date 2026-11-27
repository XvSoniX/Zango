package ir.nextminds.admin.audit.repository;

import ir.nextminds.admin.audit.domain.AdminAuditLog;
import ir.nextminds.admin.audit.domain.AuditResult;
import org.springframework.data.repository.Repository;

import java.util.Optional;
import java.time.Instant;
import java.util.UUID;

public interface AdminAuditLogRepository extends Repository<AdminAuditLog, UUID>, AuditLogSearch {

    AdminAuditLog save(AdminAuditLog auditLog);

    Optional<AdminAuditLog> findById(UUID id);

    long countByResultAndCreatedAtBefore(AuditResult result, Instant cutoff);
}
