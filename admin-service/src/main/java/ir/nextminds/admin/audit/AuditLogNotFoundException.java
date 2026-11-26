package ir.nextminds.admin.audit;

import java.util.UUID;

public class AuditLogNotFoundException extends RuntimeException {

    public AuditLogNotFoundException(UUID auditLogId) {
        super("Audit record was not found: " + auditLogId);
    }
}
