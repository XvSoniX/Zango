package ir.nextminds.admin.config;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;

@Setter
@Getter
@ConfigurationProperties(prefix = "nextminds.admin.jwt")
public class JwtProperties {

    private String publicKeyPath = "./gateway-service/keys/public.pem";
    private String issuer = "http://localhost:8081";
    private String audience = "nextminds";
}
