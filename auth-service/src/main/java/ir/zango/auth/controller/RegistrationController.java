package ir.zango.auth.controller;

import ir.zango.auth.dto.RegistrationRequestDTO;
import ir.zango.auth.dto.RegistrationResponseDTO;
import ir.zango.auth.service.RegistrationService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/auth")
@RequiredArgsConstructor
public class RegistrationController {

    private final RegistrationService registrationService;

    @PostMapping("/register")
    @ResponseStatus(HttpStatus.CREATED)
    public RegistrationResponseDTO register(@Valid @RequestBody RegistrationRequestDTO request) {
        return registrationService.register(request);
    }
}
