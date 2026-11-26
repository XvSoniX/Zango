package ir.nextminds.admin.audit.query;

import ir.nextminds.admin.audit.domain.AdminAuditLog;
import jakarta.persistence.criteria.Predicate;
import org.springframework.data.jpa.domain.Specification;

import java.util.ArrayList;
import java.util.List;

public final class AuditLogSpecifications {

    private AuditLogSpecifications() {
    }

    public static Specification<AdminAuditLog> matching(AuditLogFilter filter) {
        return (root, query, builder) -> {
            List<Predicate> predicates = new ArrayList<>();
            if (filter.administratorId() != null) {
                predicates.add(builder.equal(root.get("administratorId"), filter.administratorId()));
            }
            if (filter.action() != null) {
                predicates.add(builder.equal(root.get("action"), filter.action()));
            }
            if (filter.targetType() != null) {
                predicates.add(builder.equal(root.get("targetType"), filter.targetType()));
            }
            if (filter.targetId() != null) {
                predicates.add(builder.equal(root.get("targetId"), filter.targetId()));
            }
            if (filter.result() != null) {
                predicates.add(builder.equal(root.get("result"), filter.result()));
            }
            if (filter.from() != null) {
                predicates.add(builder.greaterThanOrEqualTo(root.get("createdAt"), filter.from()));
            }
            if (filter.to() != null) {
                predicates.add(builder.lessThan(root.get("createdAt"), filter.to()));
            }
            if (predicates.isEmpty()) {
                return builder.conjunction();
            }
            return builder.and(predicates.toArray(Predicate[]::new));
        };
    }
}
