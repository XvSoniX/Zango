package ir.nextminds.gateway;

import com.fasterxml.jackson.databind.ObjectMapper;
import ir.nextminds.gateway.exception.GatewayErrorWriter;
import ir.nextminds.gateway.exception.enums.GatewayErrorCode;
import ir.nextminds.gateway.filter.CorrelationIdFilter;
import org.junit.jupiter.api.Test;
import org.springframework.context.support.StaticMessageSource;
import org.springframework.mock.http.server.reactive.MockServerHttpRequest;
import org.springframework.mock.web.server.MockServerWebExchange;

import java.util.Locale;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class CorrelationIdTest {
    @Test
    void securityErrorsUseTheEstablishedCorrelationId() {
        for (GatewayErrorCode code : new GatewayErrorCode[]{GatewayErrorCode.UNAUTHORIZED, GatewayErrorCode.FORBIDDEN}) {
            for (String supplied : new String[]{UUID.randomUUID().toString(), "invalid", ""}) {
                var exchange = MockServerWebExchange.from(MockServerHttpRequest.get("/api/v1/admin/roles")
                        .header("X-Correlation-ID", supplied).header("Accept-Language", "en"));
                StaticMessageSource messages = new StaticMessageSource();
                messages.addMessage("error." + code.name() + ".title", Locale.ENGLISH, "error");
                messages.addMessage("error." + code.name() + ".detail", Locale.ENGLISH, "error");
                GatewayErrorWriter writer = new GatewayErrorWriter(new ObjectMapper(), messages);
                new CorrelationIdFilter().filter(exchange, filtered -> writer.write(filtered, code)).block();
                String id = exchange.getResponse().getHeaders().getFirst("X-Correlation-ID");
                assertEquals(id, UUID.fromString(id).toString());
                if (!supplied.isEmpty() && !supplied.equals("invalid")) assertEquals(supplied, id);
                assertTrue(exchange.getResponse().getBodyAsString().block().contains(id));
                assertEquals(code.getStatus(), exchange.getResponse().getStatusCode());
            }
        }
    }
}
