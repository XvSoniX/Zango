# Security

Auth issues tokens. The gateway and Auth both validate them.

## Access tokens

Access tokens are RS256 JWTs and live for 15 minutes.

| Claim | Value |
| --- | --- |
| `sub` | User id |
| `iss` | `JWT_ISSUER`, default `http://localhost:8081` |
| `aud` | `JWT_AUDIENCE`, default `zango` |
| `exp` / `iat` | Issued-at and expiry |
| `jti` | Unique token id |
| `roles` | Role names loaded from the database at issuance |

The `roles` values already include the `ROLE_` prefix. Security does not add a second prefix. `hasRole("ADMIN")` matches the authority `ROLE_ADMIN`.

There is no access-token blocklist. Logout revokes refresh tokens. An access token remains valid until it expires.

Auth keeps the private key. The gateway keeps the matching public key. Do not set `spring.security.oauth2.resourceserver.jwt.issuer-uri` on the gateway. That setting turns off the local public-key decoder. Issuer is checked with a separate validator, and both services must use the same issuer string.

## Refresh tokens

Refresh tokens are 32 random bytes, returned once, and stored as SHA-256 hex. They live for 24 hours from issuance. Rotation replaces the current token and starts a new 24-hour lifetime. Reuse of a rotated token revokes the active tokens in that family.

## Passwords

Passwords are hashed with Argon2id. Login still runs a hash comparison when the identifier does not exist, so the response time does not reveal whether the account is there.

Password change and reset update every credential for that user and revoke active refresh tokens in the same transaction.

Reset tokens are 32 random bytes, stored as SHA-256, and valid for 30 minutes. Issuing a new one consumes older active tokens. Reset consumes the presented token and any other active reset token for that user. A consumed token cannot be reused.

## Authorization rules

Gateway rules live in `gateway-service/src/main/resources/application.yml` under `zango.gateway.security.rules`. They are applied in order. The fallback is authenticated.

| Access | Meaning |
| --- | --- |
| `PUBLIC` | No token. |
| `AUTHENTICATED` | Any valid access token. |
| `ROLE` | Valid token with one of the listed authorities. |

Auth repeats the rule in `SecurityConfig`: public registration, login, refresh, logout, forgot, reset, health, and Swagger. `/api/v1/auth/admin/**` requires `ROLE_ADMIN`. Every other route requires a valid access token.

Sessions are stateless. CSRF, HTTP Basic, and form login are disabled on Auth.

## First administrator

Nothing in the API can grant the first `ROLE_ADMIN`, because that API itself requires the role. For a local database:

```bash
docker compose exec auth-db psql -U zango -d zango_auth -c "
INSERT INTO user_roles (user_id, role_id, assigned_at)
VALUES ('<user-id>', '6f1c0a3e-7b2d-4e91-9c4a-1d8e5a0b2f11', now());
"
```

`6f1c0a3e-7b2d-4e91-9c4a-1d8e5a0b2f11` is the seeded `ROLE_ADMIN` id. `ROLE_USER` is `8a4d2c1b-5e6f-4a70-8b9c-3d2e1f0a4b22`.

To mark the account active:

```bash
docker compose exec auth-db psql -U zango -d zango_auth -c "
UPDATE users
SET status = 'ACTIVE', updated_at = now()
WHERE id = '<user-id>';
"
```

`PENDING_VERIFICATION` can already sign in. Sign in again after the role insert so the new access token contains `ROLE_ADMIN`.

## Keys

```bash
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out gateway-service/keys/private.pem
openssl pkey -in gateway-service/keys/private.pem -pubout -out gateway-service/keys/public.pem
```

`*.pem` and `.env` are gitignored. The private key is mounted read-only at `/run/secrets/private.pem` in Auth. The public key is mounted read-only at `/run/secrets/public.pem` in the gateway. Neither file is copied into an image.
