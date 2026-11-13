package ir.zango.auth.service;

import ir.zango.auth.domain.entity.UserEntity;
import ir.zango.auth.dto.RefreshTokenResponseDTO;

import java.util.UUID;

public interface RefreshTokenService {

    IssuedRefreshToken issue(UserEntity user);

    RefreshTokenResponseDTO rotate(String rawToken);

    void logout(String rawToken);

    void logoutAll(UUID userId);
}
