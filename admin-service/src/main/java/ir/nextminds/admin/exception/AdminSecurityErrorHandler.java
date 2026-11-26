package ir.nextminds.admin.exception;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ProblemDetail;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.AuthenticationEntryPoint;
import org.springframework.security.web.access.AccessDeniedHandler;
import org.springframework.stereotype.Component;
import tools.jackson.databind.json.JsonMapper;

import java.io.IOException;

@Component
@RequiredArgsConstructor
@Slf4j
public class AdminSecurityErrorHandler implements AuthenticationEntryPoint, AccessDeniedHandler {

    private final AdminExceptionHandler adminExceptionHandler;
    private final JsonMapper jsonMapper;

    @Override
    public void commence(
            HttpServletRequest request,
            HttpServletResponse response,
            AuthenticationException exception
    ) throws IOException {
        log.warn("Authentication rejected on {} {}", request.getMethod(), request.getRequestURI());
        response.setHeader(HttpHeaders.WWW_AUTHENTICATE, "Bearer");
        write(response, adminExceptionHandler.create(AdminErrorCode.UNAUTHORIZED, request));
    }

    @Override
    public void handle(
            HttpServletRequest request,
            HttpServletResponse response,
            AccessDeniedException exception
    ) throws IOException {
        log.warn(
                "Access denied for subject {} on {} {}",
                subject(),
                request.getMethod(),
                request.getRequestURI()
        );
        write(response, adminExceptionHandler.create(AdminErrorCode.FORBIDDEN, request));
    }

    private String subject() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null || !authentication.isAuthenticated()) {
            return "anonymous";
        }
        return authentication.getName();
    }

    private void write(HttpServletResponse response, ProblemDetail problem) throws IOException {
        if (response.isCommitted()) {
            return;
        }
        Object correlationId = problem.getProperties() == null
                ? null
                : problem.getProperties().get("correlationId");
        if (correlationId != null) {
            response.setHeader(AdminExceptionHandler.CORRELATION_ID, correlationId.toString());
        }
        response.setStatus(problem.getStatus());
        response.setContentType(MediaType.APPLICATION_PROBLEM_JSON_VALUE);
        response.setCharacterEncoding("UTF-8");
        jsonMapper.writeValue(response.getOutputStream(), problem);
    }
}
