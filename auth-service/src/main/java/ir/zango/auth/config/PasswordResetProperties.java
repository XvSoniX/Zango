package ir.zango.auth.config;

import jakarta.annotation.PostConstruct;
import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.time.Duration;

@Getter
@Setter
@Component
@ConfigurationProperties(prefix = "zango.auth.password-reset")
public class PasswordResetProperties {

    private Duration ttl = Duration.ofMinutes(30);
    private int rateLimit = 5;
    private Duration rateLimitWindow = Duration.ofMinutes(15);

    @PostConstruct
    void validate() {
        if (ttl == null || ttl.isZero() || ttl.isNegative()) {
            throw new IllegalStateException("Password reset token expiration must be positive");
        }
        if (rateLimit < 1) {
            throw new IllegalStateException("Password reset rate limit must be positive");
        }
        if (rateLimitWindow == null || rateLimitWindow.isZero() || rateLimitWindow.isNegative()) {
            throw new IllegalStateException("Password reset rate limit window must be positive");
        }
    }
}
