package ir.zango.auth.service.impl;

import ir.zango.auth.service.PasswordResetNotifier;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

@Component
public class UnconfiguredPasswordResetNotifier implements PasswordResetNotifier {

    private static final Logger log = LoggerFactory.getLogger(UnconfiguredPasswordResetNotifier.class);

    @Override
    public void notify(String email, String rawToken) {
        log.debug("Password reset notification was not delivered because no mail provider is configured");
    }
}
