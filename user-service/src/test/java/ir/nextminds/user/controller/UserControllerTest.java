package ir.nextminds.user.controller;

import ir.nextminds.user.dto.UserResponse;
import ir.nextminds.user.exception.GlobalExceptionHandler;
import ir.nextminds.user.exception.ResourceNotFoundException;
import ir.nextminds.user.service.UserService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.time.Instant;
import java.time.LocalDate;
import java.util.UUID;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Plain MockMvc (no Spring context, no database) so the test does not depend on slice-test packages. */
@ExtendWith(MockitoExtension.class)
class UserControllerTest {

    @Mock
    private UserService userService;

    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders.standaloneSetup(new UserController(userService))
                .setControllerAdvice(new GlobalExceptionHandler())
                .build();
    }

    @Test
    void createReturns201WithLocation() throws Exception {
        UUID id = UUID.randomUUID();
        UUID authId = UUID.randomUUID();
        when(userService.create(any())).thenReturn(new UserResponse(
                id, authId, "Sara", "Ahmadi", LocalDate.of(2015, 1, 1), Instant.now(), Instant.now()));

        String body = """
                {"authUserId":"%s","firstName":"Sara","lastName":"Ahmadi","dateOfBirth":"2015-01-01"}
                """.formatted(authId);

        mockMvc.perform(post("/api/v1/users").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isCreated())
                .andExpect(header().string("Location", org.hamcrest.Matchers.endsWith("/api/v1/users/" + id)))
                .andExpect(jsonPath("$.firstName").value("Sara"));
    }

    @Test
    void createWithBlankNameReturns400WithFieldErrors() throws Exception {
        String body = """
                {"authUserId":"%s","firstName":"","lastName":"Ahmadi","dateOfBirth":"2015-01-01"}
                """.formatted(UUID.randomUUID());

        mockMvc.perform(post("/api/v1/users").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.firstName").exists());
    }

    @Test
    void getUnknownUserReturns404() throws Exception {
        UUID id = UUID.randomUUID();
        when(userService.getById(id)).thenThrow(new ResourceNotFoundException("User not found with id " + id));

        mockMvc.perform(get("/api/v1/users/" + id))
                .andExpect(status().isNotFound());
    }

    @Test
    void getWithMalformedIdReturns400() throws Exception {
        mockMvc.perform(get("/api/v1/users/not-a-uuid"))
                .andExpect(status().isBadRequest());
    }
}
