package ir.nextminds.admin.integration;

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

    public static final String HEADER = "X-Correlation-ID";
    public static final String CORRELATION_ATTRIBUTE = "ir.nextminds.admin.correlationId";

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain
    ) throws ServletException, IOException {
        UUID correlationId = resolve(request.getHeader(HEADER));
        request.setAttribute(CORRELATION_ATTRIBUTE, correlationId);
        response.setHeader(HEADER, correlationId.toString());
        MDC.put("correlationId", correlationId.toString());
        try {
            filterChain.doFilter(request, response);
        } finally {
            if (!request.getRequestURI().startsWith("/actuator")) {
                log.info("Request completed: correlationId={}, method={}, path={}, status={}",
                        correlationId, request.getMethod(), request.getRequestURI(), response.getStatus());
            }
            MDC.remove("correlationId");
        }
    }

    static UUID resolve(String header) {
        if (header == null || header.isBlank()) {
            return UUID.randomUUID();
        }
        try {
            UUID correlationId = UUID.fromString(header);
            if (correlationId.toString().equalsIgnoreCase(header)) {
                return correlationId;
            }
        } catch (IllegalArgumentException exception) {
            return UUID.randomUUID();
        }
        return UUID.randomUUID();
    }
}
