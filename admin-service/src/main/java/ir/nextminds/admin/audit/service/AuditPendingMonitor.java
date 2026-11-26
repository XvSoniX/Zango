package ir.nextminds.admin.audit.service;

import io.micrometer.core.instrument.MeterRegistry;
import ir.nextminds.admin.audit.domain.AuditResult;
import ir.nextminds.admin.audit.repository.AdminAuditLogRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.beans.factory.annotation.Value;

import java.time.Duration;
import java.time.Instant;
import java.util.concurrent.atomic.AtomicLong;

@Component
@Slf4j
public class AuditPendingMonitor {
    private final AdminAuditLogRepository repository;
    private final Duration staleAfter;
    private final AtomicLong pending = new AtomicLong();

    public AuditPendingMonitor(AdminAuditLogRepository repository, MeterRegistry registry,
                               @Value("${nextminds.admin.audit.stale-after:1h}") Duration staleAfter) {
        if (staleAfter.isNegative() || staleAfter.isZero()) {
            throw new IllegalArgumentException("Audit stale-after must be positive");
        }
        this.repository = repository;
        this.staleAfter = staleAfter;
        registry.gauge("admin.audit.pending.stale", pending);
    }

    @Scheduled(initialDelayString = "${nextminds.admin.audit.monitor-initial-delay:1m}",
            fixedDelayString = "${nextminds.admin.audit.monitor-interval:5m}")
    public void inspect() {
        try {
            long count = repository.countByResultAndCreatedAtBefore(AuditResult.PENDING, Instant.now().minus(staleAfter));
            pending.set(count);
            if (count > 0) {
                log.warn("Stale pending audit records require manual review: count={}", count);
            }
        } catch (RuntimeException exception) {
            log.error("Unable to inspect pending audit records", exception);
        }
    }
}
