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

/**
 * Establishes and propagates a canonical UUID {@code X-Correlation-ID} before Spring Security runs.
 */
@Component
public class CorrelationIdFilter implements WebFilter, Ordered {

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, WebFilterChain chain) {
        String correlationId = resolveOrGenerate(
                exchange.getRequest().getHeaders().getFirst(GatewayHeaders.CORRELATION_ID)
        );

        ServerHttpRequest mutatedRequest = exchange.getRequest()
                .mutate()
                .headers(headers -> headers.set(GatewayHeaders.CORRELATION_ID, correlationId))
                .build();

        ServerWebExchange mutatedExchange = exchange.mutate()
                .request(mutatedRequest)
                .build();

        mutatedExchange.getAttributes().put(GatewayHeaders.CORRELATION_ID_ATTRIBUTE, correlationId);
        mutatedExchange.getResponse().getHeaders().set(GatewayHeaders.CORRELATION_ID, correlationId);
        // Re-assert canonical ID before headers flush so downstream services cannot overwrite or strip it.
        mutatedExchange.getResponse().beforeCommit(() -> {
            mutatedExchange.getResponse().getHeaders().set(GatewayHeaders.CORRELATION_ID, correlationId);
            return Mono.empty();
        });

        return chain.filter(mutatedExchange);
    }

    public static String resolveOrGenerate(String candidate) {
        String valid = normalizeValidUuid(candidate);
        return valid != null ? valid : UUID.randomUUID().toString();
    }

    public static String normalizeValidUuid(String candidate) {
        if (candidate == null || candidate.isBlank()) {
            return null;
        }
        try {
            UUID uuid = UUID.fromString(candidate);
            if (uuid.toString().equalsIgnoreCase(candidate)) {
                return candidate;
            }
        } catch (IllegalArgumentException ignored) {
            return null;
        }
        return null;
    }

    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE;
    }
}