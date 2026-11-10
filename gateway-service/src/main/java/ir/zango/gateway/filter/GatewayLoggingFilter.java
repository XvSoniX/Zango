package ir.zango.gateway.filter;

import ir.zango.gateway.constant.GatewayHeaders;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.HttpStatusCode;
import org.springframework.stereotype.Component;
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

        log.info(
                "Incoming request: correlationId={}, method={}, path={}",
                correlationId,
                method,
                path
        );

        return chain.filter(exchange)
                .doFinally(signalType -> {

                    long duration = Duration.ofNanos(
                            System.nanoTime() - startTime
                    ).toMillis();

                    HttpStatusCode status = exchange.getResponse().getStatusCode();

                    log.info(
                            "Outgoing response: correlationId={}, method={}, path={}, status={}, duration={}ms, signal={}",
                            correlationId,
                            method,
                            path,
                            status != null ? status.value() : "UNKNOWN",
                            duration,
                            signalType
                    );
                });
    }

    @Override
    public int getOrder() {
        return Ordered.LOWEST_PRECEDENCE;
    }
}