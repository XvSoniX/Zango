package ir.nextminds.admin.integration.auth;

import java.net.ConnectException;
import java.net.NoRouteToHostException;
import java.net.UnknownHostException;
import java.net.http.HttpConnectTimeoutException;
import java.net.http.HttpTimeoutException;

public final class DownstreamFailureClassifier {

    public static final String CONNECTION_FAILED = "CONNECTION_FAILED";
    public static final String TIMEOUT = "TIMEOUT";

    private DownstreamFailureClassifier() {
    }

    public static DownstreamCallException classify(Throwable throwable) {
        if (definitePreSend(throwable)) {
            return DownstreamCallException.unavailable(CONNECTION_FAILED);
        }
        if (timeout(throwable)) {
            return DownstreamCallException.unknown(TIMEOUT);
        }
        return DownstreamCallException.unknown(CONNECTION_FAILED);
    }

    private static boolean definitePreSend(Throwable throwable) {
        for (Throwable current = throwable; current != null; current = current.getCause()) {
            if (current instanceof ConnectException
                    || current instanceof UnknownHostException
                    || current instanceof NoRouteToHostException
                    || current instanceof HttpConnectTimeoutException
                    || noServiceInstance(current)) {
                return true;
            }
        }
        return false;
    }

    private static boolean noServiceInstance(Throwable throwable) {
        String message = throwable.getMessage();
        return throwable instanceof IllegalStateException
                && message != null
                && (message.startsWith("No instances available for ")
                || message.startsWith("Service Instance cannot be null"));
    }

    private static boolean timeout(Throwable throwable) {
        for (Throwable current = throwable; current != null; current = current.getCause()) {
            if (current instanceof HttpTimeoutException && !(current instanceof HttpConnectTimeoutException)) {
                return true;
            }
        }
        return false;
    }
}
