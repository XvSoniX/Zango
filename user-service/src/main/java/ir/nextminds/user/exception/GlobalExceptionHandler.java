package ir.nextminds.user.exception;

import jakarta.servlet.http.HttpServletRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.ProblemDetail;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;

import java.net.URI;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);
    private static final String CORRELATION_ID_HEADER = "X-Correlation-ID";
    private static final String PROBLEM_TYPE_PREFIX = "https://api.nextminds.ir/problems/";

    @ExceptionHandler(ResourceNotFoundException.class)
    public ProblemDetail handleNotFound(ResourceNotFoundException ex, HttpServletRequest request) {
        return createProblem(HttpStatus.NOT_FOUND, "Not Found", ex.getMessage(), "USER_NOT_FOUND", request, null);
    }

    @ExceptionHandler(DuplicateResourceException.class)
    public ProblemDetail handleConflict(DuplicateResourceException ex, HttpServletRequest request) {
        return createProblem(HttpStatus.CONFLICT, "Conflict", ex.getMessage(), "USER_ALREADY_EXISTS", request, null);
    }

    @ExceptionHandler(BusinessRuleException.class)
    public ProblemDetail handleBusinessRule(BusinessRuleException ex, HttpServletRequest request) {
        return createProblem(HttpStatusCode.valueOf(422), "Unprocessable Content", ex.getMessage(), "AGE_OUT_OF_RANGE", request, null);
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ProblemDetail handleValidation(MethodArgumentNotValidException ex, HttpServletRequest request) {
        Map<String, String> fieldErrors = new LinkedHashMap<>();
        for (FieldError error : ex.getBindingResult().getFieldErrors()) {
            fieldErrors.putIfAbsent(error.getField(), error.getDefaultMessage());
        }
        return createProblem(HttpStatus.BAD_REQUEST, "Bad Request", "Validation failed", "VALIDATION_FAILED", request, fieldErrors);
    }

    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    public ProblemDetail handleTypeMismatch(MethodArgumentTypeMismatchException ex, HttpServletRequest request) {
        String detail = "Invalid value for parameter '" + ex.getName() + "'";
        return createProblem(HttpStatus.BAD_REQUEST, "Bad Request", detail, "INVALID_ARGUMENT", request, null);
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ProblemDetail handleUnreadableMessage(HttpMessageNotReadableException ex, HttpServletRequest request) {
        return createProblem(HttpStatus.BAD_REQUEST, "Bad Request", "Malformed JSON request body", "MALFORMED_JSON", request, null);
    }

    @ExceptionHandler(Exception.class)
    public ProblemDetail handleUnexpected(Exception ex, HttpServletRequest request) {
        log.error("Unexpected error while processing request path={}", request.getRequestURI(), ex);
        return createProblem(HttpStatus.INTERNAL_SERVER_ERROR, "Internal Server Error", "An unexpected error occurred", "INTERNAL_SERVER_ERROR", request, null);
    }

    private ProblemDetail createProblem(
            HttpStatusCode status,
            String title,
            String detail,
            String errorCode,
            HttpServletRequest request,
            Map<String, String> errors
    ) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(status, detail);
        problem.setType(URI.create(PROBLEM_TYPE_PREFIX + errorCode.toLowerCase().replace('_', '-')));
        problem.setTitle(title);
        problem.setInstance(URI.create(request.getRequestURI()));
        problem.setProperty("isSuccess", false);
        problem.setProperty("errorCode", errorCode);
        problem.setProperty("correlationId", resolveCorrelationId(request));
        if (errors != null && !errors.isEmpty()) {
            problem.setProperty("errors", errors);
        }
        return problem;
    }

    private String resolveCorrelationId(HttpServletRequest request) {
        String mdcId = MDC.get("correlationId");
        if (mdcId != null && !mdcId.isBlank()) {
            return mdcId;
        }
        String headerId = request.getHeader(CORRELATION_ID_HEADER);
        if (headerId != null && !headerId.isBlank()) {
            return headerId;
        }
        return UUID.randomUUID().toString();
    }
}
