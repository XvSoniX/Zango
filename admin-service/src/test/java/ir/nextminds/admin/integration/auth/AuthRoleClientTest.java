package ir.nextminds.admin.integration.auth;

import ir.nextminds.admin.integration.DownstreamCaller;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;
import tools.jackson.databind.json.JsonMapper;

import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;

class AuthRoleClientTest {

    @Test
    void preservesFourHundredResponsesAndCorrelationId() {
        for (HttpStatus status : new HttpStatus[]{HttpStatus.UNAUTHORIZED, HttpStatus.FORBIDDEN,
                HttpStatus.NOT_FOUND, HttpStatus.CONFLICT}) {
            RestClient.Builder builder = RestClient.builder().baseUrl("http://auth");
            MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
            UUID correlationId = UUID.randomUUID();
            DownstreamCaller caller = new DownstreamCaller(UUID.randomUUID(), correlationId, "Bearer token", "en");
            server.expect(requestTo("http://auth/api/v1/auth/admin/roles"))
                    .andExpect(header("X-Correlation-ID", correlationId.toString()))
                    .andExpect(header("Authorization", "Bearer token"))
                    .andRespond(withStatus(status).contentType(MediaType.APPLICATION_JSON)
                            .body("{\"title\":\"Rejected\",\"detail\":\"Denied\",\"errorCode\":\"TEST\"}"));
            AuthRoleClient client = new AuthRoleClient(builder.build(), JsonMapper.builder().build());

            DownstreamCallException failure = assertThrows(DownstreamCallException.class, () -> client.listRoles(caller));
            assertEquals(DownstreamCallException.Kind.REJECTED, failure.kind());
            assertEquals(status, failure.status());
            assertEquals("TEST", failure.errorCode());
            server.verify();
        }
    }

    @Test
    void serverErrorHasUnknownOutcome() {
        RestClient.Builder builder = RestClient.builder().baseUrl("http://auth");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        server.expect(requestTo("http://auth/api/v1/auth/admin/roles"))
                .andRespond(withStatus(HttpStatus.INTERNAL_SERVER_ERROR));
        AuthRoleClient client = new AuthRoleClient(builder.build(), JsonMapper.builder().build());
        DownstreamCaller caller = new DownstreamCaller(UUID.randomUUID(), UUID.randomUUID(), null, null);

        DownstreamCallException failure = assertThrows(DownstreamCallException.class, () -> client.listRoles(caller));
        assertEquals(DownstreamCallException.Kind.UNKNOWN, failure.kind());
        assertEquals("AUTH_SERVER_ERROR", failure.failureType());
        server.verify();
    }

    @Test
    void missingServiceInstanceIsClassifiedBeforeSend() {
        RestClient client = RestClient.builder().baseUrl("http://auth")
                .requestInterceptor((request, body, execution) -> {
                    throw new IllegalStateException("No instances available for AUTH-SERVICE");
                }).build();
        AuthRoleClient auth = new AuthRoleClient(client, JsonMapper.builder().build());
        DownstreamCaller caller = new DownstreamCaller(UUID.randomUUID(), UUID.randomUUID(), null, null);

        DownstreamCallException failure = assertThrows(DownstreamCallException.class, () -> auth.listRoles(caller));
        assertEquals(DownstreamCallException.Kind.UNAVAILABLE, failure.kind());
        assertEquals("CONNECTION_FAILED", failure.failureType());
    }
}
