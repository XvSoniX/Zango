package ir.zango.auth.repository;

import ir.zango.auth.domain.entity.PasswordResetTokenEntity;
import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

public interface PasswordResetTokenRepository extends JpaRepository<PasswordResetTokenEntity, UUID> {

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select token from PasswordResetTokenEntity token where token.tokenHash = :tokenHash")
    Optional<PasswordResetTokenEntity> findByTokenHashForUpdate(@Param("tokenHash") String tokenHash);

    @Modifying(flushAutomatically = true)
    @Query("""
            update PasswordResetTokenEntity token
            set token.usedAt = :usedAt
            where token.user.id = :userId
              and token.usedAt is null
            """)
    void consumeActiveByUserId(@Param("userId") UUID userId, @Param("usedAt") Instant usedAt);

    @Modifying(flushAutomatically = true)
    @Query("""
            update PasswordResetTokenEntity token
            set token.usedAt = :usedAt
            where token.user.id = :userId
              and token.usedAt is null
              and token.id <> :tokenId
            """)
    void consumeActiveByUserIdExcept(
            @Param("userId") UUID userId,
            @Param("tokenId") UUID tokenId,
            @Param("usedAt") Instant usedAt
    );
}
