# Auth API

Base path: `/api/v1/auth`

Through the gateway: `http://localhost:8080/api/v1/auth`

Directly on Auth: `http://localhost:8081/api/v1/auth`

Interactive reference: [http://localhost:8081/swagger-ui.html](http://localhost:8081/swagger-ui.html)

OpenAPI JSON: `http://localhost:8081/v3/api-docs`

Swagger is served by Auth, not by the gateway route. Use `swagger-ui.html`, not `swagger.html`.

## Identifiers

`identifierType` is `USERNAME` or `EMAIL`.

- `USERNAME` is a non-blank value with no whitespace.
- `EMAIL` must look like an email address.
- The field name is `identifier`. `username` is rejected.

Passwords are required, at most 128 characters, and stored only as Argon2id hashes.

## Public endpoints

### Register

`POST /register` returns `201`.

```json
{
  "identifier": "xvsonix",
  "identifierType": "USERNAME",
  "password": "toor@123"
}
```

```json
{
  "id": "bb9e9a5c-54ac-4d4f-8799-ad02539ac1bf",
  "identifier": "xvsonix",
  "identifierType": "USERNAME",
  "status": "PENDING_VERIFICATION"
}
```

The new user receives `ROLE_USER`. A duplicate identifier returns `409 IDENTIFIER_CONFLICT`.

### Login

`POST /login` returns `200`.

```json
{
  "identifier": "xvsonix",
  "identifierType": "USERNAME",
  "password": "toor@123"
}
```

The response includes `accessToken`, `tokenType` (`Bearer`), `expiresAt`, `expiresIn`, `refreshToken`, and `refreshExpiresAt`. A wrong password, an unknown identifier, and an account that cannot sign in all return `401 AUTHENTICATION_FAILED`.

### Refresh

`POST /refresh`

```json
{ "refreshToken": "<refresh-token>" }
```

Returns a new access token and a new refresh token. The presented refresh token is revoked. Presenting an already rotated token revokes the rest of that token family.

### Logout

`POST /logout` returns `204`.

```json
{ "refreshToken": "<refresh-token>" }
```

Unknown and already revoked tokens still return `204`.

### Forgot password

`POST /password/forgot` returns `204` whether or not the email exists.

```json
{ "email": "person@example.com" }
```

More than 5 requests for the same email inside 15 minutes returns `429 TOO_MANY_REQUESTS`. No mail provider is configured, so the reset token is not delivered. The raw token is not logged.

### Reset password

`POST /password/reset` returns `204`.

```json
{
  "token": "<reset-token>",
  "newPassword": "new-password"
}
```

A missing, expired, or already used token returns `400 PASSWORD_RESET_FAILED`. The message does not say which of those happened.

## Authenticated endpoints

Send `Authorization: Bearer <accessToken>`. The subject is the user id inside the token. The body cannot name another user.

| Method | Path | Result |
| --- | --- | --- |
| `GET` | `/roles/me` | Role names for the current user. |
| `POST` | `/logout-all` | `204`. Revokes every active refresh token for the current user. |
| `POST` | `/password/change` | `204`. Checks the current password, replaces every credential hash, and revokes refresh tokens in the same transaction. |

Change password body:

```json
{
  "currentPassword": "toor@123",
  "newPassword": "new-password"
}
```

A wrong current password returns `401 AUTHENTICATION_FAILED`.

## Admin endpoints

These require an access token whose `roles` claim contains `ROLE_ADMIN`. Registration only grants `ROLE_USER`. The first admin is assigned in the database. See [Security](security.md).

Log in again after the assignment. An older access token does not gain the role.

| Method | Path | Result |
| --- | --- | --- |
| `GET` | `/admin/roles` | All roles. |
| `POST` | `/admin/roles` | `201`. Creates a role. |
| `PUT` | `/admin/roles/{roleId}` | Updates the name and description. |
| `DELETE` | `/admin/roles/{roleId}` | `204`. Refuses while the role is still assigned. |
| `GET` | `/admin/users/{userId}/roles` | Roles held by that user. |
| `POST` | `/admin/users/{userId}/roles` | `204`. Assigns a role. |
| `DELETE` | `/admin/users/{userId}/roles/{roleId}` | `204`. Removes that assignment. |

Create body:

```json
{
  "name": "ROLE_MODERATOR",
  "description": "Optional description"
}
```

Role names match `ROLE_[A-Z0-9_]+`. Assign body:

```json
{ "roleId": "6f1c0a3e-7b2d-4e91-9c4a-1d8e5a0b2f11" }
```

Duplicate names return `409 ROLE_CONFLICT`. A second assignment of the same role returns `409 ROLE_ASSIGNMENT_CONFLICT`. Deleting an assigned role returns `409 ROLE_IN_USE`. An unknown user or role returns `404 NOT_FOUND`.

A valid token without `ROLE_ADMIN` receives `403 FORBIDDEN`. A missing or invalid token receives `401 UNAUTHORIZED`.
