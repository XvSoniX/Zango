# Architecture

Zango runs as three Spring Boot services on one Docker network named `zango`.

```text
client
  |
  |  :8080
  v
gateway-service  ----validates RS256 JWT with the public key----
  |
  |  lb://AUTH-SERVICE
  v
auth-service  :8081
  |                \
  | jdbc            \ Eureka
  v                  v
auth-db            discovery-service :8761
```

Discovery locator is disabled. The gateway has one explicit route:

- `Path=/api/v1/auth/**` to `lb://AUTH-SERVICE`

Service names are used inside Compose. `localhost` is only a default for processes that run on the host.

## Modules

| Module | Application name | Responsibility |
| --- | --- | --- |
| `discovery-service` | `discovery-service` | Eureka server. HTTP Basic protects the registry. |
| `gateway-service` | `gateway-service` | Reactive gateway, CORS, JWT validation, authorization rules. |
| `auth-service` | `auth-service` | Identity, credentials, tokens, password reset, and roles. |

Auth registers in Eureka as `AUTH-SERVICE`.

## Request path

1. The gateway matches `zango.gateway.security.rules` in order.
2. Public routes skip authentication. Everything else needs a valid access token. Admin routes also need `ROLE_ADMIN`.
3. A request that fails validation never reaches Auth.
4. A request that passes is forwarded with its `Authorization` header.
5. Auth enforces the same boundaries again. The gateway is not the only check.

## What each service owns

Auth owns the private key, password hashes, refresh-token hashes, reset-token hashes, and role assignments.

The gateway owns only the public key. It checks signature, `RS256`, expiry, issuer, and audience. It does not issue tokens.

Discovery stores no business data.

## Data

Auth uses one PostgreSQL database, `zango_auth`, schema `public`. Hibernate validates the schema. Liquibase applies it from `auth-service/src/main/resources/db/changelog`.

Tables:

| Table | Purpose |
| --- | --- |
| `users` | Account id, status, timestamps, soft delete. |
| `credentials` | Identifier, type, Argon2 hash. Unique on type plus identifier. |
| `roles` | Role name. `ROLE_USER` and `ROLE_ADMIN` are seeded. |
| `user_roles` | Assignment of a role to a user. |
| `refresh_tokens` | SHA-256 hash, family, expiry, revocation, replacement. |
| `password_reset_tokens` | SHA-256 hash, expiry, one-time use. |

Account statuses are `PENDING_VERIFICATION`, `ACTIVE`, `INACTIVE`, and `SUSPENDED`. Registration creates `PENDING_VERIFICATION`. Sign-in is allowed for `PENDING_VERIFICATION` and `ACTIVE` when the account is not deleted.

## Errors

Auth and the gateway return `application/problem+json`.

```json
{
  "type": "http://localhost/problems/bad-request",
  "title": "Invalid request",
  "status": 400,
  "detail": "The request is not valid.",
  "instance": "/api/v1/auth/register",
  "isSuccess": false,
  "errorCode": "BAD_REQUEST",
  "correlationId": "4401740b-20f9-4866-aa25-83f9eae7b9fe"
}
```

Validation failures also include an `errors` array of `{ "field", "message" }`. Unknown JSON properties are rejected. The default message locale is Persian. Send `Accept-Language: en` for English text.

Auth error codes: `BAD_REQUEST`, `IDENTIFIER_CONFLICT`, `AUTHENTICATION_FAILED`, `UNAUTHORIZED`, `FORBIDDEN`, `NOT_FOUND`, `ROLE_CONFLICT`, `ROLE_ASSIGNMENT_CONFLICT`, `ROLE_IN_USE`, `PASSWORD_RESET_FAILED`, `TOO_MANY_REQUESTS`, `INTERNAL_SERVER_ERROR`.

## Logging

Auth logs through SLF4J. Successful sign-in, registration, token rotation, password changes, and role changes are `INFO`. Rejected authentication and authorization are `WARN`. Unexpected persistence failures include the stack trace at `ERROR`.

Passwords, access tokens, refresh tokens, reset tokens, private keys, and email addresses are not written to logs. Containers set `LOGGING_FILE_NAME` empty and log to stdout.
