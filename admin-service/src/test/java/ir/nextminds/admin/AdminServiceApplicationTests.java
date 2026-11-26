package ir.nextminds.admin;

import ir.nextminds.admin.audit.repository.AdminAuditLogRepository;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;

@SpringBootTest
@MockitoBean(types = AdminAuditLogRepository.class)
class AdminServiceApplicationTests {

    @Test
    void contextLoads() {
    }
}
