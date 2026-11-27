package ir.nextminds.auth.repository;

import ir.nextminds.auth.domain.entity.RoleEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import jakarta.persistence.LockModeType;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface RoleRepository extends JpaRepository<RoleEntity, UUID> {

    Optional<RoleEntity> findByName(String name);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select role from RoleEntity role where role.id = :id")
    Optional<RoleEntity> findByIdForUpdate(@Param("id") UUID id);

    List<RoleEntity> findAllByOrderByNameAsc();
}
