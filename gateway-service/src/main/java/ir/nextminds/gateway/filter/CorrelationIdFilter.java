package ir.nextminds.gateway.filter;

import ir.nextminds.gateway.constant.GatewayHeaders;
import org.springframework.core.Ordered;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import org.springframework.web.server.WebFilter;
import org.springframework.web.server.WebFilterChain;
import reactor.core.publisher.Mono;

import java.util.UUID;

@Component
public class CorrelationIdFilter implements WebFilter, Ordered {

    public static final String ATTRIBUTE = CorrelationIdFilter.class.getName() + ".id";

    @Override
    public Mono<Void> filter(
            ServerWebExchange exchange,
            WebFilterChain chain
    ) {

        String correlationId = resolveCorrelationId(exchange);
        exchange.getAttributes().put(ATTRIBUTE, correlationId);

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
        return Ordered.HIGHEST_PRECEDENCE;
    }
}
