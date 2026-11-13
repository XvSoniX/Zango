package ir.zango.auth.service.impl;

import ir.zango.auth.service.PasswordResetNotifier;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

@Component
@Slf4j
public class UnconfiguredPasswordResetNotifier implements PasswordResetNotifier {

    /**
     * Records that delivery was skipped. The email and the raw token are intentionally omitted.
     */
    @Override
    public void notify(String email, String rawToken) {
        log.debug("Password reset notification was not delivered because no mail provider is configured");
    }
}
