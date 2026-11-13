package ir.zango.auth.service;

import ir.zango.auth.dto.LoginRequestDTO;
import ir.zango.auth.dto.LoginResponseDTO;

public interface LoginService {

    LoginResponseDTO login(LoginRequestDTO request);
}
