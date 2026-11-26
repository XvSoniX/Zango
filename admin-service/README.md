# NextMinds Admin Service

Admin Service provides the administrative API for managing role definitions and user-role assignments, and for reviewing the audit trail of those changes. It acts as an orchestration layer: Auth Service owns users, roles, and assignments, while Admin Service owns its own audit database.

**Production readiness: not yet accepted.** The last recorded review on November 26, 2026 passed unit and MVC tests, but PostgreSQL integration, concurrent last-administrator protection, end-to-end traffic, and Swagger with a real token were not verified. See [Testing and limitations](#testing-and-limitations).

## Business purpose

Roles describe access categories such as `ROLE_ADMIN` or `ROLE_SUPPORT`. An administrator can create and maintain those definitions, assign an existing role to a user, remove an assignment when access is no longer needed, and inspect a user's current role names. The meaning and enforcement of an individual role outside these endpoints belong to the services that use it; creating a role does not itself grant permissions or assign it to a user.

Every accepted role-changing request must first create an audit attempt. This creates accountability for who initiated a change, what they tried to change, when, why, and what is known about the outcome. Administrators can search these records to investigate changes or uncertain results. Read-only requests do not produce audit records.

Auth prevents deletion of an assigned role and rejects removal of the last active administrator's `ROLE_ADMIN` assignment. Renaming `ROLE_ADMIN` is rejected while any active administrator has it. These protections are implemented in Auth, where the data lives; their behavior under PostgreSQL concurrency still requires integration testing. Auth currently exposes no user deletion or status-change API. Any such future path must preserve the same invariant.

## Architecture and ownership

```text
Client → Gateway → Eureka discovery → Admin → Auth → Auth PostgreSQL
                                        └──────────→ Admin PostgreSQL (audit)
```

Gateway routes `/api/v1/admin/**` to `ADMIN-SERVICE`. Admin validates the caller's JWT, authorizes the administrator, records mutation attempts locally, and forwards role operations and the caller's bearer token to Auth. Auth remains the authority for role data and performs its own authorization. There is no distributed transaction: an Auth operation can succeed even when the later Admin audit finalization fails. The two services do not share a database.

## Security and JWT

- `/api/v1/admin/**` requires a valid JWT with `ROLE_ADMIN`.
- Admin validates RS256 signatures using the configured public key, issuer, audience, timestamps, and a UUID subject. The subject identifies the administrator in the audit record.
- `/actuator/health`, its subpaths, `/actuator/prometheus`, `/swagger-ui.html`, `/swagger-ui/**`, `/v3/api-docs`, and its subpaths are public in Admin. Other paths require authentication.
- A JWT contains the roles present when it was issued. Role changes do not necessarily invalidate an already issued token; consider token lifetime when removing access.
- Do not put real credentials, tokens, or private keys in source control, documentation, logs, or examples.

## API reference

All paths below are relative to Admin or the Gateway, and all require `Authorization: Bearer <access-token>` with `ROLE_ADMIN`. Path IDs are UUIDs. Swagger provides English and Persian operation descriptions.

| Method | Path | Business effect | Success |
| --- | --- | --- | --- |
| GET | `/api/v1/admin/roles` | List role definitions from Auth. | 200, array of roles |
| POST | `/api/v1/admin/roles` | Create a unique role definition. | 201, created role |
| PUT | `/api/v1/admin/roles/{roleId}` | Replace a role's name and description. | 200, updated role |
| DELETE | `/api/v1/admin/roles/{roleId}` | Delete an unassigned role; requires a reason in the request body. | 204 |
| GET | `/api/v1/admin/users/{userId}/roles` | Retrieve a user's assigned role names. | 200, user ID and role names |
| POST | `/api/v1/admin/users/{userId}/roles` | Assign an existing role; requires a reason. | 204 |
| DELETE | `/api/v1/admin/users/{userId}/roles/{roleId}` | Revoke an assignment; requires a reason. | 204 |
| GET | `/api/v1/admin/audit-logs` | Search audit attempts with filters and pagination. | 200, page of audit records |
| GET | `/api/v1/admin/audit-logs/{auditId}` | Retrieve one audit record. | 200, audit record |

### Requests and responses

Role names are required, at most 100 characters, and must match `ROLE_[A-Z0-9_]+`. Descriptions are optional and limited to 255 characters. Create and update accept an optional audit `reason` of at most 500 characters. A successful role response contains `id`, `name`, and `description`.

```json
{
  "name": "ROLE_SUPPORT",
  "description": "Support team access category",
  "reason": "Create a role for the support team"
}
```

Assigning a role requires an existing `roleId` and a nonblank `reason` of at most 500 characters. Both DELETE operations require a JSON body containing a nonblank `reason`, also limited to 500 characters. For example:

```json
{
  "roleId": "6f1c0a3e-7b2d-4e91-9c4a-1d8e5a0b2f11",
  "reason": "User joined the support team"
}
```

The user-role read response contains `userId` and `roles`, a list of role-name strings. An audit response includes `id`, `administratorId`, `action`, `targetType`, `targetId`, `reason`, `result`, `sourceIp`, `correlationId`, `metadata`, `createdAt`, and `completedAt`. Some fields can be null, including `sourceIp`, `completedAt`, and the target ID of a pending role creation.

### Audit search

Filters are optional and combined: `administratorId`, `action`, `targetType`, `targetId`, `result`, `from`, and `to`. `targetId` requires `targetType`. Times are ISO-8601 instants; `from` is inclusive and `to` is exclusive. Actions are `ROLE_CREATED`, `ROLE_UPDATED`, `ROLE_DELETED`, `ROLE_ASSIGNED`, and `ROLE_REVOKED`; target types are `ROLE` and `USER`; results are `PENDING`, `SUCCESS`, and `FAILURE`.

`page` is zero-based and defaults to `0`; `size` defaults to `20` and is limited to `1–100`. Results use fixed ordering by `createdAt DESC, id DESC`; there is no public sort parameter. The page response contains `content`, `page`, `size`, `totalElements`, and `totalPages`.

```text
GET /api/v1/admin/audit-logs?result=PENDING&page=0&size=20
GET /api/v1/admin/audit-logs?targetType=USER&targetId=<user-uuid>&from=2026-01-01T00:00:00Z
```

### Errors

Errors use Problem Details with fields such as `type`, `title`, `status`, `detail`, `instance`, `errorCode`, and `correlationId`; validation errors can also include `errors`. Depending on the operation, responses include 400 for invalid input, 401 for missing or invalid authentication, 403 for insufficient role, 404 for an unknown resource, and 409 for an Auth conflict, including `LAST_ADMIN`. Auth rejection details are forwarded when available. A definite pre-send failure maps to 503; an uncertain downstream outcome maps to 504. An unexpected internal failure can return 500.

## Swagger and OpenAPI

When Admin is running directly on its default port, open `http://localhost:8083/swagger-ui/index.html`; the OpenAPI document is at `http://localhost:8083/v3/api-docs`. Admin's UI is not separately routed through the existing Gateway configuration. The specification defines an HTTP Bearer JWT security scheme, applies it to the administrative operations, and documents the operations in English and Persian.

To use it with a real administrator account:

1. Send `POST /api/v1/auth/login` to Auth or its configured Gateway route with the account's `identifier`, `identifierType`, and `password`; obtain `accessToken` from the response. Use your own account and keep the token private.
2. Open Admin's Swagger UI and select **Authorize**.
3. Paste the access token value without the `Bearer ` prefix. Swagger sends `Authorization: Bearer <JWT>` on protected requests.
4. Open **List roles**, choose **Try it out**, and execute it. The token must have `ROLE_ADMIN` and match Admin's configured key, issuer, and audience.

OpenAPI generation was checked with MockMvc in the last review; a real login and browser execution remain unverified.

## Database and Liquibase

Admin uses its own PostgreSQL database. Connection settings are `ADMIN_DB_HOST`, `ADMIN_DB_PORT`, `ADMIN_DB_NAME`, `ADMIN_DB_USERNAME`, `ADMIN_DB_PASSWORD`, and `ADMIN_DB_SCHEMA`. Liquibase runs `src/main/resources/db/changelog/db.changelog-master.yaml`; Hibernate validates the schema. The `admin_audit_logs` table stores structured metadata as PostgreSQL JSONB. A real PostgreSQL migration and repository test has not yet been run.

## Auth integration and audit lifecycle

The default Auth destination is `http://AUTH-SERVICE`, resolved through service discovery and load balancing. The default connection timeout is one second and response timeout is three seconds. `ADMIN_AUTH_BASE_URL`, `ADMIN_AUTH_CONNECT_TIMEOUT`, and `ADMIN_AUTH_RESPONSE_TIMEOUT` override these values. The URL host is a service ID resolved by the load balancer, not an arbitrary direct host URL. Admin forwards the caller's Authorization header, `Accept-Language` when present, and `X-Correlation-ID`.

For a mutation, Admin persists a `PENDING` attempt before contacting Auth. If the initial write fails, it does not call Auth. Once the downstream outcome is known, Admin attempts to finalize the record as `SUCCESS` or `FAILURE`:

| Metadata outcome | Meaning |
| --- | --- |
| `CONFIRMED` | Auth reported success. |
| `REJECTED` | Auth returned a rejection, typically a 4xx response. |
| `NOT_SENT` | A definite pre-send failure was identified. |
| `UNKNOWN` | The operation's outcome cannot be established, for example after a response timeout or a 5xx. |

If Auth succeeds but audit finalization fails, Admin logs and counts the failure and still returns the successful business result. The audit row can remain `PENDING`. An unexpected exception can also leave a pending row. Do not interpret `UNKNOWN` or `PENDING` as proof that Auth did nothing, and do not blindly repeat a mutation.

Read requests and requests rejected by security or validation before reaching the mutation service are not written to the audit table. The current mutation path records `sourceIp` as null; forwarded headers are not used to attribute a client IP. Request logs are not a substitute for a complete audit record.

## Audit monitoring and recovery

By default the pending monitor starts after one minute, checks every five minutes for records older than one hour, and exposes their count as `admin.audit.pending.stale`. Set `ADMIN_AUDIT_MONITOR_INITIAL_DELAY`, `ADMIN_AUDIT_MONITOR_INTERVAL`, and `ADMIN_AUDIT_STALE_AFTER` to change those durations; the stale threshold must be positive. It logs a warning when it finds records. On a query failure, it logs an error and the gauge retains its previous value, so the gauge alone does not prove monitoring is healthy. Finalization failures increment `admin.audit.finalization.failures`, tagged by downstream outcome.

Operators can search for `result=PENDING`, use the correlation ID and Auth-side evidence to investigate, and handle the business consequences manually. There is currently no API for manually finalizing an audit record or automated reconciliation. The monitor does not change audit outcomes or retry Auth operations. Configure alerts and define an operational investigation process before production use.

## Correlation ID, Gateway, and Eureka

Gateway accepts a canonical UUID in `X-Correlation-ID` or generates one for a missing or invalid value. Its filter propagates the ID and places it in the response; Gateway error responses use the established ID. Admin records it in MDC, the response, Auth requests, and audit attempts. Auth uses the established ID in its logs and errors. Isolated tests cover parts of this flow; consistent propagation through the complete deployed chain has not been proven.

Admin listens on port 8083 by default and registers with Eureka. Configure `EUREKA_SERVER_URL` for your environment. The Gateway route and service discovery require running instances of the relevant services.

## Observability

Actuator exposes health, info, and Prometheus according to the application configuration. Logs include the correlation ID. Monitor audit finalization failures, stale pending attempts, monitor query errors, Auth availability and latency, and database health. Ensure operational log access and retention comply with your environment's policies; do not log JWTs.

## Build and run

Use the repository's `.env.example` as a template for deployment values; its credentials and URLs are local-development examples and must be replaced for production. The file does not automatically configure a local Java process: export the variables or load them using your deployment tooling. For a local run from the repository root, provide an isolated Admin PostgreSQL database, the `ADMIN_DB_*` variables, `JWT_PUBLIC_KEY_PATH`, `JWT_ISSUER`, `JWT_AUDIENCE`, and `EUREKA_SERVER_URL`. Start the dependencies and run:

```bash
mvn -pl admin-service spring-boot:run
```

Run the standard Admin tests with `mvn -pl admin-service test`. The root project specifies Java 24; the last review used Java 25 and Maven 3.8.7. Never point test code at production or development data. Do not remove existing databases, containers, or volumes to run tests.

Compose reads `.env` for interpolation and explicitly passes the documented Admin settings to its containers. Compose uses the internal `admin-db:5432` address and constructs its own Eureka URL; the local-process `ADMIN_DB_HOST`, `ADMIN_DB_PORT`, and `EUREKA_SERVER_URL` examples do not override those internal values. Compose uses `JWT_PUBLIC_KEY_FILE` and `JWT_PRIVATE_KEY_FILE` as host-side mount paths, while `JWT_PUBLIC_KEY_PATH` and `JWT_PRIVATE_KEY_PATH` configure local processes. Set `SPRING_PROFILES_ACTIVE` explicitly for deployment. `GATEWAY_CONNECT_TIMEOUT_MS` and `GATEWAY_RESPONSE_TIMEOUT` control the Gateway budgets; coordinate them with Admin's Auth timeouts so the Gateway does not routinely give up first. If service ports change, update the static targets in `monitoring/prometheus.yml` as well.

## Testing and limitations

The following are historical results from November 26, 2026, not a claim that every scenario was retested after later documentation changes:

| Check | Result |
| --- | --- |
| Admin JUnit Launcher | 45 passed; includes mocked Auth, MVC security, OpenAPI JSON, and audit tests. |
| Auth JUnit Launcher | 26 passed; includes last-admin business rules with mocked repositories. |
| Gateway JUnit Launcher | 2 passed; includes filter-level correlation checks for 401/403. |
| PostgreSQL migration, JSONB, query filters, ordering, pagination, and rollback | NOT RUN; repeatable real-database integration tests remain to be built and executed. |
| Concurrent last-administrator protection on PostgreSQL | NOT RUN. Mocked repositories cannot establish concurrency safety. |
| Full Gateway → Eureka → Admin → Auth and audit database flow | NOT RUN, including real-token access, CRUD, errors, timeout, and end-to-end correlation. |
| Swagger UI with a real JWT | NOT RUN. |

The standard Maven test command failed before running tests because Surefire required an uncached `plexus-utils:1.1` artifact and Maven Central DNS resolution failed. Offline `test-compile` succeeded, and the above tests were run with JUnit Platform Launcher and a Mockito javaagent. Docker access failed with permission denied on its socket; PostgreSQL on localhost:5432 did not respond. The cause was not established as Snap or AppArmor. No existing database, container, or volume was removed.

## Remaining work and production readiness

1. Build and run isolated PostgreSQL integration tests for Liquibase, JSONB, repository queries, pagination, ordering, and transaction failures.
2. Verify last-admin protection with concurrent transactions on PostgreSQL, and ensure any future user deletion or status change uses the same invariant and locking protocol.
3. Run the complete service chain with real JWTs, including authorized and unauthorized requests, role operations, audit records, failures, correlation IDs, and Swagger.
4. Establish alerting, trusted client-IP policy, and a documented manual reconciliation process for unresolved audit attempts.
5. Restore normal Maven dependency access and execute the standard build in CI.

Until these checks and operational controls are complete, the service is **not production-ready**.
