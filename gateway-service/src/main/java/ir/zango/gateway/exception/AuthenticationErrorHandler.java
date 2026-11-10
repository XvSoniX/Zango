package ir.zango.gateway.exception;

import ir.zango.gateway.exception.enums.GatewayErrorCode;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.web.server.ServerAuthenticationEntryPoint;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

@Component
@RequiredArgsConstructor
public class AuthenticationErrorHandler implements ServerAuthenticationEntryPoint {

    private final GatewayErrorWriter errorWriter;

    @Override
    public Mono<Void> commence(
            ServerWebExchange exchange,
            AuthenticationException exception
    ) {
        return errorWriter.write(
                exchange,
                GatewayErrorCode.UNAUTHORIZED
        );
    }
}