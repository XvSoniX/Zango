package ir.nextminds.admin.config;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.converter.RsaKeyConverters;
import org.springframework.security.oauth2.core.DelegatingOAuth2TokenValidator;
import org.springframework.security.oauth2.core.OAuth2Error;
import org.springframework.security.oauth2.core.OAuth2TokenValidator;
import org.springframework.security.oauth2.core.OAuth2TokenValidatorResult;
import org.springframework.security.oauth2.jose.jws.SignatureAlgorithm;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtValidators;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.interfaces.RSAPublicKey;
import java.util.UUID;

@Configuration
@EnableConfigurationProperties(JwtProperties.class)
public class JwtConfig {

    @Bean
    public JwtDecoder jwtDecoder(JwtProperties properties) {
        validate(properties);
        NimbusJwtDecoder decoder = NimbusJwtDecoder.withPublicKey(loadPublicKey(Path.of(properties.getPublicKeyPath())))
                .signatureAlgorithm(SignatureAlgorithm.RS256)
                .build();
        decoder.setJwtValidator(validator(properties.getIssuer(), properties.getAudience()));
        return decoder;
    }

    private OAuth2TokenValidator<Jwt> validator(String issuer, String audience) {
        return new DelegatingOAuth2TokenValidator<>(
                JwtValidators.createDefaultWithIssuer(issuer),
                token -> requireAudience(token, audience),
                this::requireSubject
        );
    }

    private OAuth2TokenValidatorResult requireAudience(Jwt token, String audience) {
        if (token.getAudience() == null || !token.getAudience().contains(audience)) {
            return OAuth2TokenValidatorResult.failure(new OAuth2Error("invalid_token"));
        }
        return OAuth2TokenValidatorResult.success();
    }

    private OAuth2TokenValidatorResult requireSubject(Jwt token) {
        String subject = token.getSubject();
        if (subject == null || subject.isBlank()) {
            return OAuth2TokenValidatorResult.failure(new OAuth2Error("invalid_token"));
        }
        try {
            UUID.fromString(subject);
        } catch (IllegalArgumentException exception) {
            return OAuth2TokenValidatorResult.failure(new OAuth2Error("invalid_token"));
        }
        return OAuth2TokenValidatorResult.success();
    }

    private void validate(JwtProperties properties) {
        if (properties.getPublicKeyPath() == null || properties.getPublicKeyPath().isBlank()) {
            throw new IllegalStateException("JWT public key path is required");
        }
        if (properties.getIssuer() == null || properties.getIssuer().isBlank()) {
            throw new IllegalStateException("JWT issuer is required");
        }
        if (properties.getAudience() == null || properties.getAudience().isBlank()) {
            throw new IllegalStateException("JWT audience is required");
        }
    }

    private RSAPublicKey loadPublicKey(Path path) {
        if (!Files.isRegularFile(path)) {
            throw new IllegalStateException("JWT public key file was not found: " + path);
        }
        try (InputStream input = Files.newInputStream(path)) {
            return RsaKeyConverters.x509().convert(input);
        } catch (IOException exception) {
            throw new IllegalStateException("JWT public key file could not be read: " + path, exception);
        }
    }
}
