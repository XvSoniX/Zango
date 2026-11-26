package ir.nextminds.admin.exception;

import ir.nextminds.admin.audit.AuditLogNotFoundException;
import ir.nextminds.admin.audit.InvalidAuditQueryException;
import ir.nextminds.admin.integration.CorrelationIdFilter;
import ir.nextminds.admin.integration.auth.DownstreamCallException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.MessageSource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ProblemDetail;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.net.URI;
import java.util.List;
import java.util.Locale;
import java.util.UUID;

@RestControllerAdvice
@RequiredArgsConstructor
@Slf4j
public class AdminExceptionHandler {

    static final String CORRELATION_ID = "X-Correlation-ID";

    private final MessageSource messageSource;

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ProblemDetail handleValidation(
            MethodArgumentNotValidException exception,
            HttpServletRequest request,
            HttpServletResponse response
    ) {
        List<FieldErrorDetailDTO> errors = exception.getBindingResult().getFieldErrors().stream()
                .map(fieldError -> new FieldErrorDetailDTO(fieldError.getField(), fieldError.getDefaultMessage()))
                .toList();
        return problem(AdminErrorCode.BAD_REQUEST, request, response, errors);
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ProblemDetail handleUnreadableMessage(HttpServletRequest request, HttpServletResponse response) {
        return problem(AdminErrorCode.BAD_REQUEST, request, response, List.of());
    }

    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    public ProblemDetail handleTypeMismatch(HttpServletRequest request, HttpServletResponse response) {
        return problem(AdminErrorCode.BAD_REQUEST, request, response, List.of());
    }

    @ExceptionHandler(InvalidAuditQueryException.class)
    public ProblemDetail handleInvalidAuditQuery(
            InvalidAuditQueryException exception,
            HttpServletRequest request,
            HttpServletResponse response
    ) {
        Locale locale = resolveLocale(request);
        List<FieldErrorDetailDTO> errors = exception.violations().stream()
                .map(violation -> new FieldErrorDetailDTO(
                        violation.field(),
                        messageSource.getMessage(violation.messageKey(), null, violation.messageKey(), locale)
                ))
                .toList();
        return problem(AdminErrorCode.BAD_REQUEST, request, response, errors);
    }

    @ExceptionHandler(AuditLogNotFoundException.class)
    public ProblemDetail handleAuditLogNotFound(HttpServletRequest request, HttpServletResponse response) {
        return problem(AdminErrorCode.NOT_FOUND, request, response, List.of());
    }

    @ExceptionHandler(DownstreamCallException.class)
    public ProblemDetail handleDownstream(
            DownstreamCallException exception,
            HttpServletRequest request,
            HttpServletResponse response
    ) {
        if (exception.kind() == DownstreamCallException.Kind.REJECTED) {
            return rejected(exception, request, response);
        }
        AdminErrorCode errorCode = exception.kind() == DownstreamCallException.Kind.UNAVAILABLE
                ? AdminErrorCode.DOWNSTREAM_UNAVAILABLE
                : AdminErrorCode.DOWNSTREAM_OUTCOME_UNKNOWN;
        return problem(errorCode, request, response, List.of());
    }

    @ExceptionHandler(Exception.class)
    public ProblemDetail handleUnexpected(Exception exception, HttpServletRequest request, HttpServletResponse response) {
        log.error("Unexpected failure on {} {}", request.getMethod(), request.getRequestURI(), exception);
        return problem(AdminErrorCode.INTERNAL_SERVER_ERROR, request, response, List.of());
    }

    public ProblemDetail create(AdminErrorCode errorCode, HttpServletRequest request) {
        return problem(errorCode, request, null, List.of());
    }

    private ProblemDetail problem(
            AdminErrorCode errorCode,
            HttpServletRequest request,
            HttpServletResponse response,
            List<FieldErrorDetailDTO> errors
    ) {
        Locale locale = resolveLocale(request);
        ProblemDetail problemDetail = ProblemDetail.forStatusAndDetail(
                errorCode.getStatus(),
                message(errorCode, "detail", locale)
        );
        problemDetail.setType(URI.create(errorCode.getType()));
        problemDetail.setTitle(message(errorCode, "title", locale));
        problemDetail.setInstance(URI.create(request.getRequestURI()));
        String correlationId = correlationId(request);
        problemDetail.setProperty("isSuccess", false);
        problemDetail.setProperty("errorCode", errorCode.name());
        problemDetail.setProperty("correlationId", correlationId);
        if (!errors.isEmpty()) {
            problemDetail.setProperty("errors", errors);
        }
        if (response != null) {
            response.setHeader(CORRELATION_ID, correlationId);
        }
        return problemDetail;
    }

    private String message(AdminErrorCode errorCode, String part, Locale locale) {
        String code = "error." + errorCode.name() + "." + part;
        return messageSource.getMessage(code, null, code, locale);
    }

    private ProblemDetail rejected(
            DownstreamCallException exception,
            HttpServletRequest request,
            HttpServletResponse response
    ) {
        ProblemDetail problemDetail = ProblemDetail.forStatusAndDetail(exception.status(), exception.detail());
        problemDetail.setTitle(exception.title());
        if (exception.type() != null) {
            problemDetail.setType(URI.create(exception.type()));
        }
        problemDetail.setInstance(URI.create(request.getRequestURI()));
        String correlationId = correlationId(request);
        problemDetail.setProperty("isSuccess", false);
        problemDetail.setProperty("errorCode", exception.errorCode());
        problemDetail.setProperty("correlationId", correlationId);
        if (!exception.errors().isEmpty()) {
            problemDetail.setProperty("errors", exception.errors());
        }
        response.setHeader(CORRELATION_ID, correlationId);
        return problemDetail;
    }

    private String correlationId(HttpServletRequest request) {
        Object established = request.getAttribute(CorrelationIdFilter.CORRELATION_ATTRIBUTE);
        if (established instanceof UUID establishedId) {
            return establishedId.toString();
        }
        String correlationId = request.getHeader(CORRELATION_ID);
        if (correlationId == null || correlationId.isBlank()) {
            return UUID.randomUUID().toString();
        }
        try {
            UUID uuid = UUID.fromString(correlationId);
            if (uuid.toString().equalsIgnoreCase(correlationId)) {
                return correlationId;
            }
        } catch (IllegalArgumentException exception) {
            return UUID.randomUUID().toString();
        }
        return UUID.randomUUID().toString();
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
