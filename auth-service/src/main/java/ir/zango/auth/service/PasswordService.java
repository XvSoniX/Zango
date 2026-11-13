package ir.zango.auth.service;

import ir.zango.auth.dto.ChangePasswordRequestDTO;
import ir.zango.auth.dto.ForgotPasswordRequestDTO;
import ir.zango.auth.dto.ResetPasswordRequestDTO;

import java.util.UUID;

public interface PasswordService {

    /**
     * Replaces the user's password after the current password matches, then revokes all refresh tokens
     * in the same transaction.
     */
    void changePassword(UUID userId, ChangePasswordRequestDTO request);

    /**
     * Accepts a reset request without revealing whether the email exists.
     * A single-use token is issued only when the account can authenticate.
     */
    void requestReset(ForgotPasswordRequestDTO request);

    /**
     * Consumes a valid reset token, updates the password, and revokes the user's refresh tokens.
     */
    void resetPassword(ResetPasswordRequestDTO request);
}
