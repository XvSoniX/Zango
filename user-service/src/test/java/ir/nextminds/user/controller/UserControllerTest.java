package ir.nextminds.user.controller;

import ir.nextminds.user.dto.UserResponse;
import ir.nextminds.user.exception.BusinessRuleException;
import ir.nextminds.user.exception.DuplicateResourceException;
import ir.nextminds.user.exception.GlobalExceptionHandler;
import ir.nextminds.user.exception.ResourceNotFoundException;
import ir.nextminds.user.service.UserService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.web.PageableHandlerMethodArgumentResolver;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
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
                .setCustomArgumentResolvers(new PageableHandlerMethodArgumentResolver())
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
                .andExpect(jsonPath("$.isSuccess").value(false))
                .andExpect(jsonPath("$.errorCode").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.errors.firstName").exists());
    }

    @Test
    void createDuplicateReturns409ProblemDetail() throws Exception {
        UUID authId = UUID.randomUUID();
        when(userService.create(any())).thenThrow(
                new DuplicateResourceException("User profile already exists for authUserId " + authId));

        String body = """
                {"authUserId":"%s","firstName":"Sara","lastName":"Ahmadi","dateOfBirth":"2015-01-01"}
                """.formatted(authId);

        mockMvc.perform(post("/api/v1/users").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.isSuccess").value(false))
                .andExpect(jsonPath("$.errorCode").value("USER_ALREADY_EXISTS"));
    }

    @Test
    void createOutOfAgeRangeReturns422ProblemDetail() throws Exception {
        when(userService.create(any())).thenThrow(
                new BusinessRuleException("User age 5 is outside the allowed range of 8 to 18"));

        String body = """
                {"authUserId":"%s","firstName":"Sara","lastName":"Ahmadi","dateOfBirth":"2021-01-01"}
                """.formatted(UUID.randomUUID());

        mockMvc.perform(post("/api/v1/users").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().is(422))
                .andExpect(jsonPath("$.isSuccess").value(false))
                .andExpect(jsonPath("$.errorCode").value("AGE_OUT_OF_RANGE"));
    }

    @Test
    void getUnknownUserReturns404() throws Exception {
        UUID id = UUID.randomUUID();
        when(userService.getById(id)).thenThrow(new ResourceNotFoundException("User not found with id " + id));

        mockMvc.perform(get("/api/v1/users/" + id))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.isSuccess").value(false))
                .andExpect(jsonPath("$.errorCode").value("USER_NOT_FOUND"));
    }

    @Test
    void getWithMalformedIdReturns400() throws Exception {
        mockMvc.perform(get("/api/v1/users/not-a-uuid"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errorCode").value("INVALID_ARGUMENT"));
    }

    @Test
    void getByAuthUserIdReturns200() throws Exception {
        UUID id = UUID.randomUUID();
        UUID authId = UUID.randomUUID();
        when(userService.getByAuthUserId(authId)).thenReturn(new UserResponse(
                id, authId, "Sara", "Ahmadi", LocalDate.of(2015, 1, 1), Instant.now(), Instant.now()));

        mockMvc.perform(get("/api/v1/users/by-auth-id/" + authId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.authUserId").value(authId.toString()));
    }

    @Test
    void getAllReturnsPagedUsers() throws Exception {
        UUID id = UUID.randomUUID();
        UUID authId = UUID.randomUUID();
        UserResponse response = new UserResponse(
                id, authId, "Sara", "Ahmadi", LocalDate.of(2015, 1, 1), Instant.now(), Instant.now());
        when(userService.getAll(any())).thenReturn(new PageImpl<>(List.of(response), PageRequest.of(0, 20), 1));

        mockMvc.perform(get("/api/v1/users?page=0&size=20&sort=lastName"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.content[0].firstName").value("Sara"));
    }

    @Test
    void updateReturns200() throws Exception {
        UUID id = UUID.randomUUID();
        UUID authId = UUID.randomUUID();
        when(userService.update(eq(id), any())).thenReturn(new UserResponse(
                id, authId, "Dara", "Ahmadi", LocalDate.of(2014, 2, 2), Instant.now(), Instant.now()));

        String body = """
                {"firstName":"Dara","lastName":"Ahmadi","dateOfBirth":"2014-02-02"}
                """;

        mockMvc.perform(put("/api/v1/users/" + id).contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.firstName").value("Dara"));
    }

    @Test
    void deleteReturns204() throws Exception {
        UUID id = UUID.randomUUID();
        doNothing().when(userService).delete(id);

        mockMvc.perform(delete("/api/v1/users/" + id))
                .andExpect(status().isNoContent());
    }
}
