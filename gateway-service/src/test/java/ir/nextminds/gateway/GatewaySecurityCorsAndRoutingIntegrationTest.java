package ir.nextminds.gateway;

import com.sun.net.httpserver.HttpServer;
import ir.nextminds.gateway.constant.GatewayHeaders;
import ir.nextminds.gateway.filter.CorrelationIdFilter;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.context.ApplicationContext;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.security.web.server.WebFilterChainProxy;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.reactive.server.EntityExchangeResult;
import org.springframework.test.web.reactive.server.WebTestClient;
import org.springframework.web.server.WebFilter;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class GatewaySecurityCorsAndRoutingIntegrationTest extends GatewayTestSupport {

    private static final HttpServer DOWNSTREAM_SERVER = startDownstreamServer();
    private static final AtomicReference<String> LAST_DOWNSTREAM_PATH = new AtomicReference<>();
    private static final AtomicReference<String> LAST_DOWNSTREAM_CORRELATION_ID = new AtomicReference<>();
    private static final AtomicReference<String> FORCED_DOWNSTREAM_RESPONSE_CORRELATION_ID = new AtomicReference<>();
    private static final AtomicInteger FORCED_DOWNSTREAM_STATUS = new AtomicInteger(200);

    @LocalServerPort
    private int port;

    @Autowired
    private ApplicationContext applicationContext;

    @Autowired
    private JsonMapper jsonMapper;

    private WebTestClient webTestClient;

    @DynamicPropertySource
    static void registerDownstreamDiscovery(DynamicPropertyRegistry registry) {
        String baseUri = "http://127.0.0.1:" + DOWNSTREAM_SERVER.getAddress().getPort();
        registry.add("spring.cloud.discovery.client.simple.instances.AUTH-SERVICE[0].uri", () -> baseUri);
        registry.add("spring.cloud.discovery.client.simple.instances.USER-SERVICE[0].uri", () -> baseUri);
        registry.add("spring.cloud.discovery.client.simple.instances.ADMIN-SERVICE[0].uri", () -> baseUri);
        registry.add("spring.cloud.discovery.client.simple.instances.CONSULTING-SERVICE[0].uri", () -> baseUri);
        registry.add("spring.cloud.discovery.client.simple.instances.ASSESSMENT-SERVICE[0].uri", () -> baseUri);
    }

    @AfterAll
    static void stopDownstreamServer() {
        DOWNSTREAM_SERVER.stop(0);
    }

    @BeforeEach
    void setUp() {
        LAST_DOWNSTREAM_PATH.set(null);
        LAST_DOWNSTREAM_CORRELATION_ID.set(null);
        FORCED_DOWNSTREAM_RESPONSE_CORRELATION_ID.set(null);
        FORCED_DOWNSTREAM_STATUS.set(200);
        this.webTestClient = WebTestClient.bindToServer()
                .baseUrl("http://localhost:" + port)
                .build();
    }

    @Test
    void correlationIdWebFilterIsOrderedStrictlyBeforeSpringSecurityFilterChain() {
        List<WebFilter> orderedFilters = applicationContext.getBeanProvider(WebFilter.class)
                .orderedStream()
                .toList();

        int correlationIndex = -1;
        int securityIndex = -1;
        for (int index = 0; index < orderedFilters.size(); index++) {
            WebFilter webFilter = orderedFilters.get(index);
            if (webFilter instanceof CorrelationIdFilter) {
                correlationIndex = index;
            }
            if (webFilter instanceof WebFilterChainProxy) {
                securityIndex = index;
            }
        }

        assertThat(correlationIndex).isGreaterThanOrEqualTo(0);
        assertThat(securityIndex).isGreaterThan(correlationIndex);
    }

    @Test
    void preservesValidCorrelationIdAndSetsHeaderOn401And403And404And5xxAnd2xx() throws Exception {
        String userJwt = signJwt(UUID.randomUUID().toString(), List.of("ROLE_USER"));
        String adminJwt = signJwt(UUID.randomUUID().toString(), List.of("ROLE_ADMIN"));

        // 1. 401 Unauthorized (before routing, handled by Spring Security entry point)
        String id401 = "aaaaaaaa-1111-4111-8111-111111111111";
        EntityExchangeResult<byte[]> res401 = webTestClient.get()
                .uri("/api/v1/users/me")
                .header(GatewayHeaders.CORRELATION_ID, id401)
                .header(HttpHeaders.ACCEPT_LANGUAGE, "en")
                .exchange()
                .expectStatus().isUnauthorized()
                .expectHeader().contentType(MediaType.APPLICATION_PROBLEM_JSON)
                .expectHeader().valueEquals(HttpHeaders.WWW_AUTHENTICATE, "Bearer")
                .expectHeader().valueEquals(GatewayHeaders.CORRELATION_ID, id401)
                .expectBody().returnResult();
        assertProblemCorrelationId(res401, id401, "UNAUTHORIZED");

        // 2. 403 Forbidden (authenticated user without ROLE_ADMIN)
        String id403 = "bbbbbbbb-2222-4222-8222-222222222222";
        EntityExchangeResult<byte[]> res403 = webTestClient.get()
                .uri("/api/v1/admin/roles")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + userJwt)
                .header(GatewayHeaders.CORRELATION_ID, id403)
                .header(HttpHeaders.ACCEPT_LANGUAGE, "en")
                .exchange()
                .expectStatus().isForbidden()
                .expectHeader().contentType(MediaType.APPLICATION_PROBLEM_JSON)
                .expectHeader().valueEquals(GatewayHeaders.CORRELATION_ID, id403)
                .expectBody().returnResult();
        assertProblemCorrelationId(res403, id403, "FORBIDDEN");

        // 3. 404 Route Not Found (authenticated request to unmapped route)
        String id404 = "cccccccc-3333-4333-8333-333333333333";
        EntityExchangeResult<byte[]> res404 = webTestClient.get()
                .uri("/api/v1/unknown/resource")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + userJwt)
                .header(GatewayHeaders.CORRELATION_ID, id404)
                .exchange()
                .expectStatus().isNotFound()
                .expectHeader().contentType(MediaType.APPLICATION_PROBLEM_JSON)
                .expectHeader().valueEquals(GatewayHeaders.CORRELATION_ID, id404)
                .expectBody().returnResult();
        assertProblemCorrelationId(res404, id404, "ROUTE_NOT_FOUND");

        // 4. 2xx Proxied response where downstream attempts to overwrite X-Correlation-ID
        String id200 = "dddddddd-4444-4444-8444-444444444444";
        FORCED_DOWNSTREAM_RESPONSE_CORRELATION_ID.set("99999999-9999-4999-8999-999999999999");
        webTestClient.get()
                .uri("/api/v1/admin/roles")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + adminJwt)
                .header(GatewayHeaders.CORRELATION_ID, id200)
                .exchange()
                .expectStatus().isOk()
                .expectHeader().valueEquals(GatewayHeaders.CORRELATION_ID, id200);
        assertThat(LAST_DOWNSTREAM_CORRELATION_ID.get()).isEqualTo(id200);

        // 5. 5xx Downstream error preserves Gateway canonical X-Correlation-ID
        String id500 = "eeeeeeee-5555-4555-8555-555555555555";
        FORCED_DOWNSTREAM_STATUS.set(500);
        FORCED_DOWNSTREAM_RESPONSE_CORRELATION_ID.set("bad-downstream-id");
        webTestClient.get()
                .uri("/api/v1/users/123")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + userJwt)
                .header(GatewayHeaders.CORRELATION_ID, id500)
                .exchange()
                .expectStatus().is5xxServerError()
                .expectHeader().valueEquals(GatewayHeaders.CORRELATION_ID, id500);
    }

    @Test
    void replacesInvalidIncomingCorrelationIdOnSecurityRejectedRequests() throws Exception {
        EntityExchangeResult<byte[]> result = webTestClient.get()
                .uri("/api/v1/consulting/orgs")
                .header(GatewayHeaders.CORRELATION_ID, "not-a-valid-uuid")
                .exchange()
                .expectStatus().isUnauthorized()
                .expectBody().returnResult();

        String headerId = result.getResponseHeaders().getFirst(GatewayHeaders.CORRELATION_ID);
        assertThat(headerId).isNotBlank().isNotEqualTo("not-a-valid-uuid");
        assertThat(UUID.fromString(headerId).toString()).isEqualToIgnoringCase(headerId);
        assertProblemCorrelationId(result, headerId, "UNAUTHORIZED");
    }

    @Test
    void handlesCorsPreflightBeforeAuthenticationAndAddsCorsHeadersOn401And403() {
        String userJwt = signJwt(UUID.randomUUID().toString(), List.of("ROLE_USER"));

        // Valid preflight OPTIONS on protected route succeeds without Authorization token
        webTestClient.options()
                .uri("/api/v1/admin/roles")
                .header(HttpHeaders.ORIGIN, "http://localhost:3000")
                .header(HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD, "POST")
                .header(HttpHeaders.ACCESS_CONTROL_REQUEST_HEADERS, "Authorization, Content-Type, Accept-Language, X-Correlation-ID")
                .exchange()
                .expectStatus().isOk()
                .expectHeader().valueEquals(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN, "http://localhost:3000")
                .expectHeader().value(HttpHeaders.ACCESS_CONTROL_ALLOW_HEADERS, value -> {
                    assertThat(value).contains("Accept-Language");
                    assertThat(value).contains("X-Correlation-ID");
                    assertThat(value).contains("Authorization");
                })
                .expectHeader().doesNotExist(HttpHeaders.ACCESS_CONTROL_ALLOW_CREDENTIALS);

        // Disallowed origin preflight is rejected
        webTestClient.options()
                .uri("/api/v1/assessments/start")
                .header(HttpHeaders.ORIGIN, "https://evil.example.com")
                .header(HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD, "POST")
                .exchange()
                .expectStatus().isForbidden()
                .expectHeader().doesNotExist(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN);

        // 401 response includes CORS allow-origin header for allowed origin
        webTestClient.get()
                .uri("/api/v1/assessments/start")
                .header(HttpHeaders.ORIGIN, "http://localhost:3000")
                .exchange()
                .expectStatus().isUnauthorized()
                .expectHeader().valueEquals(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN, "http://localhost:3000");

        // 403 response includes CORS allow-origin header for allowed origin
        webTestClient.get()
                .uri("/api/v1/admin/roles")
                .header(HttpHeaders.ORIGIN, "http://localhost:3000")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + userJwt)
                .exchange()
                .expectStatus().isForbidden()
                .expectHeader().valueEquals(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN, "http://localhost:3000");
    }

    @Test
    void enforcesRoutesAndExplicitSecurityRulesAcrossAllServices() {
        String userJwt = signJwt(UUID.randomUUID().toString(), List.of("ROLE_USER"));
        String adminJwt = signJwt(UUID.randomUUID().toString(), List.of("ROLE_ADMIN"));

        // Public auth login route succeeds without token
        webTestClient.post()
                .uri("/api/v1/auth/login")
                .exchange()
                .expectStatus().isOk();
        assertThat(LAST_DOWNSTREAM_PATH.get()).isEqualTo("/api/v1/auth/login");

        // Users route: 401 without token, 200 with authenticated user
        webTestClient.get().uri("/api/v1/users/me").exchange().expectStatus().isUnauthorized();
        webTestClient.get()
                .uri("/api/v1/users/me")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + userJwt)
                .exchange()
                .expectStatus().isOk();
        assertThat(LAST_DOWNSTREAM_PATH.get()).isEqualTo("/api/v1/users/me");

        // Admin route: 401 without token, 403 with ROLE_USER, 200 with ROLE_ADMIN
        webTestClient.get().uri("/api/v1/admin/audit-logs").exchange().expectStatus().isUnauthorized();
        webTestClient.get()
                .uri("/api/v1/admin/audit-logs")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + userJwt)
                .exchange()
                .expectStatus().isForbidden();
        webTestClient.get()
                .uri("/api/v1/admin/audit-logs")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + adminJwt)
                .exchange()
                .expectStatus().isOk();
        assertThat(LAST_DOWNSTREAM_PATH.get()).isEqualTo("/api/v1/admin/audit-logs");

        // Consulting route: 401 without token, 200 with authenticated user
        webTestClient.get().uri("/api/v1/consulting/orgs/1").exchange().expectStatus().isUnauthorized();
        webTestClient.get()
                .uri("/api/v1/consulting/orgs/1")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + userJwt)
                .exchange()
                .expectStatus().isOk();
        assertThat(LAST_DOWNSTREAM_PATH.get()).isEqualTo("/api/v1/consulting/orgs/1");

        // Assessments route: 401 without token, 200 with authenticated user
        webTestClient.post().uri("/api/v1/assessments/start").exchange().expectStatus().isUnauthorized();
        webTestClient.post()
                .uri("/api/v1/assessments/start")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + userJwt)
                .exchange()
                .expectStatus().isOk();
        assertThat(LAST_DOWNSTREAM_PATH.get()).isEqualTo("/api/v1/assessments/start");

        // Selection-trace must remain outside Gateway (no new public route)
        webTestClient.method(HttpMethod.POST)
                .uri("/api/v1/internal/simulations/selection-trace")
                .exchange()
                .expectStatus().isUnauthorized();
        webTestClient.method(HttpMethod.POST)
                .uri("/api/v1/internal/simulations/selection-trace")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + userJwt)
                .exchange()
                .expectStatus().isNotFound();
    }

    private void assertProblemCorrelationId(
            EntityExchangeResult<byte[]> result,
            String expectedCorrelationId,
            String expectedErrorCode
    ) throws Exception {
        JsonNode json = jsonMapper.readTree(result.getResponseBody());
        assertThat(json.get("isSuccess").asBoolean()).isFalse();
        assertThat(json.get("errorCode").asString()).isEqualTo(expectedErrorCode);
        assertThat(json.get("correlationId").asString()).isEqualTo(expectedCorrelationId);
    }

    private static HttpServer startDownstreamServer() {
        try {
            HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
            server.createContext("/", exchange -> {
                LAST_DOWNSTREAM_PATH.set(exchange.getRequestURI().getPath());
                LAST_DOWNSTREAM_CORRELATION_ID.set(exchange.getRequestHeaders().getFirst(GatewayHeaders.CORRELATION_ID));
                String forcedResponseId = FORCED_DOWNSTREAM_RESPONSE_CORRELATION_ID.get();
                if (forcedResponseId != null) {
                    exchange.getResponseHeaders().set(GatewayHeaders.CORRELATION_ID, forcedResponseId);
                }
                byte[] body = "{\"ok\":true}".getBytes(StandardCharsets.UTF_8);
                exchange.getResponseHeaders().set("Content-Type", "application/json");
                exchange.sendResponseHeaders(FORCED_DOWNSTREAM_STATUS.get(), body.length);
                try (OutputStream out = exchange.getResponseBody()) {
                    out.write(body);
                }
            });
            server.start();
            return server;
        } catch (IOException exception) {
            throw new IllegalStateException("Failed to start embedded downstream test server", exception);
        }
    }
}
