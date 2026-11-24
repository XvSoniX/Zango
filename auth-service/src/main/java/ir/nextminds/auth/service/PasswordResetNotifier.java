package ir.nextminds.auth.service;

public interface PasswordResetNotifier {

    void notify(String email, String rawToken);
}
