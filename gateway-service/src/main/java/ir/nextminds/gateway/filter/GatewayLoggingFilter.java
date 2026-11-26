package ir.nextminds.gateway.filter;

import ir.nextminds.gateway.constant.GatewayHeaders;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.HttpStatusCode;
import org.springframework.stereotype.Component;
import org.slf4j.MDC;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.time.Duration;

@Slf4j
@Component
public class GatewayLoggingFilter implements GlobalFilter, Ordered {

    @Override
    public Mono<Void> filter(
            ServerWebExchange exchange,
            GatewayFilterChain chain
    ) {

        String correlationId = exchange.getRequest()
                .getHeaders()
                .getFirst(GatewayHeaders.CORRELATION_ID);

        String method = exchange.getRequest().getMethod().name();
        String path = exchange.getRequest().getURI().getPath();

        long startTime = System.nanoTime();

        withCorrelation(correlationId, () -> log.info(
                "Incoming request: correlationId={}, method={}, path={}",
                correlationId,
                method,
                path
        ));

        return chain.filter(exchange)
                .doFinally(signalType -> {

                    long duration = Duration.ofNanos(
                            System.nanoTime() - startTime
                    ).toMillis();

                    HttpStatusCode status = exchange.getResponse().getStatusCode();

                    withCorrelation(correlationId, () -> log.info(
                            "Outgoing response: correlationId={}, method={}, path={}, status={}, duration={}ms, signal={}",
                            correlationId,
                            method,
                            path,
                            status != null ? status.value() : "UNKNOWN",
                            duration,
                            signalType
                    ));
                });
    }

    private static void withCorrelation(String correlationId, Runnable action) {
        if (correlationId != null) {
            MDC.put("correlationId", correlationId);
        }
        try {
            action.run();
        } finally {
            MDC.remove("correlationId");
        }
    }

    @Override
    public int getOrder() {
        return Ordered.LOWEST_PRECEDENCE;
    }
}