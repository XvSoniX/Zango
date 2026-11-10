package ir.zango.gateway.exception.enums;

import org.springframework.http.HttpStatus;

import lombok.Getter;
import lombok.RequiredArgsConstructor;

@Getter
@RequiredArgsConstructor
public enum GatewayErrorCode {

    BAD_REQUEST(
            HttpStatus.BAD_REQUEST,
            "https://zango.ir/problems/bad-request"
    ),

    UNAUTHORIZED(
            HttpStatus.UNAUTHORIZED,
            "https://zango.ir/problems/unauthorized"
    ),

    FORBIDDEN(
            HttpStatus.FORBIDDEN,
            "https://zango.ir/problems/forbidden"
    ),

    ROUTE_NOT_FOUND(
            HttpStatus.NOT_FOUND,
            "https://zango.ir/problems/route-not-found"
    ),

    BAD_GATEWAY(
            HttpStatus.BAD_GATEWAY,
            "https://zango.ir/problems/bad-gateway"
    ),

    SERVICE_UNAVAILABLE(
            HttpStatus.SERVICE_UNAVAILABLE,
            "https://zango.ir/problems/service-unavailable"
    ),

    GATEWAY_TIMEOUT(
            HttpStatus.GATEWAY_TIMEOUT,
            "https://zango.ir/problems/gateway-timeout"
    ),

    INTERNAL_SERVER_ERROR(
            HttpStatus.INTERNAL_SERVER_ERROR,
            "https://zango.ir/problems/internal-server-error"
    );

    private final HttpStatus status;
    private final String type;
}