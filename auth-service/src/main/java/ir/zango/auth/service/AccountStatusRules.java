package ir.zango.auth.service;

import ir.zango.auth.domain.entity.UserEntity;
import ir.zango.auth.domain.enums.AccountStatusEnum;

import java.util.EnumSet;
import java.util.Set;

public final class AccountStatusRules {

    private static final Set<AccountStatusEnum> AUTHENTICATABLE_STATUSES = EnumSet.of(
            AccountStatusEnum.ACTIVE,
            AccountStatusEnum.PENDING_VERIFICATION
    );

    private AccountStatusRules() {
    }

    /**
     * A user can sign in only while the account is active or pending verification and has not been deleted.
     */
    public static boolean canAuthenticate(UserEntity user) {
        return user != null
                && user.getDeletedAt() == null
                && AUTHENTICATABLE_STATUSES.contains(user.getStatus());
    }
}
