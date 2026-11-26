package ir.nextminds.admin.integration;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

class CorrelationIdFilterTest {

    @Test
    void propagatesIncomingIdToRequestAndResponse() throws Exception {
        UUID correlationId = UUID.randomUUID();
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/v1/admin/roles");
        request.addHeader(CorrelationIdFilter.HEADER, correlationId.toString());
        MockHttpServletResponse response = new MockHttpServletResponse();

        new CorrelationIdFilter().doFilter(request, response, (incoming, outgoing) ->
                assertEquals(correlationId, incoming.getAttribute(CorrelationIdFilter.CORRELATION_ATTRIBUTE)));

        assertEquals(correlationId.toString(), response.getHeader(CorrelationIdFilter.HEADER));
    }

    @Test
    void generatesOneIdForInvalidInput() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/v1/admin/roles");
        request.addHeader(CorrelationIdFilter.HEADER, "invalid");
        MockHttpServletResponse response = new MockHttpServletResponse();

        new CorrelationIdFilter().doFilter(request, response, (incoming, outgoing) ->
                assertNotNull(incoming.getAttribute(CorrelationIdFilter.CORRELATION_ATTRIBUTE)));

        assertEquals(request.getAttribute(CorrelationIdFilter.CORRELATION_ATTRIBUTE).toString(),
                response.getHeader(CorrelationIdFilter.HEADER));
    }
}
