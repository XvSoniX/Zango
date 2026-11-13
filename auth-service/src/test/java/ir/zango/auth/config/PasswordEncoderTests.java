package ir.zango.auth.config;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.security.crypto.password.PasswordEncoder;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
class PasswordEncoderTests {

    @Autowired
    private PasswordEncoder passwordEncoder;

    @Test
    void encodesWithArgon2idAndVerifiesThroughMatches() {
        String rawPassword = "correct-horse-battery";

        String encoded = passwordEncoder.encode(rawPassword);
        String encodedAgain = passwordEncoder.encode(rawPassword);

        assertThat(encoded).startsWith("$argon2id$v=19$m=65536,t=3,p=1$");
        assertThat(encoded).isNotEqualTo(rawPassword);
        assertThat(encodedAgain).isNotEqualTo(encoded);
        assertThat(passwordEncoder.matches(rawPassword, encoded)).isTrue();
        assertThat(passwordEncoder.matches("wrong-password", encoded)).isFalse();
    }
}
