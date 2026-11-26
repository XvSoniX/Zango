package ir.nextminds.admin.config;

import ir.nextminds.admin.exception.AdminSecurityErrorHandler;
import ir.nextminds.admin.security.JwtRoleAuthoritiesConverter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.oauth2.jwt.JwtClaimNames;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationConverter;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
@EnableMethodSecurity
public class SecurityConfig {

    @Bean
    public JwtAuthenticationConverter jwtAuthenticationConverter() {
        JwtAuthenticationConverter converter = new JwtAuthenticationConverter();
        converter.setPrincipalClaimName(JwtClaimNames.SUB);
        converter.setJwtGrantedAuthoritiesConverter(new JwtRoleAuthoritiesConverter());
        return converter;
    }

    /**
     * Health is public. Administrative routes require {@code ROLE_ADMIN}.
     * Every other route, including actuator info, requires a valid access token.
     */
    @Bean
    public SecurityFilterChain securityFilterChain(
            HttpSecurity http,
            JwtAuthenticationConverter jwtAuthenticationConverter,
            AdminSecurityErrorHandler adminSecurityErrorHandler
    ) throws Exception {
        return http
                .csrf(AbstractHttpConfigurer::disable)
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers("/actuator/health", "/actuator/health/**", "/actuator/prometheus").permitAll()
                        .requestMatchers("/api/v1/admin/**").hasRole("ADMIN")
                        .anyRequest().authenticated()
                )
                .exceptionHandling(exceptions -> exceptions
                        .authenticationEntryPoint(adminSecurityErrorHandler)
                        .accessDeniedHandler(adminSecurityErrorHandler)
                )
                .oauth2ResourceServer(oauth2 -> oauth2
                        .authenticationEntryPoint(adminSecurityErrorHandler)
                        .accessDeniedHandler(adminSecurityErrorHandler)
                        .jwt(jwt -> jwt.jwtAuthenticationConverter(jwtAuthenticationConverter))
                )
                .httpBasic(AbstractHttpConfigurer::disable)
                .formLogin(AbstractHttpConfigurer::disable)
                .build();
    }
}
