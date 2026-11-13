package ir.zango.auth.service;

import ir.zango.auth.dto.LoginRequestDTO;
import ir.zango.auth.dto.LoginResponseDTO;

public interface LoginService {

    /**
     * Authenticates the identifier and issues a new access token and refresh token.
     * Unknown identifiers, bad passwords, and accounts that cannot sign in all fail the same way.
     */
    LoginResponseDTO login(LoginRequestDTO request);
}
