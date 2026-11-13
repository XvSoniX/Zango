package ir.zango.auth.service;

import ir.zango.auth.dto.RegistrationRequestDTO;
import ir.zango.auth.dto.RegistrationResponseDTO;

public interface RegistrationService {

    /**
     * Creates a pending user, stores the Argon2 password hash, and assigns {@code ROLE_USER}.
     */
    RegistrationResponseDTO register(RegistrationRequestDTO request);
}
