package ir.nextminds.user.service;

import ir.nextminds.user.dto.CreateUserRequest;
import ir.nextminds.user.dto.UpdateUserRequest;
import ir.nextminds.user.dto.UserResponse;
import ir.nextminds.user.entity.User;
import ir.nextminds.user.exception.BusinessRuleException;
import ir.nextminds.user.exception.DuplicateResourceException;
import ir.nextminds.user.exception.ResourceNotFoundException;
import ir.nextminds.user.repository.UserRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Clock;
import java.time.LocalDate;
import java.time.Period;
import java.util.UUID;

@Service
public class UserService {

    private final UserRepository userRepository;
    private final Clock clock;
    private final int minAge;
    private final int maxAge;

    public UserService(
            UserRepository userRepository,
            Clock clock,
            @Value("${nextminds.user.age-limits.min:8}") int minAge,
            @Value("${nextminds.user.age-limits.max:18}") int maxAge
    ) {
        this.userRepository = userRepository;
        this.clock = clock;
        this.minAge = minAge;
        this.maxAge = maxAge;
    }

    @Transactional
    public UserResponse create(CreateUserRequest request) {
        if (userRepository.existsByAuthUserId(request.authUserId())) {
            throw new DuplicateResourceException(
                    "User profile already exists for authUserId " + request.authUserId());
        }
        validateAge(request.dateOfBirth());

        User user = new User(
                request.authUserId(),
                request.firstName().strip(),
                request.lastName().strip(),
                request.dateOfBirth()
        );
        return UserResponse.from(userRepository.saveAndFlush(user));
    }

    @Transactional(readOnly = true)
    public UserResponse getById(UUID id) {
        return UserResponse.from(findByIdOrThrow(id));
    }

    @Transactional(readOnly = true)
    public UserResponse getByAuthUserId(UUID authUserId) {
        User user = userRepository.findByAuthUserId(authUserId)
                .orElseThrow(() -> new ResourceNotFoundException(
                        "User not found with authUserId " + authUserId));
        return UserResponse.from(user);
    }

    @Transactional(readOnly = true)
    public Page<UserResponse> getAll(Pageable pageable) {
        return userRepository.findAll(pageable).map(UserResponse::from);
    }

    @Transactional
    public UserResponse update(UUID id, UpdateUserRequest request) {
        User existing = findByIdOrThrow(id);
        validateAge(request.dateOfBirth());

        existing.updateProfile(
                request.firstName().strip(),
                request.lastName().strip(),
                request.dateOfBirth()
        );
        return UserResponse.from(userRepository.saveAndFlush(existing));
    }

    @Transactional
    public void delete(UUID id) {
        User existing = findByIdOrThrow(id);
        userRepository.delete(existing);
    }

    private User findByIdOrThrow(UUID id) {
        return userRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("User not found with id " + id));
    }

    private void validateAge(LocalDate dateOfBirth) {
        LocalDate today = LocalDate.now(clock);
        int age = Period.between(dateOfBirth, today).getYears();
        if (age < minAge || age > maxAge) {
            throw new BusinessRuleException(
                    "User age " + age + " is outside the allowed range of " + minAge + " to " + maxAge);
        }
    }
}
