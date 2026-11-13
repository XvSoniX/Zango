package ir.zango.auth.repository;

import ir.zango.auth.domain.entity.UserRoleEntity;
import ir.zango.auth.domain.entity.UserRoleId;
import org.springframework.data.jpa.repository.JpaRepository;

public interface UserRoleRepository extends JpaRepository<UserRoleEntity, UserRoleId> {
}
