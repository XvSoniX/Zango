package ir.nextminds.admin.audit.repository;

import ir.nextminds.admin.audit.domain.AdminAuditLog;
import org.springframework.data.repository.Repository;

import java.util.Optional;
import java.util.UUID;

public interface AdminAuditLogRepository extends Repository<AdminAuditLog, UUID>, AuditLogSearch {

    AdminAuditLog save(AdminAuditLog auditLog);

    Optional<AdminAuditLog> findById(UUID id);
}
