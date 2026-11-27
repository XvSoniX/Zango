package ir.nextminds.user.repository;

import ir.nextminds.user.entity.User;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@SpringBootTest
@ActiveProfiles("test")
@Transactional
class UserRepositoryIntegrationTest {

    @Autowired
    private UserRepository userRepository;

    @Test
    void liquibaseSchemaValidatesAndPersistsUser() {
        UUID authUserId = UUID.randomUUID();
        User saved = userRepository.saveAndFlush(
                new User(authUserId, "Sara", "Ahmadi", LocalDate.of(2015, 4, 12)));

        assertThat(saved.getId()).isNotNull();
        assertThat(saved.getCreatedAt()).isNotNull();
        assertThat(saved.getUpdatedAt()).isNotNull();
        assertThat(userRepository.existsByAuthUserId(authUserId)).isTrue();
        assertThat(userRepository.findByAuthUserId(authUserId))
                .isPresent()
                .get()
                .extracting(User::getFirstName)
                .isEqualTo("Sara");
    }

    @Test
    void uniqueAuthUserIdConstraintIsEnforcedByDatabase() {
        UUID authUserId = UUID.randomUUID();
        userRepository.saveAndFlush(new User(authUserId, "Sara", "Ahmadi", LocalDate.of(2015, 4, 12)));

        assertThatThrownBy(() -> userRepository.saveAndFlush(
                new User(authUserId, "Another", "User", LocalDate.of(2014, 1, 1))))
                .isInstanceOf(DataIntegrityViolationException.class);
    }
}
