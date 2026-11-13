package ir.zango.auth.repository;

import ir.zango.auth.domain.entity.UserRoleEntity;
import ir.zango.auth.domain.entity.UserRoleId;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.UUID;

public interface UserRoleRepository extends JpaRepository<UserRoleEntity, UserRoleId> {

    @Query("""
            select role.name
            from UserRoleEntity userRole
            join userRole.role role
            where userRole.user.id = :userId
            order by role.name
            """)
    List<String> findRoleNamesByUserId(@Param("userId") UUID userId);
}
