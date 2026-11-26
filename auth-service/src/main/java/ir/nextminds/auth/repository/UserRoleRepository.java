package ir.nextminds.auth.repository;

import ir.nextminds.auth.domain.entity.UserRoleEntity;
import ir.nextminds.auth.domain.entity.UserRoleId;
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

    boolean existsByRole_Id(UUID roleId);

    @Query("""
            select count(userRole) from UserRoleEntity userRole
            where userRole.role.id = :roleId
              and userRole.user.status = ir.nextminds.auth.domain.enums.AccountStatusEnum.ACTIVE
              and userRole.user.deletedAt is null
            """)
    long countActiveUsersByRoleId(@Param("roleId") UUID roleId);
}
