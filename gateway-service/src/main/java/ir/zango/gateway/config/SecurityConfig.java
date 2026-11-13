package ir.zango.gateway.config;

import ir.zango.gateway.exception.AccessDeniedErrorHandler;
import ir.zango.gateway.exception.AuthenticationErrorHandler;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.reactive.EnableWebFluxSecurity;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.config.web.server.ServerHttpSecurity;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.security.oauth2.core.OAuth2TokenValidator;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtClaimNames;
import org.springframework.security.oauth2.jwt.JwtIssuerValidator;
import org.springframework.security.oauth2.server.resource.authentication.ReactiveJwtAuthenticationConverter;
import org.springframework.security.web.server.SecurityWebFilterChain;
import org.springframework.security.web.server.context.NoOpServerSecurityContextRepository;
import reactor.core.publisher.Flux;

import java.util.List;
import java.util.Locale;

@Configuration
@EnableWebFluxSecurity
@RequiredArgsConstructor
public class SecurityConfig {

    private final AuthenticationErrorHandler authenticationErrorHandler;
    private final AccessDeniedErrorHandler accessDeniedErrorHandler;
    private final GatewaySecurityProperties gatewaySecurityProperties;

    @Bean
    public SecurityWebFilterChain securityWebFilterChain(
            ServerHttpSecurity http) {

        return http
                .csrf(ServerHttpSecurity.CsrfSpec::disable)
                .cors(cors -> {})
                .httpBasic(ServerHttpSecurity.HttpBasicSpec::disable)
                .formLogin(ServerHttpSecurity.FormLoginSpec::disable)
                .logout(ServerHttpSecurity.LogoutSpec::disable)
                .securityContextRepository(
                        NoOpServerSecurityContextRepository.getInstance()
                )
                .exceptionHandling(exceptionHandling -> exceptionHandling
                        .authenticationEntryPoint(authenticationErrorHandler)
                        .accessDeniedHandler(accessDeniedErrorHandler)
                )
                .authorizeExchange(this::applyRules)
                .oauth2ResourceServer(oauth2 -> oauth2.jwt(jwt ->
                        jwt.jwtAuthenticationConverter(jwtAuthenticationConverter())))
                .build();
    }

    @Bean
    OAuth2TokenValidator<Jwt> jwtIssuerValidator(@Value("${zango.jwt.issuer}") String issuer) {
        return new JwtIssuerValidator(issuer);
    }

    private void applyRules(ServerHttpSecurity.AuthorizeExchangeSpec exchanges) {
        ServerHttpSecurity.AuthorizeExchangeSpec spec = exchanges;
        for (GatewaySecurityProperties.Rule rule : gatewaySecurityProperties.getRules()) {
            String[] paths = rule.getPaths().toArray(String[]::new);
            ServerHttpSecurity.AuthorizeExchangeSpec.Access access = rule.getMethod() == null
                    || rule.getMethod().isBlank()
                    ? spec.pathMatchers(paths)
                    : spec.pathMatchers(HttpMethod.valueOf(rule.getMethod().trim().toUpperCase(Locale.ROOT)), paths);
            spec = switch (rule.getAccess()) {
                case PUBLIC -> access.permitAll();
                case AUTHENTICATED -> access.authenticated();
                case ROLE -> access.hasAnyAuthority(rule.getRoles().toArray(String[]::new));
            };
        }
        spec.anyExchange().authenticated();
    }

    private ReactiveJwtAuthenticationConverter jwtAuthenticationConverter() {
        ReactiveJwtAuthenticationConverter converter = new ReactiveJwtAuthenticationConverter();
        converter.setPrincipalClaimName(JwtClaimNames.SUB);
        converter.setJwtGrantedAuthoritiesConverter(this::roles);
        return converter;
    }

    private Flux<GrantedAuthority> roles(Jwt jwt) {
        List<String> roles = jwt.getClaimAsStringList("roles");
        if (roles == null || roles.isEmpty()) {
            return Flux.empty();
        }
        return Flux.fromIterable(roles)
                .filter(role -> role != null && !role.isBlank())
                .map(SimpleGrantedAuthority::new);
    }
}