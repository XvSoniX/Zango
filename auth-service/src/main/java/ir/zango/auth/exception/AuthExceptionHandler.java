package ir.zango.auth.exception;

import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.MessageSource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ProblemDetail;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.net.URI;
import java.util.List;
import java.util.Locale;
import java.util.UUID;

@RestControllerAdvice
@RequiredArgsConstructor
public class AuthExceptionHandler {

    static final String CORRELATION_ID = "X-Correlation-ID";

    private static final Logger log = LoggerFactory.getLogger(AuthExceptionHandler.class);

    private final MessageSource messageSource;

    @ExceptionHandler(AuthenticationFailedException.class)
    public ProblemDetail handleAuthenticationFailed(HttpServletRequest request) {
        return problem(AuthErrorCode.AUTHENTICATION_FAILED, request, List.of());
    }

    @ExceptionHandler(DuplicateIdentifierException.class)
    public ProblemDetail handleDuplicateIdentifier(HttpServletRequest request) {
        return problem(AuthErrorCode.IDENTIFIER_CONFLICT, request, List.of());
    }

    @ExceptionHandler(MissingDefaultRoleException.class)
    public ProblemDetail handleMissingDefaultRole(HttpServletRequest request) {
        log.error("Registration failed because ROLE_USER is not present");
        return problem(AuthErrorCode.INTERNAL_SERVER_ERROR, request, List.of());
    }

    @ExceptionHandler({RoleNotFoundException.class, UserNotFoundException.class})
    public ProblemDetail handleNotFound(HttpServletRequest request) {
        return problem(AuthErrorCode.NOT_FOUND, request, List.of());
    }

    @ExceptionHandler(DuplicateRoleException.class)
    public ProblemDetail handleDuplicateRole(HttpServletRequest request) {
        return problem(AuthErrorCode.ROLE_CONFLICT, request, List.of());
    }

    @ExceptionHandler(DuplicateRoleAssignmentException.class)
    public ProblemDetail handleDuplicateRoleAssignment(HttpServletRequest request) {
        return problem(AuthErrorCode.ROLE_ASSIGNMENT_CONFLICT, request, List.of());
    }

    @ExceptionHandler(RoleInUseException.class)
    public ProblemDetail handleRoleInUse(HttpServletRequest request) {
        return problem(AuthErrorCode.ROLE_IN_USE, request, List.of());
    }

    @ExceptionHandler(PasswordResetFailedException.class)
    public ProblemDetail handlePasswordResetFailed(HttpServletRequest request) {
        return problem(AuthErrorCode.PASSWORD_RESET_FAILED, request, List.of());
    }

    @ExceptionHandler(TooManyRequestsException.class)
    public ProblemDetail handleTooManyRequests(HttpServletRequest request) {
        return problem(AuthErrorCode.TOO_MANY_REQUESTS, request, List.of());
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ProblemDetail handleValidation(MethodArgumentNotValidException exception, HttpServletRequest request) {
        List<FieldErrorDetailDTO> errors = exception.getBindingResult().getFieldErrors().stream()
                .map(fieldError -> new FieldErrorDetailDTO(fieldError.getField(), fieldError.getDefaultMessage()))
                .toList();
        return problem(AuthErrorCode.BAD_REQUEST, request, errors);
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ProblemDetail handleUnreadableMessage(HttpServletRequest request) {
        return problem(AuthErrorCode.BAD_REQUEST, request, List.of());
    }

    public ProblemDetail create(AuthErrorCode errorCode, HttpServletRequest request) {
        return problem(errorCode, request, List.of());
    }

    private ProblemDetail problem(AuthErrorCode errorCode, HttpServletRequest request, List<FieldErrorDetailDTO> errors) {
        Locale locale = resolveLocale(request);
        String code = errorCode.name();
        ProblemDetail problemDetail = ProblemDetail.forStatusAndDetail(
                errorCode.getStatus(),
                message(errorCode, "detail", locale)
        );
        problemDetail.setType(URI.create(errorCode.getType()));
        problemDetail.setTitle(message(errorCode, "title", locale));
        problemDetail.setInstance(URI.create(request.getRequestURI()));
        problemDetail.setProperty("isSuccess", false);
        problemDetail.setProperty("errorCode", code);
        problemDetail.setProperty("correlationId", correlationId(request));
        if (!errors.isEmpty()) {
            problemDetail.setProperty("errors", errors);
        }
        return problemDetail;
    }

    private String message(AuthErrorCode errorCode, String part, Locale locale) {
        String code = "error." + errorCode.name() + "." + part;
        return messageSource.getMessage(code, null, code, locale);
    }

    private String correlationId(HttpServletRequest request) {
        String correlationId = request.getHeader(CORRELATION_ID);
        if (correlationId == null || correlationId.isBlank()) {
            return UUID.randomUUID().toString();
        }
        return correlationId;
    }

    private Locale resolveLocale(HttpServletRequest request) {
        String acceptLanguage = request.getHeader(HttpHeaders.ACCEPT_LANGUAGE);
        if (acceptLanguage == null || acceptLanguage.isBlank()) {
            return Locale.forLanguageTag("fa");
        }
        try {
            List<Locale.LanguageRange> ranges = Locale.LanguageRange.parse(acceptLanguage);
            Locale matched = Locale.lookup(ranges, List.of(Locale.forLanguageTag("fa"), Locale.ENGLISH));
            return matched != null ? matched : Locale.forLanguageTag("fa");
        } catch (IllegalArgumentException exception) {
            return Locale.forLanguageTag("fa");
        }
    }

    public record FieldErrorDetailDTO(String field, String message) {
    }
}
