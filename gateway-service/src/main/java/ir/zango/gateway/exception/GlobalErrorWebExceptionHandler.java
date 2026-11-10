package ir.zango.gateway.exception;

import ir.zango.gateway.exception.enums.GatewayErrorCode;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.webflux.error.ErrorWebExceptionHandler;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpStatusCode;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.net.ConnectException;
import java.net.UnknownHostException;
import java.util.concurrent.TimeoutException;

@Slf4j
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
@RequiredArgsConstructor
public class GlobalErrorWebExceptionHandler implements ErrorWebExceptionHandler {

    private final GatewayErrorWriter errorWriter;

    @Override
    public Mono<Void> handle(
            ServerWebExchange exchange,
            Throwable exception
    ) {

        if (exchange.getResponse().isCommitted()) {
            return Mono.error(exception);
        }

        GatewayErrorCode errorCode = resolveErrorCode(exception);

        log.error(
                "Gateway error occurred. Path: {}, ErrorCode: {}",
                exchange.getRequest().getPath(),
                errorCode,
                exception
        );

        return errorWriter.write(exchange, errorCode);
    }

    private GatewayErrorCode resolveErrorCode(Throwable exception) {

        Throwable cause = exception;

        while (cause != null) {

            if (cause instanceof ResponseStatusException responseException) {
                return resolveStatus(responseException.getStatusCode());
            }

            if (cause instanceof TimeoutException) {
                return GatewayErrorCode.GATEWAY_TIMEOUT;
            }

            if (cause instanceof ConnectException
                    || cause instanceof UnknownHostException) {
                return GatewayErrorCode.SERVICE_UNAVAILABLE;
            }

            cause = cause.getCause();
        }

        return GatewayErrorCode.INTERNAL_SERVER_ERROR;
    }

    private GatewayErrorCode resolveStatus(HttpStatusCode status) {

        return switch (status.value()) {
            case 400 -> GatewayErrorCode.BAD_REQUEST;
            case 401 -> GatewayErrorCode.UNAUTHORIZED;
            case 403 -> GatewayErrorCode.FORBIDDEN;
            case 404 -> GatewayErrorCode.ROUTE_NOT_FOUND;
            case 502 -> GatewayErrorCode.BAD_GATEWAY;
            case 503 -> GatewayErrorCode.SERVICE_UNAVAILABLE;
            case 504 -> GatewayErrorCode.GATEWAY_TIMEOUT;
            default -> GatewayErrorCode.INTERNAL_SERVER_ERROR;
        };
    }
}