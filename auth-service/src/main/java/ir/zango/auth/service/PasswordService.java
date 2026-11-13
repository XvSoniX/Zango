package ir.zango.auth.service;

import ir.zango.auth.dto.ChangePasswordRequestDTO;
import ir.zango.auth.dto.ForgotPasswordRequestDTO;
import ir.zango.auth.dto.ResetPasswordRequestDTO;

import java.util.UUID;

public interface PasswordService {

    void changePassword(UUID userId, ChangePasswordRequestDTO request);

    void requestReset(ForgotPasswordRequestDTO request);

    void resetPassword(ResetPasswordRequestDTO request);
}
