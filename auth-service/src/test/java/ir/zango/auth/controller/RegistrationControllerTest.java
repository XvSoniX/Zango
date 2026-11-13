package ir.zango.auth.controller;

import ir.zango.auth.config.SecurityConfig;
import ir.zango.auth.domain.enums.AccountStatusEnum;
import ir.zango.auth.domain.enums.IdentifierTypeEnum;
import ir.zango.auth.dto.RegistrationResponseDTO;
import ir.zango.auth.exception.AuthExceptionHandler;
import ir.zango.auth.exception.DuplicateIdentifierException;
import ir.zango.auth.service.RegistrationService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.context.MessageSourceAutoConfiguration;
import org.springframework.boot.security.autoconfigure.web.servlet.ServletWebSecurityAutoConfiguration;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import java.util.UUID;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(RegistrationController.class)
@Import({
        SecurityConfig.class,
        JwtDecoderTestConfig.class,
        AuthExceptionHandler.class,
        ServletWebSecurityAutoConfiguration.class,
        MessageSourceAutoConfiguration.class
})
class RegistrationControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private RegistrationService registrationService;

    @Test
    void registersAndReturnsCreatedUserWithoutSecrets() throws Exception {
        UUID userId = UUID.randomUUID();
        when(registrationService.register(any())).thenReturn(new RegistrationResponseDTO(
                userId,
                "ada@example.com",
                IdentifierTypeEnum.EMAIL,
                AccountStatusEnum.PENDING_VERIFICATION
        ));

        mockMvc.perform(post("/api/v1/auth/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "identifier": "ada@example.com",
                                  "identifierType": "EMAIL",
                                  "password": "raw-password"
                                }
                                """))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").value(userId.toString()))
                .andExpect(jsonPath("$.identifier").value("ada@example.com"))
                .andExpect(jsonPath("$.identifierType").value("EMAIL"))
                .andExpect(jsonPath("$.status").value("PENDING_VERIFICATION"))
                .andExpect(jsonPath("$.password").doesNotExist())
                .andExpect(jsonPath("$.passwordHash").doesNotExist());
    }

    @Test
    void returnsConflictForDuplicateIdentifier() throws Exception {
        when(registrationService.register(any())).thenThrow(new DuplicateIdentifierException());

        mockMvc.perform(post("/api/v1/auth/register")
                        .header("Accept-Language", "en")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "identifier": "ada",
                                  "identifierType": "USERNAME",
                                  "password": "raw-password"
                                }
                                """))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.errorCode").value("IDENTIFIER_CONFLICT"))
                .andExpect(jsonPath("$.password").doesNotExist())
                .andExpect(jsonPath("$.passwordHash").doesNotExist());
    }

    @Test
    void rejectsInvalidRequestWithoutCallingService() throws Exception {
        String response = mockMvc.perform(post("/api/v1/auth/register")
                        .header("Accept-Language", "en")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "identifier": "not-an-email",
                                  "identifierType": "EMAIL",
                                  "password": "raw-password",
                                  "roles": ["ROLE_ADMIN"]
                                }
                                """))
                .andExpect(status().isBadRequest())
                .andReturn()
                .getResponse()
                .getContentAsString();

        org.assertj.core.api.Assertions.assertThat(response).doesNotContain("raw-password");
        verify(registrationService, never()).register(any());
    }

    @Test
    void keepsOtherEndpointsAuthenticated() throws Exception {
        mockMvc.perform(post("/api/v1/auth/logout-all"))
                .andExpect(status().isUnauthorized());
    }
}
