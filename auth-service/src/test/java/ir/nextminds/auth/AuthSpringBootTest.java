package ir.nextminds.auth;

import ir.nextminds.auth.repository.CredentialRepository;
import ir.nextminds.auth.repository.PasswordResetTokenRepository;
import ir.nextminds.auth.repository.RefreshTokenRepository;
import ir.nextminds.auth.repository.RoleRepository;
import ir.nextminds.auth.repository.UserRepository;
import ir.nextminds.auth.repository.UserRoleRepository;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@SpringBootTest
@MockitoBean(types = UserRepository.class)
@MockitoBean(types = CredentialRepository.class)
@MockitoBean(types = RoleRepository.class)
@MockitoBean(types = UserRoleRepository.class)
@MockitoBean(types = RefreshTokenRepository.class)
@MockitoBean(types = PasswordResetTokenRepository.class)
public @interface AuthSpringBootTest {
}
