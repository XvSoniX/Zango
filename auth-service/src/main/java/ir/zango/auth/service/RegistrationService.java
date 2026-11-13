package ir.zango.auth.service;

import ir.zango.auth.dto.RegistrationRequestDTO;
import ir.zango.auth.dto.RegistrationResponseDTO;

public interface RegistrationService {

    RegistrationResponseDTO register(RegistrationRequestDTO request);
}
