package ir.zango.auth.security;

import org.springframework.core.convert.converter.Converter;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtGrantedAuthoritiesConverter;

import java.util.Collection;
import java.util.List;

public final class JwtRoleAuthoritiesConverter implements Converter<Jwt, Collection<GrantedAuthority>> {

    public static final String ROLES_CLAIM = "roles";

    private final JwtGrantedAuthoritiesConverter delegate = new JwtGrantedAuthoritiesConverter();

    public JwtRoleAuthoritiesConverter() {
        delegate.setAuthoritiesClaimName(ROLES_CLAIM);
        delegate.setAuthorityPrefix("");
    }

    @Override
    public Collection<GrantedAuthority> convert(Jwt jwt) {
        Collection<GrantedAuthority> authorities = delegate.convert(jwt);
        return authorities == null ? List.of() : authorities;
    }
}
