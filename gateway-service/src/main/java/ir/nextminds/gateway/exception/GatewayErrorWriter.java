package ir.nextminds.gateway.exception;

import ir.nextminds.gateway.constant.GatewayHeaders;
import ir.nextminds.gateway.exception.enums.GatewayErrorCode;
import ir.nextminds.gateway.filter.CorrelationIdFilter;
import lombok.RequiredArgsConstructor;
import org.springframework.context.MessageSource;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ProblemDetail;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;
import tools.jackson.databind.json.JsonMapper;

import java.net.URI;
import java.util.List;
import java.util.Locale;
import java.util.UUID;

@Component
@RequiredArgsConstructor
public class GatewayErrorWriter {

    private static final Locale DEFAULT_LOCALE = Locale.forLanguageTag("fa");

    private final JsonMapper jsonMapper;
    private final MessageSource messageSource;

    public Mono<Void> write(
            ServerWebExchange exchange,
            GatewayErrorCode errorCode
    ) {
        if (exchange.getResponse().isCommitted()) {
            return Mono.error(
                    new IllegalStateException("Response already committed")
            );
        }

        Locale locale = resolveLocale(exchange);
        String code = errorCode.name();

        String title = resolveMessage(
                "error." + code + ".title",
                errorCode.getStatus().getReasonPhrase(),
                locale
        );

        String detail = resolveMessage(
                "error." + code + ".detail",
                code,
                locale
        );

        String correlationId = resolveCorrelationId(exchange);

        ProblemDetail problemDetail = ProblemDetail.forStatusAndDetail(
                errorCode.getStatus(),
                detail
        );

        problemDetail.setType(URI.create(errorCode.getType()));
        problemDetail.setTitle(title);
        problemDetail.setInstance(resolveInstance(exchange));

        problemDetail.setProperty("isSuccess", false);
        problemDetail.setProperty("errorCode", code);
        problemDetail.setProperty("correlationId", correlationId);

        try {
            byte[] responseBody = jsonMapper.writeValueAsBytes(problemDetail);

            exchange.getResponse().setStatusCode(errorCode.getStatus());
            exchange.getResponse().getHeaders()
                    .setContentType(MediaType.APPLICATION_PROBLEM_JSON);
            exchange.getResponse().getHeaders()
                    .set(GatewayHeaders.CORRELATION_ID, correlationId);

            DataBuffer buffer = exchange.getResponse()
                    .bufferFactory()
                    .wrap(responseBody);

            return exchange.getResponse().writeWith(Mono.just(buffer));
        } catch (Exception exception) {
            return Mono.error(exception);
        }
    }

    private String resolveMessage(String key, String fallback, Locale locale) {
        String resolved = messageSource.getMessage(key, null, fallback, locale);
        return resolved != null && !resolved.isBlank() ? resolved : fallback;
    }

    private String resolveCorrelationId(ServerWebExchange exchange) {
        Object attributeValue = exchange.getAttribute(GatewayHeaders.CORRELATION_ID_ATTRIBUTE);
        if (attributeValue instanceof String attrString) {
            String valid = CorrelationIdFilter.normalizeValidUuid(attrString);
            if (valid != null) {
                return valid;
            }
        }

        String responseHeader = CorrelationIdFilter.normalizeValidUuid(
                exchange.getResponse().getHeaders().getFirst(GatewayHeaders.CORRELATION_ID)
        );
        if (responseHeader != null) {
            return responseHeader;
        }

        String requestHeader = CorrelationIdFilter.normalizeValidUuid(
                exchange.getRequest().getHeaders().getFirst(GatewayHeaders.CORRELATION_ID)
        );
        if (requestHeader != null) {
            return requestHeader;
        }

        return UUID.randomUUID().toString();
    }

    private URI resolveInstance(ServerWebExchange exchange) {
        String path = exchange.getRequest().getPath().value();
        try {
            return URI.create(path);
        } catch (IllegalArgumentException exception) {
            String rawPath = exchange.getRequest().getURI().getRawPath();
            return URI.create(rawPath != null && !rawPath.isBlank() ? rawPath : "/");
        }
    }

    private Locale resolveLocale(ServerWebExchange exchange) {
        String acceptLanguage = exchange.getRequest()
                .getHeaders()
                .getFirst(HttpHeaders.ACCEPT_LANGUAGE);

        if (acceptLanguage == null || acceptLanguage.isBlank()) {
            return DEFAULT_LOCALE;
        }

        try {
            List<Locale.LanguageRange> ranges =
                    Locale.LanguageRange.parse(acceptLanguage);

            Locale matched = Locale.lookup(
                    ranges,
                    List.of(
                            DEFAULT_LOCALE,
                            Locale.ENGLISH
                    )
            );

            return matched != null ? matched : DEFAULT_LOCALE;
        } catch (IllegalArgumentException exception) {
            return DEFAULT_LOCALE;
        }
    }
}