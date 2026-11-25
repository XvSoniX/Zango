package ir.nextminds.user.service;

import ir.nextminds.user.dto.CreateUserRequest;
import ir.nextminds.user.dto.UpdateUserRequest;
import ir.nextminds.user.dto.UserResponse;
import ir.nextminds.user.entity.User;
import ir.nextminds.user.exception.BusinessRuleException;
import ir.nextminds.user.exception.DuplicateResourceException;
import ir.nextminds.user.exception.ResourceNotFoundException;
import ir.nextminds.user.repository.UserRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class UserServiceTest {

    private static final Clock FIXED_CLOCK =
            Clock.fixed(Instant.parse("2026-06-15T00:00:00Z"), ZoneOffset.UTC);

    @Mock
    private UserRepository userRepository;

    private UserService userService;

    @BeforeEach
    void setUp() {
        userService = new UserService(userRepository, FIXED_CLOCK, 8, 16);
    }

    @Test
    void createSavesTrimmedProfile() {
        UUID authId = UUID.randomUUID();
        when(userRepository.existsByAuthUserId(authId)).thenReturn(false);
        when(userRepository.saveAndFlush(any(User.class))).thenAnswer(inv -> inv.getArgument(0));

        UserResponse response = userService.create(
                new CreateUserRequest(authId, "  Sara ", " Ahmadi ", LocalDate.of(2015, 1, 1)));

        assertThat(response.authUserId()).isEqualTo(authId);
        assertThat(response.firstName()).isEqualTo("Sara");
        assertThat(response.lastName()).isEqualTo("Ahmadi");
    }

    @Test
    void createRejectsDuplicateAuthUserId() {
        UUID authId = UUID.randomUUID();
        when(userRepository.existsByAuthUserId(authId)).thenReturn(true);

        assertThatThrownBy(() -> userService.create(
                new CreateUserRequest(authId, "Sara", "Ahmadi", LocalDate.of(2015, 1, 1))))
                .isInstanceOf(DuplicateResourceException.class);
        verify(userRepository, never()).saveAndFlush(any());
    }

    @Test
    void createRejectsTooYoung() {
        UUID authId = UUID.randomUUID();
        when(userRepository.existsByAuthUserId(authId)).thenReturn(false);

        // 7 years old on 2026-06-15
        assertThatThrownBy(() -> userService.create(
                new CreateUserRequest(authId, "Sara", "Ahmadi", LocalDate.of(2019, 6, 16))))
                .isInstanceOf(BusinessRuleException.class);
    }

    @Test
    void createRejectsTooOld() {
        UUID authId = UUID.randomUUID();
        when(userRepository.existsByAuthUserId(authId)).thenReturn(false);

        // 17 years old on 2026-06-15
        assertThatThrownBy(() -> userService.create(
                new CreateUserRequest(authId, "Sara", "Ahmadi", LocalDate.of(2009, 6, 15))))
                .isInstanceOf(BusinessRuleException.class);
    }

    @Test
    void createAcceptsBoundaryAges() {
        UUID authId = UUID.randomUUID();
        when(userRepository.existsByAuthUserId(authId)).thenReturn(false);
        when(userRepository.saveAndFlush(any(User.class))).thenAnswer(inv -> inv.getArgument(0));

        // exactly 8 today
        assertThat(userService.create(
                new CreateUserRequest(authId, "A", "B", LocalDate.of(2018, 6, 15)))).isNotNull();
    }

    @Test
    void getByIdThrowsWhenMissing() {
        UUID id = UUID.randomUUID();
        when(userRepository.findById(id)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> userService.getById(id))
                .isInstanceOf(ResourceNotFoundException.class);
    }

    @Test
    void updateChangesProfileButNotAuthUserId() {
        UUID id = UUID.randomUUID();
        UUID authId = UUID.randomUUID();
        User existing = new User(authId, "Old", "Name", LocalDate.of(2015, 1, 1));
        when(userRepository.findById(id)).thenReturn(Optional.of(existing));
        when(userRepository.saveAndFlush(existing)).thenReturn(existing);

        UserResponse response = userService.update(id,
                new UpdateUserRequest("New", "Person", LocalDate.of(2014, 3, 3)));

        assertThat(response.firstName()).isEqualTo("New");
        assertThat(response.lastName()).isEqualTo("Person");
        assertThat(response.authUserId()).isEqualTo(authId);
    }

    @Test
    void deleteThrowsWhenMissing() {
        UUID id = UUID.randomUUID();
        when(userRepository.findById(id)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> userService.delete(id))
                .isInstanceOf(ResourceNotFoundException.class);
        verify(userRepository, never()).delete(any());
    }
}
