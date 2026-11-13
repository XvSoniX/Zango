package ir.zango.auth.config;

import com.nimbusds.jose.JWSAlgorithm;
import com.nimbusds.jose.jwk.JWKSet;
import com.nimbusds.jose.jwk.KeyUse;
import com.nimbusds.jose.jwk.RSAKey;
import com.nimbusds.jose.jwk.source.ImmutableJWKSet;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.converter.RsaKeyConverters;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.security.oauth2.jwt.NimbusJwtEncoder;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.GeneralSecurityException;
import java.security.KeyFactory;
import java.security.interfaces.RSAPrivateCrtKey;
import java.security.interfaces.RSAPrivateKey;
import java.security.interfaces.RSAPublicKey;
import java.security.spec.RSAPublicKeySpec;

@Configuration
@EnableConfigurationProperties(JwtProperties.class)
public class JwtConfig {

    @Bean
    public JwtEncoder jwtEncoder(JwtProperties properties) {
        validate(properties);
        RSAPrivateKey privateKey = loadPrivateKey(Path.of(properties.getPrivateKeyPath()));
        RSAKey signingKey = new RSAKey.Builder(publicKey(privateKey))
                .privateKey(privateKey)
                .keyID(properties.getKeyId())
                .keyUse(KeyUse.SIGNATURE)
                .algorithm(JWSAlgorithm.RS256)
                .build();
        return new NimbusJwtEncoder(new ImmutableJWKSet<>(new JWKSet(signingKey)));
    }

    @Bean
    public JwtDecoder jwtDecoder(JwtProperties properties) {
        validate(properties);
        return NimbusJwtDecoder.withPublicKey(
                publicKey(
                        loadPrivateKey(
                                Path.of(
                                        properties.getPrivateKeyPath()
                                )
                        )
                )
        ).build();
    }

    private void validate(JwtProperties properties) {
        if (properties.getPrivateKeyPath() == null || properties.getPrivateKeyPath().isBlank()) {
            throw new IllegalStateException("JWT private key path is required");
        }
        if (properties.getIssuer() == null || properties.getIssuer().isBlank()) {
            throw new IllegalStateException("JWT issuer is required");
        }
        if (properties.getKeyId() == null || properties.getKeyId().isBlank()) {
            throw new IllegalStateException("JWT key id is required");
        }
        if (properties.getAccessTokenTtl() == null || properties.getAccessTokenTtl().isZero()
                || properties.getAccessTokenTtl().isNegative()) {
            throw new IllegalStateException("JWT access token expiration must be positive");
        }
    }

    private RSAPrivateKey loadPrivateKey(Path path) {
        if (!Files.isRegularFile(path)) {
            throw new IllegalStateException("JWT private key file was not found: " + path);
        }
        try (InputStream input = Files.newInputStream(path)) {
            return RsaKeyConverters.pkcs8().convert(input);
        } catch (IOException exception) {
            throw new IllegalStateException("JWT private key file could not be read: " + path, exception);
        }
    }

    private RSAPublicKey publicKey(RSAPrivateKey privateKey) {
        if (!(privateKey instanceof RSAPrivateCrtKey crtKey)) {
            throw new IllegalStateException("JWT private key must include the RSA public exponent");
        }
        try {
            return (RSAPublicKey) KeyFactory.getInstance("RSA")
                    .generatePublic(new RSAPublicKeySpec(crtKey.getModulus(), crtKey.getPublicExponent()));
        } catch (GeneralSecurityException exception) {
            throw new IllegalStateException("JWT public key could not be derived from the private key", exception);
        }
    }
}
