# Admin Service API and integration contract

Phase 3 contract for NextMinds Admin Service. This document defines the initial public API and the Auth Service delegation. It does not add the service, clients, or configuration.

The audit record follows [Admin Service domain and database design](admin-service-domain.md).

## 1. Purpose and scope

Admin Service exposes platform administration under `/api/v1/admin`. The initial API is a facade over the role operations Auth already implements, plus read access to `admin_audit_logs`.

Clients call Admin Service. Admin Service calls Auth with the same administrator bearer token. Role data stays in Auth. Audit data stays in Admin Service.

## 2. Approved architecture and security assumptions

- Every Admin endpoint requires a valid access token whose `roles` claim contains `ROLE_ADMIN`.
- `sub` is the administrator UUID. There is no local administrator record.
- The gateway forwards `Authorization`. Admin Service forwards that same header to Auth.
- There is no service account, client-credentials flow, or second token signer.
- Access tokens, refresh tokens, and `Authorization` values are never logged.
- The audit attempt commits before the Auth call. Auth success is not described as rolled back when audit finalization fails.
- Read-only calls do not create audit rows.
- No audit update or delete API exists.
- Fine-grained `admin.*` permissions are not part of this contract.

JWT checks match Auth and the gateway: RS256, issuer, audience `nextminds`, expiry, `roles` taken as authorities with no extra prefix. `hasRole("ADMIN")` matches `ROLE_ADMIN`.

Unknown JSON properties are rejected. Auth already sets `spring.jackson.deserialization.fail-on-unknown-properties` to `true`. Admin Service uses the same rule.

## 3. Public API overview

Base path: `/api/v1/admin`.

Through the gateway, once the route exists: `http://localhost:8080/api/v1/admin`.

Directly on Admin Service: `http://localhost:8083/api/v1/admin`.

| Method | Path | Audit | Auth call |
| --- | --- | --- | --- |
| `GET` | `/roles` | no | `GET /api/v1/auth/admin/roles` |
| `POST` | `/roles` | `ROLE_CREATED` | `POST /api/v1/auth/admin/roles` |
| `PUT` | `/roles/{roleId}` | `ROLE_UPDATED` | `PUT /api/v1/auth/admin/roles/{roleId}` |
| `DELETE` | `/roles/{roleId}` | `ROLE_DELETED` | `DELETE /api/v1/auth/admin/roles/{roleId}` |
| `GET` | `/users/{userId}/roles` | no | `GET /api/v1/auth/admin/users/{userId}/roles` |
| `POST` | `/users/{userId}/roles` | `ROLE_ASSIGNED` | `POST /api/v1/auth/admin/users/{userId}/roles` |
| `DELETE` | `/users/{userId}/roles/{roleId}` | `ROLE_REVOKED` | `DELETE /api/v1/auth/admin/users/{userId}/roles/{roleId}` |
| `GET` | `/audit-logs` | no | none |
| `GET` | `/audit-logs/{auditId}` | no | none |

There is no `GET /roles/{roleId}`. Auth has no role-by-id API.

Successful bodies are the resource itself. They do not use an `isSuccess` envelope. Auth already returns its DTOs this way. Errors use `application/problem+json`.

## 4. Role management

Authority for every endpoint in this section: `ROLE_ADMIN`.

`roleId` is a UUID. A malformed path UUID is `400 BAD_REQUEST`.

### `GET /api/v1/admin/roles`

Lists every role. Admin Service returns Auth's body unchanged.

Auth orders by name ascending and returns a JSON array, not a page. Admin Service does not add pagination.

Response `200`:

```json
[
  {
    "id": "6f1c0a3e-7b2d-4e91-9c4a-1d8e5a0b2f11",
    "name": "ROLE_ADMIN",
    "description": null
  }
]
```

Fields are Auth's `RoleResponseDTO`: `id` (UUID), `name` (string), `description` (string or null).

No audit record.

### `POST /api/v1/admin/roles`

Creates a role. Admin Service forwards only `name` and `description`.

Request:

```json
{
  "name": "ROLE_MODERATOR",
  "description": "Optional description",
  "reason": "Optional justification"
}
```

