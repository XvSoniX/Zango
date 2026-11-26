package ir.nextminds.gateway.exception;

import ir.nextminds.gateway.exception.enums.GatewayErrorCode;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpHeaders;
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
        exchange.getResponse().getHeaders().set(HttpHeaders.WWW_AUTHENTICATE, "Bearer");
        return errorWriter.write(
                exchange,
                GatewayErrorCode.UNAUTHORIZED
        );
    }
}