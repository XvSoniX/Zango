package ir.zango.auth.domain.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
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
@Table(name = "roles")
public class RoleEntity {

    @Id
    @GeneratedValue
    @UuidGenerator
    @Column(name = "id", nullable = false, updatable = false)
    private UUID id;

    @Setter
    @Column(name = "name", nullable = false, length = 100)
    private String name;

    @Setter
    @Column(name = "description", length = 255)
    private String description;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    public void assignCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }

    public static RoleEntity create(String name, String description, Instant createdAt) {
        RoleEntity role = new RoleEntity();
        role.name = name;
        role.description = description;
        role.createdAt = createdAt;
        return role;
    }
}
