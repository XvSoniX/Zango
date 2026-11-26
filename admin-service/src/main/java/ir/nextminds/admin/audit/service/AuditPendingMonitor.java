package ir.nextminds.admin.audit.service;

import io.micrometer.core.instrument.MeterRegistry;
import ir.nextminds.admin.audit.domain.AuditResult;
import ir.nextminds.admin.audit.repository.AdminAuditLogRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.concurrent.atomic.AtomicLong;

@Component
@Slf4j
public class AuditPendingMonitor {
    private final AdminAuditLogRepository repository;
    private final AtomicLong pending = new AtomicLong();

    public AuditPendingMonitor(AdminAuditLogRepository repository, MeterRegistry registry) {
        this.repository = repository;
        registry.gauge("admin.audit.pending.stale", pending);
    }

    @Scheduled(initialDelayString = "PT1M", fixedDelayString = "PT5M")
    public void inspect() {
        try {
            long count = repository.countByResultAndCreatedAtBefore(AuditResult.PENDING, Instant.now().minus(1, ChronoUnit.HOURS));
            pending.set(count);
            if (count > 0) {
                log.warn("Stale pending audit records require manual review: count={}", count);
            }
        } catch (RuntimeException exception) {
            log.error("Unable to inspect pending audit records", exception);
        }
    }
}
