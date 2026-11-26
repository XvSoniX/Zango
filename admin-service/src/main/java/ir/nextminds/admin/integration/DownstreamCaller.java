package ir.nextminds.admin.integration;

import java.util.UUID;

/**
 * The administrator call that must be forwarded to Auth. {@code toString} omits the bearer token.
 */
public record DownstreamCaller(
        UUID administratorId,
        UUID correlationId,
        String authorization,
        String acceptLanguage
) {

    @Override
    public String toString() {
        return "DownstreamCaller[administratorId=" + administratorId + ", correlationId=" + correlationId + "]";
    }
}