Validation, matching Auth:

| Field | Rule |
| --- | --- |
| `name` | Required, not blank, at most 100 characters, must match `ROLE_[A-Z0-9_]+`. |
| `description` | Optional. At most 255 characters. Auth stores a blank description as null. |
| `reason` | Optional. Trimmed. Blank becomes null. At most 500 characters. |

Auth trims `name` after validation. A name with surrounding spaces fails the pattern before that trim. Admin Service applies the same validation and does not invent extra name rules.

Success `201` is Auth's `RoleResponseDTO`:

```json
{
  "id": "bb9e9a5c-54ac-4d4f-8799-ad02539ac1bf",
  "name": "ROLE_MODERATOR",
  "description": "Optional description"
}
```

Audit: `ROLE_CREATED`, `targetType` `ROLE`, `targetId` null until success. Success finalization requires `id` from this body and then stores that id as `targetId`. Metadata on success: `downstream` `auth-service`, `downstreamOutcome` `CONFIRMED`, `roleId`, `roleName`.

Definite Auth errors today: `409 ROLE_CONFLICT` when the name exists, `400 BAD_REQUEST` for validation Auth still rejects.

### `PUT /api/v1/admin/roles/{roleId}`

Updates the role name and description. The body uses the same fields and validation as create.

Auth returns the updated `RoleResponseDTO` with `200`. An unknown `roleId` is `404 NOT_FOUND`. A name owned by a different role is `409 ROLE_CONFLICT`.

Audit: `ROLE_UPDATED`, `targetType` `ROLE`, `targetId` is the path id. The reason is optional.

Auth's response contains the new id, name, and description. It does not contain the previous name or description, and Auth has no get-by-id call. Success metadata therefore contains `downstream`, `downstreamOutcome` `CONFIRMED`, `roleId`, `roleName`, and `description`. It does not contain `previousName` or `previousDescription`.

### `DELETE /api/v1/admin/roles/{roleId}`

Deletes a role that is not assigned.

Auth's delete has no body and returns `204` with an empty body. Admin Service still requires a reason, so the Admin request body is:

```json
{
  "reason": "Role is no longer used"
}
```

`reason` is required, trimmed, non-blank, and at most 500 characters. Admin Service validates it before the audit insert. The Auth call remains a body-less delete.

Audit: `ROLE_DELETED`, `targetType` `ROLE`, `targetId` is the path id. Success metadata: `downstream`, `downstreamOutcome` `CONFIRMED`, `roleId`. Auth does not return the role name.

An unknown role is `404 NOT_FOUND`. A role that is still assigned is `409 ROLE_IN_USE`. Auth does not protect the last `ROLE_ADMIN`. Admin Service does not add that protection.

## 5. User role management

Authority for every endpoint in this section: `ROLE_ADMIN`.

`userId` and `roleId` are Auth UUIDs. Admin Service does not load a local user. A malformed path UUID is `400 BAD_REQUEST`.

### `GET /api/v1/admin/users/{userId}/roles`

Reads the role names Auth stores for that user. No audit record.

Response `200`, Auth's `UserRolesResponseDTO`:

```json
{
  "userId": "bb9e9a5c-54ac-4d4f-8799-ad02539ac1bf",
  "roles": ["ROLE_USER", "ROLE_ADMIN"]
}
```

`roles` is a list of role names, not role ids. An unknown user is `404 NOT_FOUND`. A known user with no roles returns `200` and an empty `roles` array. Registration normally assigns `ROLE_USER`, so an empty list only happens after every assignment has been revoked.

### `POST /api/v1/admin/users/{userId}/roles`

Assigns a role.

```json
{
  "roleId": "6f1c0a3e-7b2d-4e91-9c4a-1d8e5a0b2f11",
  "reason": "Grant platform administration"
}
```

| Field | Rule |
| --- | --- |
| `roleId` | Required UUID. This is the only field forwarded to Auth. |
| `reason` | Required, trimmed, non-blank, at most 500 characters. |

Auth's body is `{ "roleId": "..." }`. Auth returns `204` and an empty body.

