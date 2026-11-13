package ir.zango.auth.controller;

import ir.zango.auth.dto.LogoutRequestDTO;
import ir.zango.auth.dto.RefreshTokenRequestDTO;
import ir.zango.auth.dto.RefreshTokenResponseDTO;
import ir.zango.auth.service.RefreshTokenService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.Objects;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/auth")
@RequiredArgsConstructor
public class RefreshTokenController {

    private final RefreshTokenService refreshTokenService;

    @PostMapping("/refresh")
    public RefreshTokenResponseDTO refresh(@Valid @RequestBody RefreshTokenRequestDTO request) {
        return refreshTokenService.rotate(request.refreshToken());
    }

    @PostMapping("/logout")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void logout(@Valid @RequestBody LogoutRequestDTO request) {
        refreshTokenService.logout(request.refreshToken());
    }

    @PostMapping("/logout-all")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void logoutAll(@AuthenticationPrincipal Jwt jwt) {
        refreshTokenService.logoutAll(
                UUID.fromString(
                        Objects.requireNonNull(
                                jwt.getSubject()
                        )
                )
        );
    }
}
