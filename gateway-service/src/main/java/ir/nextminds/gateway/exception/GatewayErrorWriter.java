package ir.nextminds.gateway.exception;

import com.fasterxml.jackson.databind.ObjectMapper;
import ir.nextminds.gateway.exception.enums.GatewayErrorCode;
import ir.nextminds.gateway.constant.GatewayHeaders;
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

import java.net.URI;
import java.util.List;
import java.util.Locale;
import java.util.UUID;

@Component
@RequiredArgsConstructor
public class GatewayErrorWriter {

    private final ObjectMapper objectMapper;
    private final MessageSource messageSource;

    public Mono<Void> write(
            ServerWebExchange exchange,
            GatewayErrorCode errorCode
    ) {
        Locale locale = resolveLocale(exchange);

        String code = errorCode.name();

        String title = messageSource.getMessage(
                "error." + code + ".title",
                null,
                locale
        );

        String detail = messageSource.getMessage(
                "error." + code + ".detail",
                null,
                locale
        );

        ProblemDetail problemDetail = ProblemDetail.forStatusAndDetail(
                errorCode.getStatus(),
                detail
        );

        problemDetail.setType(URI.create(errorCode.getType()));
        problemDetail.setTitle(title);
        problemDetail.setInstance(
                URI.create(
                        exchange.getRequest().getPath().value()
                )
        );

        problemDetail.setProperty("isSuccess", false);
        problemDetail.setProperty("errorCode", code);
        String correlationId = exchange.getAttribute(CorrelationIdFilter.ATTRIBUTE);
        if (correlationId == null) {
            correlationId = UUID.randomUUID().toString();
            exchange.getAttributes().put(CorrelationIdFilter.ATTRIBUTE, correlationId);
        }
        exchange.getResponse().getHeaders().set(GatewayHeaders.CORRELATION_ID, correlationId);
        problemDetail.setProperty("correlationId", correlationId);

        if (exchange.getResponse().isCommitted()) {
            return Mono.error(
                    new IllegalStateException("Response already committed")
            );
        }

        try {
            byte[] responseBody = objectMapper.writeValueAsBytes(problemDetail);

            exchange.getResponse().setStatusCode(errorCode.getStatus());

            exchange.getResponse().getHeaders()
                    .setContentType(MediaType.APPLICATION_PROBLEM_JSON);

            DataBuffer buffer = exchange.getResponse()
                    .bufferFactory()
                    .wrap(responseBody);

            return exchange.getResponse().writeWith(Mono.just(buffer));

        } catch (Exception exception) {
            return Mono.error(exception);
        }
    }

    private Locale resolveLocale(
            ServerWebExchange exchange
    ) {
        String acceptLanguage = exchange.getRequest()
                .getHeaders()
                .getFirst(HttpHeaders.ACCEPT_LANGUAGE);

        if (acceptLanguage == null || acceptLanguage.isBlank()) {
            return Locale.forLanguageTag("fa");
        }

        try {
            List<Locale.LanguageRange> ranges =
                    Locale.LanguageRange.parse(acceptLanguage);

            Locale matched = Locale.lookup(
                    ranges,
                    List.of(
                            Locale.forLanguageTag("fa"),
                            Locale.ENGLISH
                    )
            );

            return matched != null
                    ? matched
                    : Locale.forLanguageTag("fa");
        } catch (IllegalArgumentException exception) {
            return Locale.forLanguageTag("fa");
        }
    }
}
