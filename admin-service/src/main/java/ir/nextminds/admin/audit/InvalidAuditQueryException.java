package ir.nextminds.admin.audit;

import java.util.List;

public class InvalidAuditQueryException extends RuntimeException {

    private final List<Violation> violations;

    public InvalidAuditQueryException(List<Violation> violations) {
        super("invalid audit query");
        this.violations = List.copyOf(violations);
    }

    public List<Violation> violations() {
        return violations;
    }

    public record Violation(String field, String messageKey) {
    }
}
