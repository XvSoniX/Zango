package ir.nextminds.admin.audit.service;

import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import ir.nextminds.admin.audit.domain.AuditResult;
import ir.nextminds.admin.audit.repository.AdminAuditLogRepository;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class AuditPendingMonitorTest {
    @Test
    void reportsStaleAttemptsWithoutChangingThem() {
        AdminAuditLogRepository repository = mock(AdminAuditLogRepository.class);
        SimpleMeterRegistry registry = new SimpleMeterRegistry();
        when(repository.countByResultAndCreatedAtBefore(eq(AuditResult.PENDING), any())).thenReturn(3L);
        new AuditPendingMonitor(repository, registry).inspect();
        assertEquals(3.0, registry.get("admin.audit.pending.stale").gauge().value());
        verify(repository).countByResultAndCreatedAtBefore(eq(AuditResult.PENDING), any());
    }
}