Audit: `ROLE_ASSIGNED`, `targetType` `USER`, `targetId` is `userId`. Metadata `roleId` is the request role id. Auth does not return the role name on this call, so metadata does not add `roleName` unless it was already known without another Auth call. This contract does not perform an extra lookup.

An unknown user or unknown role is `404 NOT_FOUND`. A duplicate assignment is `409 ROLE_ASSIGNMENT_CONFLICT`.

### `DELETE /api/v1/admin/users/{userId}/roles/{roleId}`

Revokes that assignment.

Admin body:

```json
{
  "reason": "Remove platform administration"
}
```

`reason` follows the same required rule as assign. Auth's delete has no body and returns `204`.

Audit: `ROLE_REVOKED`, `targetType` `USER`, `targetId` is `userId`. Metadata includes `roleId` from the path.

An unknown user, unknown role, or missing assignment is `404 NOT_FOUND`. Auth uses the same not-found outcome for a missing assignment as for a missing role. Admin Service preserves that status and `errorCode`.

## 6. Audit log reads

Authority: `ROLE_ADMIN`. These reads do not create audit rows. There is no `PUT`, `PATCH`, or `DELETE`.

### `GET /api/v1/admin/audit-logs`

Returns one page of audit attempts, newest first.

Query parameters:

| Parameter | Type | Rule |
| --- | --- | --- |
| `administratorId` | UUID | Optional. |
| `action` | string | Optional. One of the five catalog actions. |
| `targetType` | string | Optional. `ROLE` or `USER`. |
| `targetId` | UUID | Optional. Requires `targetType`. |
| `result` | string | Optional. `PENDING`, `SUCCESS`, or `FAILURE`. |
| `from` | instant | Optional. Inclusive lower bound on `createdAt`. |
| `to` | instant | Optional. Exclusive upper bound on `createdAt`. |
| `page` | integer | Optional. Default `0`. Minimum `0`. |
| `size` | integer | Optional. Default `20`. Minimum `1`. Maximum `100`. |

Instants are ISO-8601 with `Z` or an explicit offset, for example `2026-11-24T12:00:00Z`. Values are compared as absolute instants. `from` must be less than or equal to `to` when both are present. A page past the end returns `200` and an empty `content` array.

The sort is fixed: `createdAt` descending, then `id` descending. Clients do not pass a sort parameter.

Response `200`:

```json
{
  "content": [
    {
      "id": "3d6c2a10-0d1e-4f2a-9b7c-1a2b3c4d5e6f",
      "administratorId": "bb9e9a5c-54ac-4d4f-8799-ad02539ac1bf",
      "action": "ROLE_ASSIGNED",
      "targetType": "USER",
      "targetId": "8c1d9e20-1111-4222-8333-444455556666",
      "reason": "Grant platform administration",
      "result": "SUCCESS",
      "sourceIp": null,
      "correlationId": "4401740b-20f9-4866-aa25-83f9eae7b9fe",
      "metadata": {
        "downstream": "auth-service",
        "downstreamOutcome": "CONFIRMED",
        "roleId": "6f1c0a3e-7b2d-4e91-9c4a-1d8e5a0b2f11"
      },
      "createdAt": "2026-11-24T12:00:00Z",
      "completedAt": "2026-11-24T12:00:01Z"
    }
  ],
  "page": 0,
  "size": 20,
  "totalElements": 1,
  "totalPages": 1
}
```

`totalPages` is `0` when `totalElements` is `0`.

The page object is a proposed Admin Service shape. Auth does not paginate, and the repository has no existing page envelope to copy.

List and detail return the same audit fields, including `metadata`. Secrets stay out of `metadata` because the write path refuses them. The read path returns the stored object and does not add fields.

`FAILURE` with `downstreamOutcome` `UNKNOWN` means the Auth result was not confirmed. Clients must not treat that row as proof that Auth rejected the change.

### `GET /api/v1/admin/audit-logs/{auditId}`

Returns one audit object, the same fields as a list element, with `200`. An unknown `auditId` is `404 NOT_FOUND`. A malformed UUID is `400 BAD_REQUEST`.

