package ir.nextminds.user.filter;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.UUID;

@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class CorrelationIdFilter extends OncePerRequestFilter {

    public static final String CORRELATION_ID_HEADER = "X-Correlation-ID";
    private static final Logger log = LoggerFactory.getLogger(CorrelationIdFilter.class);

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain
    ) throws ServletException, IOException {
        String correlationId = resolveCorrelationId(request.getHeader(CORRELATION_ID_HEADER));
        response.setHeader(CORRELATION_ID_HEADER, correlationId);
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

    private static String resolveCorrelationId(String header) {
        if (header == null || header.isBlank()) {
            return UUID.randomUUID().toString();
        }
        try {
            UUID parsed = UUID.fromString(header.strip());
            if (parsed.toString().equalsIgnoreCase(header.strip())) {
                return parsed.toString();
            }
        } catch (IllegalArgumentException ignored) {
            // Replace malformed correlation ID with a valid UUID.
        }
        return UUID.randomUUID().toString();
    }
}
