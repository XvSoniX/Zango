package ir.nextminds.user.filter;

import jakarta.servlet.FilterChain;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

class CorrelationIdFilterTest {

    private final CorrelationIdFilter filter = new CorrelationIdFilter();

    @Test
    void generatesCorrelationIdWhenHeaderMissing() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/v1/users");
        MockHttpServletResponse response = new MockHttpServletResponse();
        FilterChain chain = (req, res) -> assertThat(MDC.get("correlationId")).isNotBlank();

        filter.doFilter(request, response, chain);

        String header = response.getHeader(CorrelationIdFilter.CORRELATION_ID_HEADER);
        assertThat(header).isNotBlank();
        assertThat(UUID.fromString(header)).isNotNull();
        assertThat(MDC.get("correlationId")).isNull();
    }

    @Test
    void preservesValidIncomingCorrelationId() throws Exception {
        String validId = UUID.randomUUID().toString();
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/v1/users");
        request.addHeader(CorrelationIdFilter.CORRELATION_ID_HEADER, validId);
        MockHttpServletResponse response = new MockHttpServletResponse();
        FilterChain chain = (req, res) -> assertThat(MDC.get("correlationId")).isEqualTo(validId);

        filter.doFilter(request, response, chain);

        assertThat(response.getHeader(CorrelationIdFilter.CORRELATION_ID_HEADER)).isEqualTo(validId);
        assertThat(MDC.get("correlationId")).isNull();
    }

    @Test
    void replacesMalformedCorrelationIdWithFreshUuid() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/v1/users");
        request.addHeader(CorrelationIdFilter.CORRELATION_ID_HEADER, "invalid-correlation-id");
        MockHttpServletResponse response = new MockHttpServletResponse();
        FilterChain chain = (req, res) -> assertThat(MDC.get("correlationId")).isNotEqualTo("invalid-correlation-id");

        filter.doFilter(request, response, chain);

        String header = response.getHeader(CorrelationIdFilter.CORRELATION_ID_HEADER);
        assertThat(header).isNotEqualTo("invalid-correlation-id");
        assertThat(UUID.fromString(header)).isNotNull();
        assertThat(MDC.get("correlationId")).isNull();
    }
}
