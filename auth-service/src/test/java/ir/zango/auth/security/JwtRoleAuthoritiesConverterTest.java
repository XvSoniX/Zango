package ir.zango.auth.security;

import org.junit.jupiter.api.Test;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class JwtRoleAuthoritiesConverterTest {

    private final JwtRoleAuthoritiesConverter converter = new JwtRoleAuthoritiesConverter();

    @Test
    void mapsRoleClaimsWithoutAddingAnotherPrefix() {
        Jwt jwt = Jwt.withTokenValue("token")
                .header("alg", "none")
                .subject("user")
                .claim(JwtRoleAuthoritiesConverter.ROLES_CLAIM, List.of("ROLE_ADMIN", "ROLE_USER"))
                .build();

        assertThat(converter.convert(jwt))
                .extracting(GrantedAuthority::getAuthority)
                .containsExactly("ROLE_ADMIN", "ROLE_USER");
    }
}
