package ir.nextminds.admin.integration;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpHeaders;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.util.UUID;

@Component
public class CallerContext {

    public DownstreamCaller current() {
        ServletRequestAttributes attributes = (ServletRequestAttributes) RequestContextHolder.currentRequestAttributes();
        HttpServletRequest request = attributes.getRequest();
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null || authentication.getName() == null) {
            throw new IllegalStateException("authenticated administrator is required");
        }
        Object correlation = request.getAttribute(CorrelationIdFilter.CORRELATION_ATTRIBUTE);
        UUID correlationId = correlation instanceof UUID uuid ? uuid : CorrelationIdFilter.resolve(null);
        return new DownstreamCaller(
                UUID.fromString(authentication.getName()),
                correlationId,
                request.getHeader(HttpHeaders.AUTHORIZATION),
                request.getHeader(HttpHeaders.ACCEPT_LANGUAGE)
        );
    }
}