## 7. Request and response conventions

`Content-Type` for JSON bodies is `application/json`. `Accept` for success calls is `application/json`. Error responses are `application/problem+json`.

The default message locale is Persian. `Accept-Language: en` selects English. Admin Service forwards `Accept-Language` to Auth unchanged.

### Correlation

The header is `X-Correlation-ID`.

If the incoming value is a canonical UUID, Admin Service keeps it. Otherwise it generates a new UUID. This matches the gateway filter. Admin Service sends that id to Auth, stores it on the audit row when an attempt is written, returns it in the response header, and copies it into the problem `correlationId`.

The header and the problem property are the same value. The current gateway problem writer mints a new UUID inside the problem body. Admin Service does not copy that behavior.

### Success

Status codes follow Auth for delegated calls: `200` for reads and role update, `201` for role create, `204` for assign, revoke, and role delete. `204` has no body.

Audit reads return `200` and a JSON body.

### Errors

Problem fields match Auth and the gateway:

```json
{
  "type": "http://localhost/problems/bad-request",
  "title": "Invalid request",
  "status": 400,
  "detail": "The submitted request is invalid.",
  "instance": "/api/v1/admin/roles",
  "isSuccess": false,
  "errorCode": "BAD_REQUEST",
  "correlationId": "4401740b-20f9-4866-aa25-83f9eae7b9fe"
}
```

The example text is the existing English Auth message. Persian is the default.

Validation failures add `errors`:

```json
{
  "errors": [
    {
      "field": "reason",
      "message": "Reason is required."
    }
  ]
}
```

`field` and `message` match Auth's validation entries. A missing required reason uses this `400` response and does not call Auth.

| Situation | Status | `errorCode` |
| --- | --- | --- |
| Missing or invalid bearer token | `401` | `UNAUTHORIZED` |
| Authenticated caller without `ROLE_ADMIN` | `403` | `FORBIDDEN` |
| Malformed JSON, unknown property, or bean validation failure | `400` | `BAD_REQUEST` |
| Unknown audit id, or Auth `NOT_FOUND` | `404` | `NOT_FOUND` |
| Auth conflict | `409` | Auth's code: `ROLE_CONFLICT`, `ROLE_ASSIGNMENT_CONFLICT`, or `ROLE_IN_USE` |
| Auth confirmed another `4xx` or `5xx` problem | Auth's status | Auth's `errorCode` |
| Auth call timed out or ended without a confirmed result | `504` | `DOWNSTREAM_OUTCOME_UNKNOWN` |
| Auth could not be connected to | `503` | `DOWNSTREAM_UNAVAILABLE` |
| Audit insert failed, or any other unexpected local failure | `500` | `INTERNAL_SERVER_ERROR` |

`401` also sets `WWW-Authenticate: Bearer`, as Auth does.

`DOWNSTREAM_OUTCOME_UNKNOWN` is an Admin Service code. Its detail must say that Admin Service could not confirm whether Auth applied the change. It must not say the change was rejected.

## 8. Auth Service integration

The repository has no service-to-service client. The gateway is WebFlux and calls Auth with `lb://AUTH-SERVICE`. Admin Service should be a servlet application, like Auth.

Recommended client: Spring `RestClient` with a `@LoadBalanced` builder. The load-balancer dependency is `spring-cloud-starter-loadbalancer`, which the gateway already uses. OpenFeign is not added.

Eureka application name is `auth-service`. The gateway route id is `AUTH-SERVICE`. The load-balanced base URL is `http://AUTH-SERVICE`, matching that route. A direct base URL is `http://localhost:8081` when Admin Service runs on the host without discovery. Docker uses the Eureka client, as Auth and the gateway do. The exact property names belong to a later configuration phase.

Timeouts, proposed so Admin Service can record the outcome inside the gateway's five-second response budget:

| Timeout | Value |
| --- | --- |
| Connection | 2 seconds |
| Response | 4 seconds |

The gateway today uses a 3 second connect timeout and a 5 second response timeout.

Each Auth request sets:

