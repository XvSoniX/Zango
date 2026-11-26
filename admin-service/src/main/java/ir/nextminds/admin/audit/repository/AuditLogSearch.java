package ir.nextminds.admin.audit.repository;

import ir.nextminds.admin.audit.domain.AdminAuditLog;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.domain.Specification;

public interface AuditLogSearch {

    Page<AdminAuditLog> search(Specification<AdminAuditLog> specification, Pageable pageable);
}
