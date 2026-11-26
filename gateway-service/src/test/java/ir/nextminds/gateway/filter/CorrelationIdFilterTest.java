package ir.nextminds.gateway.filter;

import ir.nextminds.gateway.constant.GatewayHeaders;
import org.junit.jupiter.api.Test;
import org.springframework.core.Ordered;
import org.springframework.mock.http.server.reactive.MockServerHttpRequest;
import org.springframework.mock.web.server.MockServerWebExchange;
import org.springframework.web.server.ServerWebExchange;
import org.springframework.web.server.WebFilterChain;
import reactor.core.publisher.Mono;

import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;

class CorrelationIdFilterTest {

    private static final int SPRING_SECURITY_WEB_FILTER_CHAIN_ORDER = -100;

    private final CorrelationIdFilter filter = new CorrelationIdFilter();

    @Test
    void runsStrictlyBeforeSpringSecurityWebFilterChain() {
        assertThat(filter.getOrder()).isEqualTo(Ordered.HIGHEST_PRECEDENCE);
        assertThat(filter.getOrder()).isLessThan(SPRING_SECURITY_WEB_FILTER_CHAIN_ORDER);
    }

    @Test
    void generatesCanonicalUuidWhenIncomingHeaderIsMissing() {
        MockServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.get("/api/v1/users/me").build()
        );

        AtomicReference<ServerWebExchange> downstreamExchange = new AtomicReference<>();
        WebFilterChain chain = ex -> {
            downstreamExchange.set(ex);
            return ex.getResponse().setComplete();
        };

        filter.filter(exchange, chain).block();

        String attributeId = downstreamExchange.get().getAttribute(GatewayHeaders.CORRELATION_ID_ATTRIBUTE);
        String requestId = downstreamExchange.get().getRequest().getHeaders().getFirst(GatewayHeaders.CORRELATION_ID);
        String responseId = downstreamExchange.get().getResponse().getHeaders().getFirst(GatewayHeaders.CORRELATION_ID);

        assertThat(attributeId).isNotBlank();
        assertThat(UUID.fromString(attributeId).toString()).isEqualToIgnoringCase(attributeId);
        assertThat(requestId).isEqualTo(attributeId);
        assertThat(responseId).isEqualTo(attributeId);
    }

    @Test
    void preservesValidIncomingUuid() {
        String validUuid = "550e8400-e29b-41d4-a716-446655440000";
        MockServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.get("/api/v1/users/me")
                        .header(GatewayHeaders.CORRELATION_ID, validUuid)
                        .build()
        );

        AtomicReference<ServerWebExchange> downstreamExchange = new AtomicReference<>();
        filter.filter(exchange, ex -> {
            downstreamExchange.set(ex);
            return ex.getResponse().setComplete();
        }).block();

        assertThat(downstreamExchange.get().<String>getAttribute(GatewayHeaders.CORRELATION_ID_ATTRIBUTE))
                .isEqualTo(validUuid);
        assertThat(downstreamExchange.get().getRequest().getHeaders().getFirst(GatewayHeaders.CORRELATION_ID))
                .isEqualTo(validUuid);
        assertThat(downstreamExchange.get().getResponse().getHeaders().getFirst(GatewayHeaders.CORRELATION_ID))
                .isEqualTo(validUuid);
    }

    @Test
    void replacesInvalidOrInjectionAttemptHeaderWithFreshUuid() {
        String maliciousHeader = "550e8400-e29b-41d4-a716-446655440000\r\nX-Injected: evil";
        MockServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.get("/api/v1/users/me")
                        .header(GatewayHeaders.CORRELATION_ID, maliciousHeader)
                        .build()
        );

        AtomicReference<ServerWebExchange> downstreamExchange = new AtomicReference<>();
        filter.filter(exchange, ex -> {
            downstreamExchange.set(ex);
            return ex.getResponse().setComplete();
        }).block();

        String resolved = downstreamExchange.get().getResponse().getHeaders().getFirst(GatewayHeaders.CORRELATION_ID);
        assertThat(resolved).isNotNull();
        assertThat(resolved).doesNotContain("\r").doesNotContain("\n").doesNotContain("X-Injected");
        assertThat(UUID.fromString(resolved).toString()).isEqualToIgnoringCase(resolved);
        assertThat(downstreamExchange.get().getRequest().getHeaders().getFirst(GatewayHeaders.CORRELATION_ID))
                .isEqualTo(resolved);
    }

    @Test
    void beforeCommitPreventsDownstreamOverwriteOfResponseHeader() {
        String canonicalId = "11111111-2222-4333-8444-555555555555";
        MockServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.get("/api/v1/assessments/start")
                        .header(GatewayHeaders.CORRELATION_ID, canonicalId)
                        .build()
        );

        filter.filter(exchange, ex -> {
            ex.getResponse().getHeaders().add(GatewayHeaders.CORRELATION_ID, "99999999-9999-4999-8999-999999999999");
            return ex.getResponse().setComplete();
        }).block();

        assertThat(exchange.getResponse().getHeaders().get(GatewayHeaders.CORRELATION_ID))
                .containsExactly(canonicalId);
    }
}
