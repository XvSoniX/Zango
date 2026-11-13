package ir.zango.gateway.config;

import jakarta.annotation.PostConstruct;
import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

@Getter
@Setter
@Component
@ConfigurationProperties(prefix = "zango.gateway.security")
public class GatewaySecurityProperties {

    private List<Rule> rules = new ArrayList<>();

    @PostConstruct
    void validate() {
        for (int index = 0; index < rules.size(); index++) {
            Rule rule = rules.get(index);
            if (rule.getPaths() == null || rule.getPaths().isEmpty()) {
                throw new IllegalStateException("Gateway security rule " + index + " must declare at least one path");
            }
            if (rule.getAccess() == null) {
                throw new IllegalStateException("Gateway security rule " + index + " must declare an access type");
            }
            if (rule.getAccess() == Access.ROLE && (rule.getRoles() == null || rule.getRoles().isEmpty())) {
                throw new IllegalStateException("Gateway security rule " + index + " must declare at least one role");
            }
        }
    }

    @Getter
    @Setter
    public static class Rule {

        private String method;
        private List<String> paths = new ArrayList<>();
        private Access access;
        private List<String> roles = new ArrayList<>();
    }

    public enum Access {
        PUBLIC,
        AUTHENTICATED,
        ROLE
    }
}
