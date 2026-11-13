package ir.zango.auth.repository;

import ir.zango.auth.domain.entity.CredentialEntity;
import ir.zango.auth.domain.enums.IdentifierTypeEnum;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;
import java.util.UUID;

public interface CredentialRepository extends JpaRepository<CredentialEntity, UUID> {

    Optional<CredentialEntity> findByIdentifierTypeAndIdentifier(
            IdentifierTypeEnum identifierType,
            String identifier
    );
}
