package ir.zango.gateway.exception.enums;

import org.springframework.http.HttpStatus;

import lombok.Getter;
import lombok.RequiredArgsConstructor;

@Getter
@RequiredArgsConstructor
public enum GatewayErrorCode {

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

    ROUTE_NOT_FOUND(
            HttpStatus.NOT_FOUND,
            "http://localhost/problems/route-not-found"
    ),

    BAD_GATEWAY(
            HttpStatus.BAD_GATEWAY,
            "http://localhost/problems/bad-gateway"
    ),

    SERVICE_UNAVAILABLE(
            HttpStatus.SERVICE_UNAVAILABLE,
            "http://localhost/problems/service-unavailable"
    ),

    GATEWAY_TIMEOUT(
            HttpStatus.GATEWAY_TIMEOUT,
            "http://localhost/problems/gateway-timeout"
    ),

    INTERNAL_SERVER_ERROR(
            HttpStatus.INTERNAL_SERVER_ERROR,
            "http://localhost/problems/internal-server-error"
    );

    private final HttpStatus status;
    private final String type;
}