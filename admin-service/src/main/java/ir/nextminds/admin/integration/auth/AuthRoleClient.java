package ir.nextminds.admin.integration.auth;

import ir.nextminds.admin.exception.AdminExceptionHandler;
import ir.nextminds.admin.integration.CorrelationIdFilter;
import ir.nextminds.admin.integration.DownstreamCaller;
import ir.nextminds.admin.role.dto.RoleResponse;
import ir.nextminds.admin.role.dto.UserRolesResponse;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.JavaType;
import tools.jackson.databind.json.JsonMapper;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Component
public class AuthRoleClient {

    static final String AUTH_SERVER_ERROR = "AUTH_SERVER_ERROR";
    static final String MISSING_ROLE_ID = "MISSING_ROLE_ID";
    static final String INCOMPLETE_RESPONSE = "INCOMPLETE_RESPONSE";

    private final RestClient authRestClient;
    private final JsonMapper jsonMapper;
    private final JavaType roleListType;

    public AuthRoleClient(RestClient authRestClient, JsonMapper jsonMapper) {
        this.authRestClient = authRestClient;
        this.jsonMapper = jsonMapper;
        this.roleListType = jsonMapper.getTypeFactory().constructCollectionType(List.class, RoleResponse.class);
    }

    public List<RoleResponse> listRoles(DownstreamCaller caller) {
        return read(execute(HttpMethod.GET, "/api/v1/auth/admin/roles", null, caller), roleListType);
    }

    public UserRolesResponse findUserRoles(UUID userId, DownstreamCaller caller) {
        return read(
                execute(HttpMethod.GET, "/api/v1/auth/admin/users/" + userId + "/roles", null, caller),
                UserRolesResponse.class
        );
    }

    public RoleResponse createRole(String name, String description, DownstreamCaller caller) {
        RoleResponse created = read(
                execute(HttpMethod.POST, "/api/v1/auth/admin/roles", new AuthRoleWrite(name, description), caller),
                RoleResponse.class
        );
        if (created == null || created.id() == null) {
            throw DownstreamCallException.unknown(MISSING_ROLE_ID);
        }
        return created;
    }

    public RoleResponse updateRole(UUID roleId, String name, String description, DownstreamCaller caller) {
        return read(
                execute(
                        HttpMethod.PUT,
                        "/api/v1/auth/admin/roles/" + roleId,
                        new AuthRoleWrite(name, description),
                        caller
                ),
                RoleResponse.class
        );
    }

    public void deleteRole(UUID roleId, DownstreamCaller caller) {
        requireSuccess(execute(HttpMethod.DELETE, "/api/v1/auth/admin/roles/" + roleId, null, caller));
    }

    public void assignRole(UUID userId, UUID roleId, DownstreamCaller caller) {
        requireSuccess(execute(
                HttpMethod.POST,
                "/api/v1/auth/admin/users/" + userId + "/roles",
                new AuthAssign(roleId),
                caller
        ));
    }

    public void revokeRole(UUID userId, UUID roleId, DownstreamCaller caller) {
        requireSuccess(execute(
                HttpMethod.DELETE,
                "/api/v1/auth/admin/users/" + userId + "/roles/" + roleId,
                null,
                caller
        ));
    }

    private ResponseEntity<byte[]> execute(HttpMethod method, String uri, Object body, DownstreamCaller caller) {
        try {
            RestClient.RequestBodySpec spec = authRestClient.method(method)
                    .uri(uri)
                    .headers(headers -> apply(headers, caller));
            if (body != null) {
                spec.contentType(MediaType.APPLICATION_JSON);
                spec.body(body);
            }
            return spec.exchange((request, response) -> {
                byte[] payload = response.getBody().readAllBytes();
                return ResponseEntity.status(response.getStatusCode()).body(payload);
            });
        } catch (RestClientException exception) {
            throw DownstreamFailureClassifier.classify(exception);
        } catch (IllegalStateException exception) {
            DownstreamCallException failure = DownstreamFailureClassifier.classify(exception);
            if (failure.kind() == DownstreamCallException.Kind.UNAVAILABLE) {
                throw failure;
            }
            throw exception;
        }
    }

    private void apply(HttpHeaders headers, DownstreamCaller caller) {
        if (caller.authorization() != null) {
            headers.set(HttpHeaders.AUTHORIZATION, caller.authorization());
        }
        if (caller.acceptLanguage() != null && !caller.acceptLanguage().isBlank()) {
            headers.set(HttpHeaders.ACCEPT_LANGUAGE, caller.acceptLanguage());
        }
        headers.set(CorrelationIdFilter.HEADER, caller.correlationId().toString());
        headers.setAccept(List.of(MediaType.APPLICATION_JSON));
    }

    private <T> T read(ResponseEntity<byte[]> response, Class<T> type) {
        byte[] body = requireSuccess(response);
        if (body == null || body.length == 0) {
            return null;
        }
        try {
            return jsonMapper.readValue(body, type);
        } catch (JacksonException exception) {
            throw DownstreamCallException.unknown(INCOMPLETE_RESPONSE);
        }
    }

    private <T> T read(ResponseEntity<byte[]> response, JavaType type) {
        byte[] body = requireSuccess(response);
        if (body == null || body.length == 0) {
            return jsonMapper.readValue("[]", type);
        }
        try {
            return jsonMapper.readValue(body, type);
        } catch (JacksonException exception) {
            throw DownstreamCallException.unknown(INCOMPLETE_RESPONSE);
        }
    }

    private byte[] requireSuccess(ResponseEntity<byte[]> response) {
        HttpStatusCode status = response.getStatusCode();
        if (status.is2xxSuccessful()) {
            return response.getBody();
        }
        if (status.is5xxServerError()) {
            throw DownstreamCallException.unknown(AUTH_SERVER_ERROR);
        }
        throw rejected(status, response.getBody());
    }

    private DownstreamCallException rejected(HttpStatusCode status, byte[] body) {
        if (body == null || body.length == 0) {
            return DownstreamCallException.rejected(status, null, "Request rejected", "", "BAD_REQUEST", List.of());
        }
        try {
            JsonNode node = jsonMapper.readTree(body);
            return DownstreamCallException.rejected(
                    status,
                    text(node, "type"),
                    text(node, "title"),
                    text(node, "detail"),
                    text(node, "errorCode"),
                    fieldErrors(node.get("errors"))
            );
        } catch (RuntimeException exception) {
            return DownstreamCallException.rejected(status, null, "Request rejected", "", "BAD_REQUEST", List.of());
        }
    }

    private List<AdminExceptionHandler.FieldErrorDetailDTO> fieldErrors(JsonNode errors) {
        if (errors == null || !errors.isArray()) {
            return List.of();
        }
        List<AdminExceptionHandler.FieldErrorDetailDTO> details = new ArrayList<>();
        for (JsonNode error : errors) {
            details.add(new AdminExceptionHandler.FieldErrorDetailDTO(text(error, "field"), text(error, "message")));
        }
        return details;
    }

    private String text(JsonNode node, String field) {
        if (node == null) {
            return null;
        }
        JsonNode value = node.get(field);
        if (value == null || value.isNull()) {
            return null;
        }
        return value.asString();
    }

    private record AuthRoleWrite(String name, String description) {
    }

    private record AuthAssign(UUID roleId) {
    }
}
