package ir.nextminds.admin.audit.service;

import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import ir.nextminds.admin.audit.domain.AuditResult;
import ir.nextminds.admin.audit.repository.AdminAuditLogRepository;
import org.junit.jupiter.api.Test;
import java.time.Duration;
import java.time.Instant;
import org.mockito.ArgumentCaptor;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
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
        Instant before = Instant.now().minus(Duration.ofHours(2));
        new AuditPendingMonitor(repository, registry, Duration.ofHours(2)).inspect();
        Instant after = Instant.now().minus(Duration.ofHours(2));
        assertEquals(3.0, registry.get("admin.audit.pending.stale").gauge().value());
        ArgumentCaptor<Instant> cutoff = ArgumentCaptor.forClass(Instant.class);
        verify(repository).countByResultAndCreatedAtBefore(eq(AuditResult.PENDING), cutoff.capture());
        assertTrue(!cutoff.getValue().isBefore(before) && !cutoff.getValue().isAfter(after));
    }

    @Test
    void rejectsNonPositiveStaleThreshold() {
        assertThrows(IllegalArgumentException.class, () -> new AuditPendingMonitor(
                mock(AdminAuditLogRepository.class), new SimpleMeterRegistry(), Duration.ZERO));
    }
}
