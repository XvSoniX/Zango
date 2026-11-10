package ir.zango.gateway.filter;

import ir.zango.gateway.constant.GatewayHeaders;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.util.UUID;

@Component
public class CorrelationIdFilter implements GlobalFilter, Ordered {

    @Override
    public Mono<Void> filter(
            ServerWebExchange exchange,
            GatewayFilterChain chain
    ) {

        String correlationId = resolveCorrelationId(exchange);

        ServerHttpRequest request = exchange.getRequest()
                .mutate()
                .headers(headers -> headers.set(
                        GatewayHeaders.CORRELATION_ID,
                        correlationId
                ))
                .build();

        exchange.getResponse().getHeaders().set(
                GatewayHeaders.CORRELATION_ID,
                correlationId
        );

        return chain.filter(
                exchange.mutate()
                        .request(request)
                        .build()
        );
    }

    private String resolveCorrelationId(ServerWebExchange exchange) {

        String correlationId = exchange.getRequest()
                .getHeaders()
                .getFirst(GatewayHeaders.CORRELATION_ID);

        if (correlationId != null) {
            try {
                UUID uuid = UUID.fromString(correlationId);

                if (uuid.toString().equalsIgnoreCase(correlationId)) {
                    return correlationId;
                }
            } catch (IllegalArgumentException ignored) {
                // Generate a new ID for invalid values.
            }
        }

        return UUID.randomUUID().toString();
    }

    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE + 10;
    }
}