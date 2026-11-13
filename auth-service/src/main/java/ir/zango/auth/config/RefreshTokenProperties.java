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
@ConfigurationProperties(prefix = "zango.auth.refresh-token")
public class RefreshTokenProperties {

    private Duration ttl = Duration.ofHours(24);

    @PostConstruct
    void validate() {
        if (ttl == null || ttl.isZero() || ttl.isNegative()) {
            throw new IllegalStateException("Refresh token expiration must be positive");
        }
    }
}
