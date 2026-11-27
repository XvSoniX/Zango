package ir.nextminds.gateway;

import com.nimbusds.jose.JOSEObjectType;
import com.nimbusds.jose.JWSAlgorithm;
import com.nimbusds.jose.JWSHeader;
import com.nimbusds.jose.crypto.RSASSASigner;
import com.nimbusds.jwt.JWTClaimsSet;
import com.nimbusds.jwt.SignedJWT;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.NoSuchAlgorithmException;
import java.security.interfaces.RSAPrivateKey;
import java.time.Instant;
import java.util.Base64;
import java.util.Date;
import java.util.List;
import java.util.UUID;

/**
 * Generates an ephemeral RSA keypair for Gateway tests so tests run in clean clones
 * without requiring gitignored {@code *.pem} key files on disk.
 */
@ActiveProfiles("test")
public abstract class GatewayTestSupport {

    private static final KeyPair RSA_KEY_PAIR = generateRsaKeyPair();
    private static final Path PUBLIC_KEY_FILE = writePublicKeyPem(RSA_KEY_PAIR);

    @DynamicPropertySource
    static void registerJwtPublicKey(DynamicPropertyRegistry registry) {
        registry.add(
                "spring.security.oauth2.resourceserver.jwt.public-key-location",
                () -> PUBLIC_KEY_FILE.toUri().toString()
        );
    }

    protected static String signJwt(String subject, List<String> roles) {
        return signJwt(subject, roles, "http://localhost:8081", "nextminds", Instant.now().plusSeconds(300));
    }

    protected static String signJwt(
            String subject,
            List<String> roles,
            String issuer,
            String audience,
            Instant expiresAt
    ) {
        try {
            JWTClaimsSet claims = new JWTClaimsSet.Builder()
                    .subject(subject)
                    .issuer(issuer)
                    .audience(audience)
                    .jwtID(UUID.randomUUID().toString())
                    .issueTime(Date.from(Instant.now()))
                    .expirationTime(Date.from(expiresAt))
                    .claim("roles", roles)
                    .build();

            JWSHeader header = new JWSHeader.Builder(JWSAlgorithm.RS256)
                    .type(JOSEObjectType.JWT)
                    .keyID("test-rs256")
                    .build();

            SignedJWT jwt = new SignedJWT(header, claims);
            jwt.sign(new RSASSASigner((RSAPrivateKey) RSA_KEY_PAIR.getPrivate()));
            return jwt.serialize();
        } catch (Exception exception) {
            throw new IllegalStateException("Failed to sign test JWT", exception);
        }
    }

    private static KeyPair generateRsaKeyPair() {
        try {
            KeyPairGenerator generator = KeyPairGenerator.getInstance("RSA");
            generator.initialize(2048);
            return generator.generateKeyPair();
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("RSA algorithm unavailable", exception);
        }
    }

    private static Path writePublicKeyPem(KeyPair keyPair) {
        try {
            Path tempFile = Files.createTempFile("gateway-test-public-", ".pem");
            tempFile.toFile().deleteOnExit();
            String encoded = Base64.getMimeEncoder(64, "\n".getBytes(StandardCharsets.US_ASCII))
                    .encodeToString(keyPair.getPublic().getEncoded());
            String pem = "-----BEGIN PUBLIC KEY-----\n" + encoded + "\n-----END PUBLIC KEY-----\n";
            Files.writeString(tempFile, pem, StandardCharsets.US_ASCII);
            return tempFile;
        } catch (IOException exception) {
            throw new IllegalStateException("Failed to write ephemeral test public key", exception);
        }
    }
}
