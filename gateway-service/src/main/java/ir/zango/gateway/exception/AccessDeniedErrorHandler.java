package ir.zango.gateway.exception;

import ir.zango.gateway.exception.enums.GatewayErrorCode;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.web.server.authorization.ServerAccessDeniedHandler;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

@Component
@RequiredArgsConstructor
public class AccessDeniedErrorHandler implements ServerAccessDeniedHandler {

    private final GatewayErrorWriter errorWriter;

    @Override
    public Mono<Void> handle(
            ServerWebExchange exchange,
            AccessDeniedException exception
    ) {
        return errorWriter.write(
                exchange,
                GatewayErrorCode.FORBIDDEN
        );
    }
}