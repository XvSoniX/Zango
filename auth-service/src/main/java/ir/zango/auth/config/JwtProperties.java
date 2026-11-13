package ir.zango.auth.config;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;

import java.time.Duration;

@Setter
@Getter
@ConfigurationProperties(prefix = "zango.auth.jwt")
public class JwtProperties {

    private String privateKeyPath = "./gateway-service/keys/private.pem";
    private String issuer = "http://localhost:8081";
    private String audience = "zango";
    private Duration accessTokenTtl = Duration.ofMinutes(15);
    private String keyId = "zango-auth-rs256-1";

}
