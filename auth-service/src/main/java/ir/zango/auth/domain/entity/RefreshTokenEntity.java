package ir.zango.auth.domain.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.OneToOne;
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
@Table(name = "refresh_tokens")
public class RefreshTokenEntity {

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
    @Column(name = "family_id", nullable = false)
    private UUID familyId;

    @Setter
    @Column(name = "expires_at", nullable = false)
    private Instant expiresAt;

    @Setter
    @Column(name = "revoked_at")
    private Instant revokedAt;

    @Setter
    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "replaced_by_id")
    private RefreshTokenEntity replacedBy;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    public void assignTokenHash(String tokenHash) {
        this.tokenHash = tokenHash;
    }

    public void assignCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }

    public static RefreshTokenEntity issue(
            UserEntity user,
            String tokenHash,
            UUID familyId,
            Instant expiresAt,
            Instant createdAt
    ) {
        RefreshTokenEntity token = new RefreshTokenEntity();
        token.user = user;
        token.tokenHash = tokenHash;
        token.familyId = familyId;
        token.expiresAt = expiresAt;
        token.createdAt = createdAt;
        return token;
    }
}
