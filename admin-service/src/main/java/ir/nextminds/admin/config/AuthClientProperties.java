package ir.nextminds.admin.config;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;

import java.time.Duration;

@Getter
@Setter
@ConfigurationProperties(prefix = "nextminds.admin.auth")
public class AuthClientProperties {

    private String baseUrl = "http://AUTH-SERVICE";

    /**
     * Connect budget. Together with {@link #responseTimeout} this stays inside the gateway's 5 second limit.
     */
    private Duration connectTimeout = Duration.ofSeconds(1);

    private Duration responseTimeout = Duration.ofSeconds(3);
}
