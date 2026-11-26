package ir.nextminds.admin.audit.service;

import ir.nextminds.admin.audit.AuditLogNotFoundException;
import ir.nextminds.admin.audit.InvalidAuditQueryException;
import ir.nextminds.admin.audit.domain.AdminAuditLog;
import ir.nextminds.admin.audit.domain.AuditAction;
import ir.nextminds.admin.audit.domain.AuditResult;
import ir.nextminds.admin.audit.domain.AuditTargetType;
import ir.nextminds.admin.audit.dto.AuditLogPageResponse;
import ir.nextminds.admin.audit.dto.AuditLogResponse;
import ir.nextminds.admin.audit.query.AuditLogFilter;
import ir.nextminds.admin.audit.repository.AdminAuditLogRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.domain.Specification;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class AuditLogQueryServiceTest {

    @Mock
    private AdminAuditLogRepository auditLogRepository;

    @InjectMocks
    private AuditLogQueryService service;

    @Test
    void listUsesDatabasePaginationSortedByTheRepository() {
        when(auditLogRepository.search(any(), any())).thenReturn(new PageImpl<>(
                List.of(pending()),
                PageRequest.of(0, 20),
                1
        ));

        AuditLogPageResponse page = service.list(filter(null, null, 0, 20));

        ArgumentCaptor<Pageable> pageable = ArgumentCaptor.forClass(Pageable.class);
        verify(auditLogRepository).search(any(Specification.class), pageable.capture());
        assertEquals(0, pageable.getValue().getPageNumber());
        assertEquals(20, pageable.getValue().getPageSize());
        assertEquals(1, page.totalElements());
        assertEquals(1, page.totalPages());
        assertEquals(AuditAction.ROLE_CREATED, page.content().getFirst().action());
        verify(auditLogRepository, never()).save(any());
    }

    @Test
    void emptyPageReportsZeroTotalPages() {
        when(auditLogRepository.search(any(), any())).thenReturn(new PageImpl<>(
                List.of(),
                PageRequest.of(0, 20),
                0
        ));

        AuditLogPageResponse page = service.list(filter(null, null, 0, 20));

        assertEquals(0, page.totalElements());
        assertEquals(0, page.totalPages());
        assertEquals(0, page.content().size());
    }

    @Test
    void targetIdRequiresTargetType() {
        UUID targetId = UUID.randomUUID();

        InvalidAuditQueryException failure = assertThrows(
                InvalidAuditQueryException.class,
                () -> service.list(filter(null, targetId, 0, 20))
        );

        assertEquals("targetType", failure.violations().getFirst().field());
        verify(auditLogRepository, never()).search(any(), any());
    }

    @Test
    void equalBoundsAreAnEmptyRange() {
        Instant instant = Instant.parse("2026-11-24T12:00:00Z");
        when(auditLogRepository.search(any(), any())).thenReturn(new PageImpl<>(
                List.of(),
                PageRequest.of(0, 20),
                0
        ));

        AuditLogPageResponse page = service.list(new AuditLogFilter(
                null, null, null, null, null, instant, instant, 0, 20
        ));

        assertEquals(0, page.totalElements());
        verify(auditLogRepository).search(any(), any());
    }

    @Test
    void reversedBoundsAreRejected() {
        Instant from = Instant.parse("2026-11-24T13:00:00Z");
        Instant to = Instant.parse("2026-11-24T12:00:00Z");

        assertThrows(InvalidAuditQueryException.class, () -> service.list(new AuditLogFilter(
                null, null, null, null, null, from, to, 0, 20
        )));
        verify(auditLogRepository, never()).search(any(), any());
    }

    @Test
    void pageAndSizeBoundsAreRejectedBeforeQuerying() {
        assertThrows(InvalidAuditQueryException.class, () -> service.list(filter(null, null, -1, 20)));
        assertThrows(InvalidAuditQueryException.class, () -> service.list(filter(null, null, 0, 101)));
        verify(auditLogRepository, never()).search(any(), any());
    }

    @Test
    void missingRecordIsNotFound() {
        UUID auditId = UUID.randomUUID();
        when(auditLogRepository.findById(auditId)).thenReturn(Optional.empty());

        assertThrows(AuditLogNotFoundException.class, () -> service.get(auditId));
        verify(auditLogRepository, never()).save(any());
    }

    @Test
    void getReturnsTheStoredRecord() {
        AdminAuditLog auditLog = pending();
        when(auditLogRepository.findById(auditLog.getCorrelationId())).thenReturn(Optional.of(auditLog));

        AuditLogResponse response = service.get(auditLog.getCorrelationId());

        assertEquals(AuditResult.PENDING, response.result());
        assertEquals(auditLog.getCorrelationId(), response.correlationId());
        verify(auditLogRepository, never()).save(any());
    }

    private AuditLogFilter filter(AuditTargetType targetType, UUID targetId, int page, int size) {
        return new AuditLogFilter(null, null, targetType, targetId, null, null, null, page, size);
    }

    private AdminAuditLog pending() {
        return AdminAuditLog.pending(
                UUID.randomUUID(),
                AuditAction.ROLE_CREATED,
                AuditTargetType.ROLE,
                null,
                null,
                null,
                UUID.randomUUID(),
                Instant.parse("2026-11-24T12:00:00Z")
        );
    }
}