| Header | Value |
| --- | --- |
| `Authorization` | The incoming bearer token, unchanged. |
| `X-Correlation-ID` | The id chosen for this Admin request. |
| `Accept-Language` | Forwarded when the client sent it. |
| `Accept` | `application/json` |
| `Content-Type` | `application/json` when a body is sent. |

Admin Service maps its own request types to Auth's body. The Auth body for create and update is `name` and `description`. The Auth body for assign is `roleId`. Deletes send no body. `reason` is never sent to Auth, because Auth's DTOs do not contain it and unknown properties fail deserialization.

Responses are deserialized into Admin-owned types that mirror the known Auth fields: `id`, `name`, `description` for a role, and `userId`, `roles` for a user's roles. A create or update success object without `id` is an uncertain outcome, not a success.

No Auth call is retried automatically. See section 12.

## 9. Audit lifecycle and failure scenarios

Mutating calls use this sequence.

1. Authenticate the caller and require `ROLE_ADMIN`.
2. Validate the body and path, including a required reason.
3. Insert and commit `PENDING`.
4. Call the matching Auth endpoint with the administrator token.
5. Finalize that same row once.
6. Return the client response.

Validation failures stop at step 2. They leave no audit row.

### Audit insert fails

Auth is not called. The client receives `500 INTERNAL_SERVER_ERROR`.

### Auth returns a definite error

Finalize `FAILURE` with:

```json
{
  "downstream": "auth-service",
  "downstreamOutcome": "REJECTED",
  "httpStatus": 409,
  "errorCode": "ROLE_IN_USE"
}
```

Return Auth's status and `errorCode` to the client, with `instance` set to the Admin path. Title and detail stay Auth's localized messages. If writing this `FAILURE` row fails, the client still receives Auth's error. The error log records the audit id and that Auth rejected the call.

### Auth succeeds

Finalize `SUCCESS` with `downstreamOutcome` `CONFIRMED` and the ids described in sections 4 and 5. Then return Auth's success status and body.

For `ROLE_CREATED`, `SUCCESS` is allowed only when the response `id` is present. That id becomes `targetId`. A success body without `id` is finalized as `FAILURE` with `downstreamOutcome` `UNKNOWN` and `failureType` `MISSING_ROLE_ID`. Admin Service does not call Auth again.

### Timeout or uncertain outcome

A timeout, a dropped connection after the request was sent, or an unreadable success body is finalized as `FAILURE` once the call has ended:

```json
{
  "downstream": "auth-service",
  "downstreamOutcome": "UNKNOWN",
  "failureType": "TIMEOUT"
}
```

`failureType` is `TIMEOUT`, `CONNECTION_FAILED`, or `MISSING_ROLE_ID`. `CONNECTION_FAILED` means no HTTP response was received. The client receives `504 DOWNSTREAM_OUTCOME_UNKNOWN`, except a pure connect failure before a request is established, which is `503 DOWNSTREAM_UNAVAILABLE`. Neither response says the mutation was rejected. Admin Service does not call Auth again.

A row left `PENDING` because the process stopped is unchanged from the domain design. It is not completed by this API.

### Auth succeeds and finalization fails

The client receives the successful Auth status and body. The response does not say the Auth change was rolled back. Admin Service does not send a compensating Auth call. The error log includes the audit id, correlation id, and action, and omits the token.

## 10. Gateway and security responsibilities

Three checks stay in place.

| Layer | Duty |
| --- | --- |
| Gateway | Validates the JWT. For `/api/v1/admin/**`, requires authority `ROLE_ADMIN`. Forwards `Authorization` and the correlation id. |
| Admin Service | Validates the JWT again and requires `ROLE_ADMIN` on every endpoint in this contract. |
| Auth Service | Requires `ROLE_ADMIN` again on `/api/v1/auth/admin/**`. |

The gateway rule is not in `gateway-service` configuration yet. The expected rule, using the existing `access: ROLE` form, is every method on `/api/v1/admin/**` with authority `ROLE_ADMIN`. This phase does not change that file.

A request rejected by the gateway never reaches Admin Service. A request that passes the gateway is checked again by Admin Service. Auth remains the last check on role data.

## 11. Error mapping

