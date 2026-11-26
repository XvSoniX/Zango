package ir.nextminds.admin.audit.domain;

public enum AuditAction {

    ROLE_CREATED(AuditTargetType.ROLE, false),
    ROLE_UPDATED(AuditTargetType.ROLE, false),
    ROLE_DELETED(AuditTargetType.ROLE, true),
    ROLE_ASSIGNED(AuditTargetType.USER, true),
    ROLE_REVOKED(AuditTargetType.USER, true);

    private final AuditTargetType targetType;
    private final boolean reasonRequired;

    AuditAction(AuditTargetType targetType, boolean reasonRequired) {
        this.targetType = targetType;
        this.reasonRequired = reasonRequired;
    }

    public AuditTargetType targetType() {
        return targetType;
    }

    public boolean reasonRequired() {
        return reasonRequired;
    }
}
