package ir.zango.gateway.controller;

import ir.zango.gateway.exception.GatewayErrorWriter;
import ir.zango.gateway.exception.enums.GatewayErrorCode;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

@Slf4j
@RestController
@RequiredArgsConstructor
public class FallbackController {

    private final GatewayErrorWriter errorWriter;

    @RequestMapping("/fallback")
    public Mono<Void> fallback(ServerWebExchange exchange) {

        log.warn(
                "Circuit Breaker fallback triggered. Path: {}",
                exchange.getRequest().getPath()
        );

        return errorWriter.write(
                exchange,
                GatewayErrorCode.SERVICE_UNAVAILABLE
        );
    }
}