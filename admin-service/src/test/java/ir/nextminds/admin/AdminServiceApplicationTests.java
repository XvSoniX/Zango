package ir.nextminds.admin;

import ir.nextminds.admin.audit.repository.AdminAuditLogRepository;
import ir.nextminds.admin.config.AuthClientProperties;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.env.YamlPropertySourceLoader;
import org.springframework.boot.context.properties.bind.Bindable;
import org.springframework.boot.context.properties.bind.Binder;
import org.springframework.core.io.FileSystemResource;
import org.springframework.mock.env.MockEnvironment;
import org.springframework.test.context.bean.override.mockito.MockitoBean;

import java.time.Duration;

import static org.junit.jupiter.api.Assertions.assertEquals;

@SpringBootTest
@MockitoBean(types = AdminAuditLogRepository.class)
class AdminServiceApplicationTests {

    @Test
    void contextLoads() {
    }

    @Test
    void environmentValuesOverrideApplicationDefaults() throws Exception {
        MockEnvironment environment = new MockEnvironment();
        environment.setProperty("ADMIN_AUTH_BASE_URL", "http://TEST-AUTH");
        environment.setProperty("ADMIN_AUTH_CONNECT_TIMEOUT", "2s");
        environment.setProperty("ADMIN_AUTH_RESPONSE_TIMEOUT", "4s");
        environment.setProperty("ADMIN_AUDIT_STALE_AFTER", "2h");
        environment.setProperty("ADMIN_AUDIT_MONITOR_INITIAL_DELAY", "2m");
        environment.setProperty("ADMIN_AUDIT_MONITOR_INTERVAL", "10m");
        var yaml = new YamlPropertySourceLoader().load("application",
                new FileSystemResource("src/main/resources/application.yml"));
        yaml.forEach(environment.getPropertySources()::addLast);
        AuthClientProperties authClientProperties = Binder.get(environment)
                .bind("nextminds.admin.auth", Bindable.of(AuthClientProperties.class)).get();
        assertEquals("http://TEST-AUTH", authClientProperties.getBaseUrl());
        assertEquals(Duration.ofSeconds(2), authClientProperties.getConnectTimeout());
        assertEquals(Duration.ofSeconds(4), authClientProperties.getResponseTimeout());
        assertEquals("2h", environment.getProperty("nextminds.admin.audit.stale-after"));
        assertEquals("2m", environment.getProperty("nextminds.admin.audit.monitor-initial-delay"));
        assertEquals("10m", environment.getProperty("nextminds.admin.audit.monitor-interval"));
    }
}
