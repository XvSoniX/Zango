package ir.nextminds.admin.audit.repository;

import ir.nextminds.admin.audit.domain.AdminAuditLog;
import jakarta.persistence.EntityManager;
import jakarta.persistence.TypedQuery;
import jakarta.persistence.criteria.CriteriaBuilder;
import jakarta.persistence.criteria.CriteriaQuery;
import jakarta.persistence.criteria.Predicate;
import jakarta.persistence.criteria.Root;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.domain.Specification;

import java.util.List;

public class AuditLogSearchImpl implements AuditLogSearch {

    private final EntityManager entityManager;

    public AuditLogSearchImpl(EntityManager entityManager) {
        this.entityManager = entityManager;
    }

    @Override
    public Page<AdminAuditLog> search(Specification<AdminAuditLog> specification, Pageable pageable) {
        CriteriaBuilder builder = entityManager.getCriteriaBuilder();

        CriteriaQuery<AdminAuditLog> query = builder.createQuery(AdminAuditLog.class);
        Root<AdminAuditLog> root = query.from(AdminAuditLog.class);
        query.select(root);
        Predicate predicate = specification.toPredicate(root, query, builder);
        if (predicate != null) {
            query.where(predicate);
        }
        query.orderBy(builder.desc(root.get("createdAt")), builder.desc(root.get("id")));

        TypedQuery<AdminAuditLog> typedQuery = entityManager.createQuery(query);
        typedQuery.setFirstResult(Math.toIntExact(pageable.getOffset()));
        typedQuery.setMaxResults(pageable.getPageSize());
        List<AdminAuditLog> content = typedQuery.getResultList();

        CriteriaQuery<Long> countQuery = builder.createQuery(Long.class);
        Root<AdminAuditLog> countRoot = countQuery.from(AdminAuditLog.class);
        countQuery.select(builder.count(countRoot));
        Predicate countPredicate = specification.toPredicate(countRoot, countQuery, builder);
        if (countPredicate != null) {
            countQuery.where(countPredicate);
        }
        long total = entityManager.createQuery(countQuery).getSingleResult();

        return new PageImpl<>(content, pageable, total);
    }
}
