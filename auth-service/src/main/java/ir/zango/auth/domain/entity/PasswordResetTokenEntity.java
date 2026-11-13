package ir.zango.auth.domain.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.UuidGenerator;

import java.time.Instant;
import java.util.UUID;

@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@Entity
@Table(name = "password_reset_tokens")
public class PasswordResetTokenEntity {

    @Id
    @GeneratedValue
    @UuidGenerator
    @Column(name = "id", nullable = false, updatable = false)
    private UUID id;

    @Setter
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_id", nullable = false)
    private UserEntity user;

    @Column(name = "token_hash", nullable = false, length = 255)
    private String tokenHash;

    @Setter
    @Column(name = "expires_at", nullable = false)
    private Instant expiresAt;

    @Setter
    @Column(name = "used_at")
    private Instant usedAt;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    public void assignTokenHash(String tokenHash) {
        this.tokenHash = tokenHash;
    }

    public void assignCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }

    public static PasswordResetTokenEntity issue(
            UserEntity user,
            String tokenHash,
            Instant expiresAt,
            Instant createdAt
    ) {
        PasswordResetTokenEntity token = new PasswordResetTokenEntity();
        token.user = user;
        token.tokenHash = tokenHash;
        token.expiresAt = expiresAt;
        token.createdAt = createdAt;
        return token;
    }
}
