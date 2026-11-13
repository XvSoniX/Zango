package ir.zango.auth;

import ir.zango.auth.repository.CredentialRepository;
import ir.zango.auth.repository.PasswordResetTokenRepository;
import ir.zango.auth.repository.RefreshTokenRepository;
import ir.zango.auth.repository.RoleRepository;
import ir.zango.auth.repository.UserRepository;
import ir.zango.auth.repository.UserRoleRepository;
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
