package ir.nextminds.admin.exception;

import lombok.Getter;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;

@Getter
@RequiredArgsConstructor
public enum AdminErrorCode {

    BAD_REQUEST(
            HttpStatus.BAD_REQUEST,
            "http://localhost/problems/bad-request"
    ),

    UNAUTHORIZED(
            HttpStatus.UNAUTHORIZED,
            "http://localhost/problems/unauthorized"
    ),

    FORBIDDEN(
            HttpStatus.FORBIDDEN,
            "http://localhost/problems/forbidden"
    ),

    NOT_FOUND(
            HttpStatus.NOT_FOUND,
            "http://localhost/problems/not-found"
    ),

    DOWNSTREAM_UNAVAILABLE(
            HttpStatus.SERVICE_UNAVAILABLE,
            "http://localhost/problems/downstream-unavailable"
    ),

    DOWNSTREAM_OUTCOME_UNKNOWN(
            HttpStatus.GATEWAY_TIMEOUT,
            "http://localhost/problems/downstream-outcome-unknown"
    ),

    INTERNAL_SERVER_ERROR(
            HttpStatus.INTERNAL_SERVER_ERROR,
            "http://localhost/problems/internal-server-error"
    );

    private final HttpStatus status;
    private final String type;
}
