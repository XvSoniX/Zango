package ir.zango.auth.controller;

import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.security.oauth2.jwt.BadJwtException;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtDecoder;

import java.util.List;
import java.util.UUID;

@TestConfiguration
public class JwtDecoderTestConfig {

    static final String USER_TOKEN = "user-token";
    static final String ADMIN_TOKEN = "admin-token";

    @Bean
    JwtDecoder jwtDecoder() {
        return token -> switch (token) {
            case USER_TOKEN -> jwt("ROLE_USER");
            case ADMIN_TOKEN -> jwt("ROLE_ADMIN");
            default -> throw new BadJwtException("invalid");
        };
    }

    private Jwt jwt(String role) {
        return Jwt.withTokenValue("token")
                .header("alg", "RS256")
                .subject(UUID.randomUUID().toString())
                .claim("roles", List.of(role))
                .build();
    }
}
