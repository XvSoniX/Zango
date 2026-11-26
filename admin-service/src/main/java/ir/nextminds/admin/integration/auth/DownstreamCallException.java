package ir.nextminds.admin.integration.auth;

import ir.nextminds.admin.exception.AdminExceptionHandler;
import org.springframework.http.HttpStatusCode;

import java.util.List;

public class DownstreamCallException extends RuntimeException {

    public enum Kind {
        REJECTED,
        UNAVAILABLE,
        UNKNOWN
    }

    private final Kind kind;
    private final String failureType;
    private final HttpStatusCode status;
    private final String type;
    private final String title;
    private final String detail;
    private final String errorCode;
    private final List<AdminExceptionHandler.FieldErrorDetailDTO> errors;

    private DownstreamCallException(
            Kind kind,
            String failureType,
            HttpStatusCode status,
            String type,
            String title,
            String detail,
            String errorCode,
            List<AdminExceptionHandler.FieldErrorDetailDTO> errors
    ) {
        super(kind.name());
        this.kind = kind;
        this.failureType = failureType;
        this.status = status;
        this.type = type;
        this.title = title;
        this.detail = detail;
        this.errorCode = errorCode;
        this.errors = errors == null ? List.of() : List.copyOf(errors);
    }

    public static DownstreamCallException unavailable(String failureType) {
        return new DownstreamCallException(Kind.UNAVAILABLE, failureType, null, null, null, null, null, List.of());
    }

    public static DownstreamCallException unknown(String failureType) {
        return new DownstreamCallException(Kind.UNKNOWN, failureType, null, null, null, null, null, List.of());
    }

    public static DownstreamCallException rejected(
            HttpStatusCode status,
            String type,
            String title,
            String detail,
            String errorCode,
            List<AdminExceptionHandler.FieldErrorDetailDTO> errors
    ) {
        return new DownstreamCallException(
                Kind.REJECTED,
                null,
                status,
                type,
                title,
                detail == null ? "" : detail,
                errorCode,
                errors
        );
    }

    public Kind kind() {
        return kind;
    }

    public String failureType() {
        return failureType;
    }

    public HttpStatusCode status() {
        return status;
    }

    public String type() {
        return type;
    }

    public String title() {
        return title;
    }

    public String detail() {
        return detail;
    }

    public String errorCode() {
        return errorCode;
    }

    public List<AdminExceptionHandler.FieldErrorDetailDTO> errors() {
        return errors;
    }
}
