package ir.nextminds.auth.service;

import ir.nextminds.auth.dto.RegistrationRequestDTO;
import ir.nextminds.auth.dto.RegistrationResponseDTO;

public interface RegistrationService {

    /**
     * Creates a pending user, stores the Argon2 password hash, and assigns {@code ROLE_USER}.
     */
    RegistrationResponseDTO register(RegistrationRequestDTO request);
}