Local failures use Admin Service messages in the existing `error.<CODE>.title` and `error.<CODE>.detail` form.

Delegated failures keep Auth's status, `errorCode`, title, and detail. Admin Service replaces `instance` with the public Admin path and replaces `correlationId` with the Admin request id. It does not return Auth's path, stack traces, or raw body.

| Auth result | Client result | Audit result |
| --- | --- | --- |
| `201` or `200` with a role id | Same status and role body | `SUCCESS` |
| `204` | `204` | `SUCCESS` |
| `400 BAD_REQUEST` | `400 BAD_REQUEST` | `FAILURE` / `REJECTED` |
| `401 UNAUTHORIZED` | `401 UNAUTHORIZED` | `FAILURE` / `REJECTED` |
| `403 FORBIDDEN` | `403 FORBIDDEN` | `FAILURE` / `REJECTED` |
| `404 NOT_FOUND` | `404 NOT_FOUND` | `FAILURE` / `REJECTED` |
| `409` and one of the role conflict codes | Same `409` and code | `FAILURE` / `REJECTED` |
| `500 INTERNAL_SERVER_ERROR` from Auth | `500` with Auth's code | `FAILURE` / `REJECTED` |
| Timeout or unreadable outcome | `504 DOWNSTREAM_OUTCOME_UNKNOWN` | `FAILURE` / `UNKNOWN` |
| Connection failed before a response | `503 DOWNSTREAM_UNAVAILABLE` | `FAILURE` / `UNKNOWN` |

An Auth `401` or `403` on a delegated call means Auth rejected the forwarded administrator token. Admin Service reports that status. It does not replace it with a success.

## 12. Retry and timeout policy

Admin Service does not automatically retry any Auth call.

A timeout does not prove that Auth skipped the mutation. A second attempt can create a different result: a second create can conflict or create another role, a second assign returns `409`, and a second delete or revoke returns `404` after the first one succeeded. Update is idempotent in Auth, and a second update would still be a second audit attempt. The initial client therefore sends one Auth request per Admin request.

Read calls are safe for the human client to repeat. The initial Admin client still does not retry them, so timeout handling stays one path.

The response timeout is 4 seconds. When it fires, the audit result is `FAILURE` with `downstreamOutcome` `UNKNOWN` and `failureType` `TIMEOUT`.

## 13. Out of scope

This contract does not define APIs for user listing or search, profiles, account status, blocking, session revocation, forced password reset, one-step administrator creation, permissions, schools, students, parents, teachers, support, platform configuration, or dashboard statistics.

Those operations have no Auth or User Service API to delegate to, or they belong to a later phase. Admin Service will not store local copies in order to imitate them.

`GET /api/v1/admin/roles/{roleId}` is also out of scope, because Auth cannot supply one role by id.

## 14. Open decisions and recommendations

Proposed here, and still worth an explicit yes:

1. Delete and revoke accept a JSON body whose only field is `reason`. Auth itself receives no body. A query-string reason would land in access logs.
2. Audit pages use `content`, `page`, `size`, `totalElements`, and `totalPages`, with `page` starting at `0`.
3. `from` is inclusive and `to` is exclusive. `targetId` is rejected unless `targetType` is present.
4. Uncertain Auth outcomes use `504 DOWNSTREAM_OUTCOME_UNKNOWN`. Connect failures use `503 DOWNSTREAM_UNAVAILABLE`. Confirmed Auth problems pass through Auth's status and `errorCode`.
5. The Auth client is a load-balanced `RestClient` aimed at `http://AUTH-SERVICE`, with a 2 second connect timeout and a 4 second response timeout, and with no automatic retry.
6. Update and delete metadata omit previous values and role names that Auth does not return. Admin Service does not list every role first in order to fill those fields.

Existing Auth behavior that this facade preserves:

- Role list is a full array ordered by name, not a page.
- User role reads return names, not role ids.
- A missing assignment and a missing role are both `404 NOT_FOUND`.
- Deleting an assigned role is `409 ROLE_IN_USE`.
- Nothing stops revocation of the last `ROLE_ADMIN`.
