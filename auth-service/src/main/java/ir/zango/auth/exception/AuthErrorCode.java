package ir.zango.auth.exception;

import lombok.Getter;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;

@Getter
@RequiredArgsConstructor
public enum AuthErrorCode {

    BAD_REQUEST(
            HttpStatus.BAD_REQUEST,
            "https://zango.ir/problems/bad-request"
    ),

    IDENTIFIER_CONFLICT(
            HttpStatus.CONFLICT,
            "https://zango.ir/problems/identifier-conflict"
    ),

    INTERNAL_SERVER_ERROR(
            HttpStatus.INTERNAL_SERVER_ERROR,
            "https://zango.ir/problems/internal-server-error"
    );

    private final HttpStatus status;
    private final String type;
}
