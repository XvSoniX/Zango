package ir.nextminds.admin.audit;

import ir.nextminds.admin.audit.repository.AdminAuditLogRepository;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class AuditLogControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private AdminAuditLogRepository adminAuditLogRepository;

    @MockitoBean
    private JwtDecoder jwtDecoder;

    @Test
    void missingTokenIsUnauthorized() throws Exception {
        mockMvc.perform(get("/api/v1/admin/audit-logs"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.errorCode").value("UNAUTHORIZED"));
    }

    @Test
    void userRoleIsForbidden() throws Exception {
        when(jwtDecoder.decode("user-token")).thenReturn(token(List.of("ROLE_USER")));

        mockMvc.perform(get("/api/v1/admin/audit-logs").header("Authorization", "Bearer user-token"))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.errorCode").value("FORBIDDEN"));
    }

    @Test
    void adminReceivesAnEmptyPageWithoutWritingAuditRows() throws Exception {
        when(jwtDecoder.decode("admin-token")).thenReturn(token(List.of("ROLE_ADMIN")));
        when(adminAuditLogRepository.search(any(), any())).thenReturn(new PageImpl<>(
                List.of(),
                PageRequest.of(0, 20),
                0
        ));

        mockMvc.perform(get("/api/v1/admin/audit-logs").header("Authorization", "Bearer admin-token"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.content").isArray())
                .andExpect(jsonPath("$.page").value(0))
                .andExpect(jsonPath("$.size").value(20))
                .andExpect(jsonPath("$.totalElements").value(0))
                .andExpect(jsonPath("$.totalPages").value(0));

        verify(adminAuditLogRepository, never()).save(any());
    }

    @Test
    void malformedAuditIdIsBadRequest() throws Exception {
        when(jwtDecoder.decode("admin-token")).thenReturn(token(List.of("ROLE_ADMIN")));

        mockMvc.perform(get("/api/v1/admin/audit-logs/not-a-uuid")
                        .header("Authorization", "Bearer admin-token"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errorCode").value("BAD_REQUEST"));
    }

    @Test
    void unknownAuditIdIsNotFound() throws Exception {
        UUID auditId = UUID.fromString("3d6c2a10-0d1e-4f2a-9b7c-1a2b3c4d5e6f");
        when(jwtDecoder.decode("admin-token")).thenReturn(token(List.of("ROLE_ADMIN")));
        when(adminAuditLogRepository.findById(auditId)).thenReturn(Optional.empty());

        mockMvc.perform(get("/api/v1/admin/audit-logs/" + auditId)
                        .header("Authorization", "Bearer admin-token")
                        .header("Accept-Language", "en"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.errorCode").value("NOT_FOUND"))
                .andExpect(jsonPath("$.title").value("Resource not found"))
                .andExpect(jsonPath("$.isSuccess").value(false));
    }

    @Test
    void targetIdWithoutTargetTypeIsRejected() throws Exception {
        when(jwtDecoder.decode("admin-token")).thenReturn(token(List.of("ROLE_ADMIN")));

        mockMvc.perform(get("/api/v1/admin/audit-logs")
                        .header("Authorization", "Bearer admin-token")
                        .header("Accept-Language", "en")
                        .param("targetId", UUID.randomUUID().toString()))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errorCode").value("BAD_REQUEST"))
                .andExpect(jsonPath("$.errors[0].field").value("targetType"));

        verify(adminAuditLogRepository, never()).search(any(), any());
    }

    @Test
    void invalidActionIsBadRequest() throws Exception {
        when(jwtDecoder.decode("admin-token")).thenReturn(token(List.of("ROLE_ADMIN")));

        mockMvc.perform(get("/api/v1/admin/audit-logs")
                        .header("Authorization", "Bearer admin-token")
                        .param("action", "NOT_AN_ACTION"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errorCode").value("BAD_REQUEST"));
    }

    private Jwt token(List<String> roles) {
        return Jwt.withTokenValue("token")
                .header("alg", "RS256")
                .subject("bb9e9a5c-54ac-4d4f-8799-ad02539ac1bf")
                .issuedAt(Instant.parse("2026-11-24T12:00:00Z"))
                .expiresAt(Instant.parse("2026-11-24T12:15:00Z"))
                .claim("roles", roles)
                .build();
    }
}
