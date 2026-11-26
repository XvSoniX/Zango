package ir.nextminds.admin.integration.auth;

import org.junit.jupiter.api.Test;
import org.springframework.web.client.RestClientException;

import java.net.ConnectException;
import java.net.http.HttpConnectTimeoutException;
import java.net.http.HttpTimeoutException;

import static org.junit.jupiter.api.Assertions.assertEquals;

class DownstreamFailureClassifierTest {

    @Test
    void connectionRefusedIsUnavailable() {
        DownstreamCallException failure = DownstreamFailureClassifier.classify(
                new RestClientException("connect", new ConnectException("Connection refused"))
        );

        assertEquals(DownstreamCallException.Kind.UNAVAILABLE, failure.kind());
        assertEquals(DownstreamFailureClassifier.CONNECTION_FAILED, failure.failureType());
    }

    @Test
    void connectTimeoutIsUnavailable() {
        DownstreamCallException failure = DownstreamFailureClassifier.classify(
                new HttpConnectTimeoutException("HTTP connect timed out")
        );

        assertEquals(DownstreamCallException.Kind.UNAVAILABLE, failure.kind());
    }

    @Test
    void readTimeoutIsUnknown() {
        DownstreamCallException failure = DownstreamFailureClassifier.classify(
                new RestClientException("read", new HttpTimeoutException("request timed out"))
        );

        assertEquals(DownstreamCallException.Kind.UNKNOWN, failure.kind());
        assertEquals(DownstreamFailureClassifier.TIMEOUT, failure.failureType());
    }

    @Test
    void missingServiceInstanceIsUnavailable() {
        DownstreamCallException failure = DownstreamFailureClassifier.classify(
                new IllegalStateException("No instances available for AUTH-SERVICE")
        );

        assertEquals(DownstreamCallException.Kind.UNAVAILABLE, failure.kind());
        assertEquals(DownstreamFailureClassifier.CONNECTION_FAILED, failure.failureType());
    }

    @Test
    void resetAfterSendIsUnknown() {
        DownstreamCallException failure = DownstreamFailureClassifier.classify(
                new RestClientException("reset", new java.net.SocketException("Connection reset"))
        );

        assertEquals(DownstreamCallException.Kind.UNKNOWN, failure.kind());
        assertEquals(DownstreamFailureClassifier.CONNECTION_FAILED, failure.failureType());
    }
}
