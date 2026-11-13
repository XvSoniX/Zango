package ir.zango.auth.security;

import ir.zango.auth.config.JwtProperties;
import ir.zango.auth.repository.UserRoleRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.security.oauth2.jose.jws.SignatureAlgorithm;
import org.springframework.security.oauth2.jwt.JwsHeader;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

@Component
@RequiredArgsConstructor
public class JwtAccessTokenGenerator {

    private final JwtEncoder jwtEncoder;
    private final JwtProperties jwtProperties;
    private final UserRoleRepository userRoleRepository;

    @Transactional(readOnly = true)
    public AccessToken generate(UUID userId) {
        Instant issuedAt = Instant.now();
        Instant expiresAt = issuedAt.plus(jwtProperties.getAccessTokenTtl());
        List<String> roles = userRoleRepository.findRoleNamesByUserId(userId);

        JwsHeader header = JwsHeader.with(SignatureAlgorithm.RS256)
                .keyId(jwtProperties.getKeyId())
                .type("JWT")
                .build();
        JwtClaimsSet claims = JwtClaimsSet.builder()
                .subject(userId.toString())
                .issuer(jwtProperties.getIssuer())
                .audience(List.of(jwtProperties.getAudience()))
                .issuedAt(issuedAt)
                .expiresAt(expiresAt)
                .id(UUID.randomUUID().toString())
                .claim(JwtRoleAuthoritiesConverter.ROLES_CLAIM, roles)
                .build();

        String token = jwtEncoder.encode(
                JwtEncoderParameters.from(
                        header,
                        claims
                )
        ).getTokenValue();

        return new AccessToken(
                token,
                expiresAt,
                jwtProperties.getAccessTokenTtl().toSeconds()
        );
    }
}
