package ir.nextminds.gateway.exception;

import ir.nextminds.gateway.constant.GatewayHeaders;
import ir.nextminds.gateway.exception.enums.GatewayErrorCode;
import org.junit.jupiter.api.Test;
import org.springframework.context.MessageSource;
import org.springframework.context.support.ReloadableResourceBundleMessageSource;
import org.springframework.context.support.StaticMessageSource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ProblemDetail;
import org.springframework.http.converter.json.ProblemDetailJacksonMixin;
import org.springframework.mock.http.server.reactive.MockServerHttpRequest;
import org.springframework.mock.web.server.MockServerWebExchange;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class GatewayErrorWriterTest {

    private final JsonMapper jsonMapper = JsonMapper.builder()
            .addMixIn(ProblemDetail.class, ProblemDetailJacksonMixin.class)
            .build();

    private static MessageSource gatewayMessageSource() {
        ReloadableResourceBundleMessageSource source = new ReloadableResourceBundleMessageSource();
        source.setBasename("classpath:i18n/message");
        source.setDefaultEncoding(StandardCharsets.UTF_8.name());
        source.setFallbackToSystemLocale(false);
        return source;
    }

    @Test
    void serializesProblemDetailWithJackson3AndCorrelationIdHeader() throws Exception {
        GatewayErrorWriter writer = new GatewayErrorWriter(jsonMapper, gatewayMessageSource());
        String expectedCorrelationId = UUID.randomUUID().toString();

        MockServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.get("/api/v1/admin/roles")
                        .header(HttpHeaders.ACCEPT_LANGUAGE, "en")
                        .build()
        );
        exchange.getAttributes().put(GatewayHeaders.CORRELATION_ID_ATTRIBUTE, expectedCorrelationId);

        writer.write(exchange, GatewayErrorCode.FORBIDDEN).block();

        assertThat(exchange.getResponse().getStatusCode().value()).isEqualTo(403);
        assertThat(exchange.getResponse().getHeaders().getContentType())
                .isEqualTo(MediaType.APPLICATION_PROBLEM_JSON);
        assertThat(exchange.getResponse().getHeaders().getFirst(GatewayHeaders.CORRELATION_ID))
                .isEqualTo(expectedCorrelationId);

        String body = exchange.getResponse().getBodyAsString().block();
        JsonNode json = jsonMapper.readTree(body);

        assertThat(json.get("type").asString()).isEqualTo("http://localhost/problems/forbidden");
        assertThat(json.get("title").asString()).isEqualTo("Forbidden");
        assertThat(json.get("status").asInt()).isEqualTo(403);
        assertThat(json.get("detail").asString()).isEqualTo("You do not have permission to access this resource.");
        assertThat(json.get("instance").asString()).isEqualTo("/api/v1/admin/roles");
        assertThat(json.get("isSuccess").asBoolean()).isFalse();
        assertThat(json.get("errorCode").asString()).isEqualTo("FORBIDDEN");
        assertThat(json.get("correlationId").asString()).isEqualTo(expectedCorrelationId);
        assertThat(json.has("properties")).isFalse();
    }

    @Test
    void defaultsToPersianAndFallsBackOnUnsupportedOrMalformedAcceptLanguage() throws Exception {
        GatewayErrorWriter writer = new GatewayErrorWriter(jsonMapper, gatewayMessageSource());

        MockServerWebExchange noLocaleExchange = MockServerWebExchange.from(
                MockServerHttpRequest.get("/api/v1/users/1").build()
        );
        writer.write(noLocaleExchange, GatewayErrorCode.UNAUTHORIZED).block();
        JsonNode defaultJson = jsonMapper.readTree(noLocaleExchange.getResponse().getBodyAsString().block());
        assertThat(defaultJson.get("title").asString()).isEqualTo("\u0627\u062D\u0631\u0627\u0632 \u0647\u0648\u06CC\u062A \u0646\u0627\u0645\u0648\u0641\u0642");

        MockServerWebExchange unsupportedExchange = MockServerWebExchange.from(
                MockServerHttpRequest.get("/api/v1/users/1")
                        .header(HttpHeaders.ACCEPT_LANGUAGE, "fr-FR,de;q=0.8")
                        .build()
        );
        writer.write(unsupportedExchange, GatewayErrorCode.UNAUTHORIZED).block();
        JsonNode unsupportedJson = jsonMapper.readTree(unsupportedExchange.getResponse().getBodyAsString().block());
        assertThat(unsupportedJson.get("title").asString()).isEqualTo(defaultJson.get("title").asString());

        MockServerWebExchange malformedExchange = MockServerWebExchange.from(
                MockServerHttpRequest.get("/api/v1/users/1")
                        .header(HttpHeaders.ACCEPT_LANGUAGE, ";;;invalid-locale;;;")
                        .build()
        );
        writer.write(malformedExchange, GatewayErrorCode.UNAUTHORIZED).block();
        JsonNode malformedJson = jsonMapper.readTree(malformedExchange.getResponse().getBodyAsString().block());
        assertThat(malformedJson.get("title").asString()).isEqualTo(defaultJson.get("title").asString());
    }

    @Test
    void fallsBackGracefullyWhenMessageKeysOrTranslationsAreMissing() throws Exception {
        StaticMessageSource emptySource = new StaticMessageSource();
        GatewayErrorWriter writer = new GatewayErrorWriter(jsonMapper, emptySource);

        MockServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.get("/api/v1/consulting/orgs")
                        .header(HttpHeaders.ACCEPT_LANGUAGE, "en")
                        .build()
        );

        writer.write(exchange, GatewayErrorCode.SERVICE_UNAVAILABLE).block();

        assertThat(exchange.getResponse().getStatusCode().value()).isEqualTo(503);
        JsonNode json = jsonMapper.readTree(exchange.getResponse().getBodyAsString().block());
        assertThat(json.get("title").asString()).isEqualTo("Service Unavailable");
        assertThat(json.get("detail").asString()).isEqualTo("SERVICE_UNAVAILABLE");
        assertThat(json.get("errorCode").asString()).isEqualTo("SERVICE_UNAVAILABLE");
        assertThat(UUID.fromString(json.get("correlationId").asString())).isNotNull();
        assertThat(exchange.getResponse().getHeaders().getFirst(GatewayHeaders.CORRELATION_ID))
                .isEqualTo(json.get("correlationId").asString());
    }

    @Test
    void fallsBackWhenMessageSourceReturnsNull() throws Exception {
        MessageSource nullReturningSource = mock(MessageSource.class);
        when(nullReturningSource.getMessage(any(), any(), any(), any(Locale.class))).thenReturn(null);

        GatewayErrorWriter writer = new GatewayErrorWriter(jsonMapper, nullReturningSource);
        MockServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.get("/api/v1/assessments/start").build()
        );

        writer.write(exchange, GatewayErrorCode.BAD_REQUEST).block();

        JsonNode json = jsonMapper.readTree(exchange.getResponse().getBodyAsString().block());
        assertThat(json.get("title").asString()).isEqualTo("Bad Request");
        assertThat(json.get("detail").asString()).isEqualTo("BAD_REQUEST");
    }

    @Test
    void rejectsWritingWhenResponseAlreadyCommitted() {
        GatewayErrorWriter writer = new GatewayErrorWriter(jsonMapper, gatewayMessageSource());
        MockServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.get("/api/v1/users/me").build()
        );
        exchange.getResponse().setComplete().block();

        assertThatThrownBy(() -> writer.write(exchange, GatewayErrorCode.UNAUTHORIZED).block())
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("Response already committed");
    }
}
