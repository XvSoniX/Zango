package ir.nextminds.auth.observability;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.UUID;

@Slf4j
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class CorrelationIdFilter extends OncePerRequestFilter {

    static final String HEADER = "X-Correlation-ID";
    public static final String ATTRIBUTE = CorrelationIdFilter.class.getName() + ".id";

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain
    ) throws ServletException, IOException {
        String correlationId = correlationId(request.getHeader(HEADER));
        request.setAttribute(ATTRIBUTE, correlationId);
        response.setHeader(HEADER, correlationId);
        MDC.put("correlationId", correlationId);
        try {
            filterChain.doFilter(request, response);
        } finally {
            if (!request.getRequestURI().startsWith("/actuator")) {
                log.info(
                        "Request completed: correlationId={}, method={}, path={}, status={}",
                        correlationId,
                        request.getMethod(),
                        request.getRequestURI(),
                        response.getStatus()
                );
            }
            MDC.remove("correlationId");
        }
    }

    private static String correlationId(String header) {
        if (header == null || header.isBlank()) {
            return UUID.randomUUID().toString();
        }
        try {
            UUID parsed = UUID.fromString(header);
            if (parsed.toString().equalsIgnoreCase(header)) {
                return header;
            }
        } catch (IllegalArgumentException ignored) {
            // Replace a malformed id so logs stay attributable.
        }
        return UUID.randomUUID().toString();
    }
}
