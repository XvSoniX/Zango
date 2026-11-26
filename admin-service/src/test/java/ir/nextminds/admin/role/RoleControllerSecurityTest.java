package ir.nextminds.admin.role;

import ir.nextminds.admin.audit.repository.AdminAuditLogRepository;
import ir.nextminds.admin.role.dto.RoleResponse;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc
class RoleControllerSecurityTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private RoleAdministrationService roleAdministrationService;

    @MockitoBean
    private AdminAuditLogRepository adminAuditLogRepository;

    @MockitoBean
    private JwtDecoder jwtDecoder;

    @Test
    void missingTokenIsUnauthorized() throws Exception {
        mockMvc.perform(get("/api/v1/admin/roles"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.errorCode").value("UNAUTHORIZED"))
                .andExpect(jsonPath("$.isSuccess").value(false));
    }

    @Test
    void userRoleIsForbidden() throws Exception {
        when(jwtDecoder.decode("user-token")).thenReturn(token(List.of("ROLE_USER")));

        mockMvc.perform(get("/api/v1/admin/roles").header("Authorization", "Bearer user-token"))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.errorCode").value("FORBIDDEN"));
    }

    @Test
    void adminCanListRoles() throws Exception {
        when(jwtDecoder.decode("admin-token")).thenReturn(token(List.of("ROLE_ADMIN")));
        when(roleAdministrationService.listRoles()).thenReturn(List.of(
                new RoleResponse(UUID.fromString("6f1c0a3e-7b2d-4e91-9c4a-1d8e5a0b2f11"), "ROLE_ADMIN", null)
        ));

        mockMvc.perform(get("/api/v1/admin/roles").header("Authorization", "Bearer admin-token"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].name").value("ROLE_ADMIN"));
    }

    @Test
    void invalidRoleNameIsRejectedBeforeDelegation() throws Exception {
        when(jwtDecoder.decode("admin-token")).thenReturn(token(List.of("ROLE_ADMIN")));

        mockMvc.perform(post("/api/v1/admin/roles")
                        .header("Authorization", "Bearer admin-token")
                        .contentType("application/json")
                        .content("{\"name\":\"support\",\"description\":null}"))
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
