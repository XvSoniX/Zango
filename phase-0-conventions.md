# User Service — Phase 0: Project Context and Architectural Alignment

**Service:** user-service
**Phase:** 0 (documentation only, no code changes)
**Status:** Draft, awaiting review and approval

## 1. Purpose

This document lists the architectural conventions that User Service must follow to stay aligned with the NextMinds platform. It is the Phase 0 deliverable of the development roadmap (`user-service/aida-readme.md`).

**Sources reviewed:** root `pom.xml`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `README.md`, `docs/*` (architecture, security, auth-api, deployment), `auth-service`, `gateway-service`, `discovery-service`, `consulting-service` and the current `user-service` module.

**Restrictions (from the roadmap).** No refactoring of unrelated services. No change to Auth Service. No change to Gateway behavior. No new infrastructure. This document changes no code; the mismatches found in section 4 are only reported.

## 2. Conventions

### 2.1 Parent POM and module layout

- Root POM: `ir.nextminds:nextminds:0.0.1-SNAPSHOT`, packaging `pom`, parent `spring-boot-starter-parent 4.1.0`.
- Properties: `java.version=24`, `spring-cloud.version=2025.1.2`, `lombok.version=1.18.48`. Spring Cloud BOM is imported in `dependencyManagement`.
- Dependencies inherited by every module: `spring-boot-starter-actuator`, `spring-boot-starter-security`, `lombok` (provided, annotation processor configured), `spring-boot-starter-test` (test).
- Each service is a module with parent `ir.nextminds:nextminds` and no versions of its own for managed libraries. Services declare their own starters (web, validation, data-jpa, liquibase, eureka client, PostgreSQL runtime).
- Library versions not managed by the parent are pinned in the module that needs them (Auth pins `springdoc-openapi-starter-webmvc-ui 3.2.0` and `bcprov-jdk18on 1.84`).
- Build entry point is the Maven wrapper at the repository root (`./mvnw -pl <module> ...`).

### 2.2 Java and Spring Boot versions

Java 24, Spring Boot 4.1.0, Spring Cloud 2025.1.2, PostgreSQL 16 (Docker image), Liquibase. `user-service` inherits all of these and must not override them.

### 2.3 Package naming

- Base package: `ir.nextminds.<service>` (`ir.nextminds.auth`, `ir.nextminds.gateway`, `ir.nextminds.discovery`, `ir.nextminds.user`).
- Auth layout (the reference implementation): `config`, `controller`, `domain.entity`, `domain.enums`, `dto`, `exception`, `repository`, `security`, `service`, `service.impl`.
- Main class: `<Service>ServiceApplication` in the base package.
- Planned user-service layout (README): `entity`, `repository`, `service`, `controller`, `dto`, `config`. See O-5 about `domain.entity` versus `entity`.

### 2.4 DTO naming

Auth uses Java records with the suffix `DTO`: `RegistrationRequestDTO`, `RegistrationResponseDTO`, `LoginRequestDTO`, `RoleResponseDTO`. Pattern: `<Action><Subject>RequestDTO` / `<Subject>ResponseDTO`. Validation messages use message keys (`{registration.identifier.required}`) resolved from `i18n/messages*.properties`. Entities are named `<Name>Entity` and enums `<Name>Enum`.

### 2.5 Exception handling and RFC 9457 errors

Auth and the Gateway return `application/problem+json` built from Spring `ProblemDetail`:

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

- Every error carries the extension members `isSuccess` (always `false`), `errorCode` and `correlationId`.
- Validation errors add `errors`: an **array** of `{ "field", "message" }`.
- Errors are declared in an enum (`AuthErrorCode`, `GatewayErrorCode`) holding the HTTP status and a `type` URI of the form `http://localhost/problems/<kebab-code>`.
- A single `@RestControllerAdvice` (`AuthExceptionHandler`) maps domain exceptions (`...Exception`) to error codes. Message texts come from `MessageSource` keys `error.<CODE>.title` and `error.<CODE>.detail`.
- Default locale is Persian (`fa`); `Accept-Language: en` returns English. Messages live in `i18n/messages.properties`, `messages_fa.properties`, `messages_en.properties`.
- `X-Correlation-ID` header: the Gateway sets it on request and response; services reuse it or generate a UUID.
- `spring.jackson.deserialization.fail-on-unknown-properties: true`.
- Security failures (401/403) go through a dedicated handler that writes the same format.

### 2.6 API response structure

- Base path `/api/v1/<domain>`; Gateway routes `/api/v1/users/**` to `lb://USER-SERVICE`.
- Successful responses return the DTO directly with no envelope (`RegistrationResponseDTO` returned with `201`; `204` for operations without a body).
- Success responses have no `isSuccess` field; `isSuccess` appears only in error bodies.

### 2.7 JWT and security architecture

- Auth issues RS256 access tokens (TTL 15 minutes) signed with a private key. Gateway validates with the public key.
- Claims: `sub` = user id (UUID), `iss` = `JWT_ISSUER` (default `http://localhost:8081`), `aud` = `JWT_AUDIENCE` (default `nextminds`), `iat`, `exp`, `jti`, `roles` (list; values already include the `ROLE_` prefix).
- The principal is the `sub` claim. Ownership comes from the token, never from the request body.
- Gateway checks signature, algorithm, expiry, issuer and audience. It forwards the `Authorization` header unchanged. It does not add user-identity headers.
- Gateway rules are in `nextminds.gateway.security.rules` (`PUBLIC`, `AUTHENTICATED`, `ROLE`). The fallback is `anyExchange().authenticated()`.
- Auth re-validates tokens (`oauth2ResourceServer` with a `JwtAuthenticationConverter`, `@EnableMethodSecurity`). Documentation states: "The gateway is not the only check."
- Stateless sessions, CSRF/basic/form login disabled. `/actuator/health` is public.
- No access-token blocklist; logout revokes refresh tokens.
- Account ids: Auth generates the user UUID (`@GeneratedValue` on `UserEntity.id`). Account statuses: `PENDING_VERIFICATION`, `ACTIVE`, `INACTIVE`, `SUSPENDED`.

### 2.8 Docker conventions

- One root `Dockerfile` builds any module: `--build-arg SERVICE=<module> --build-arg PORT=<port>`. Multi-stage (`eclipse-temurin:24-jdk` build, `24-jre` runtime), non-root user `nextminds` (uid 10001), `curl` installed for health checks, `MaxRAMPercentage=75`.
- `docker-compose.yml` (network `nextminds`): per-service database `<name>-db` (`postgres:16`, named volume `nextminds-<name>-db`, `pg_isready` health check), `restart: unless-stopped`, `stop_grace_period: 30s`, `SERVER_SHUTDOWN: graceful`, `SPRING_LIFECYCLE_TIMEOUT_PER_SHUTDOWN_PHASE: 20s`, `depends_on` with `service_healthy`, health check `curl /actuator/health`, `LOGGING_FILE_NAME: ""` (logs to stdout).
- Configuration comes from the root `.env` (copied from `.env.example`). Compose forces the database host to the DB container name.
- `user-service` and `user-db` are already defined in `docker-compose.yml` following this pattern. See O-1 for the build gap.

### 2.9 Eureka

- Client config is identical in every service: `prefer-ip-address: true`, `instance-id: ${spring.application.name}:${server.port}`, `defaultZone: ${EUREKA_SERVER_URL:http://root:toor123@localhost:8761/eureka/}`, `register-with-eureka: true`, `fetch-registry: true`.
- Registry is protected by HTTP Basic (`EUREKA_USERNAME` / `EUREKA_PASSWORD`, defaults `root` / `toor123`). Compose builds `EUREKA_SERVER_URL` from them.
- Application names are lower-case kebab (`auth-service`); Eureka shows them upper-case and the Gateway uses `lb://AUTH-SERVICE`, so User Service is `lb://USER-SERVICE`.
- Discovery locator is disabled; every route is explicit.
- Management exposes `health,info`; `show-details: never`.

### 2.10 PostgreSQL and Liquibase

- One database per service (`nextminds_auth`, `nextminds_user`), schema from `<SVC>_DB_SCHEMA` (default `public`). Hibernate `ddl-auto: validate`.
- Master changelog `classpath:db/changelog/db.changelog-master.yaml` includes `changes/NNN-description.yaml` with `relativeToChangelogFile: true`.
- Changesets: id equals the file stem (`001-create-users`), YAML format, numbered sequentially, one concern per file (create table, seed data).
- Changeset `author`: Auth uses `nextminds`.
- Table names plural snake_case (`users`, `roles`); constraints are named (`pk_users`, `uk_...`); timestamps `timestamp(6) with time zone`; ids `uuid`.
- Entities use `Instant` for timestamps (Auth `UserEntity.assignCreatedAt(Instant)`).

### 2.11 Configuration, environment variables and logging

- Variable naming: `<SERVICE>_<SETTING>` (`AUTH_DB_HOST`, `USER_DB_HOST`, `AUTH_SERVICE_PORT`, `USER_SERVICE_PORT`, `AUTH_LOG_LEVEL`, `USER_LOG_LEVEL`). Database user and password have no default in `application.yml`.
- Profiles `dev`, `stage`, `prod` via `SPRING_PROFILES_ACTIVE` (default `dev`); the profile files only change log levels (`dev` is DEBUG for the service package).
- Custom properties live under `nextminds.<service>.*` (`nextminds.auth.jwt.*`); Auth binds them with `@ConfigurationProperties` classes in `config` (`JwtProperties`, `RefreshTokenProperties`).
- Logging: SLF4J. No passwords, tokens, keys or email addresses in logs. Log file `logs/<name>/<service>.log`, disabled in containers.

### 2.12 Existing behavior that must be preserved

- Auth, Gateway and Discovery behavior and routes (restriction: none of them is modified).
- The existing `user-service` behavior documented in its README: profile CRUD under `/api/v1/users`, immutable unique `authUserId`, configurable age range 8 to 16, current `permitAll` security chain behind the Gateway.

## 3. Boundary rules for every later phase

1. Auth owns identity; User owns profile data.
2. Profile UUID must equal the UUID generated by Auth (specification 2.3).
3. No password hashes, refresh tokens or roles in this service.
4. No access to the Auth database; no cross-database foreign keys.
5. One phase at a time; no next phase without explicit approval.
6. Unresolved product decisions are documented, not guessed.

## 4. Mismatches and open points

These were found by comparing user-service with the rest of the repository. None was changed in Phase 0.

| ID | Topic | Observation | Affected area / needed |
|---|---|---|---|
| O-1 | Build and Docker | `user-service` is **not** listed in the root POM `<modules>`, and the root `Dockerfile` copies only the discovery, gateway, auth and consulting `pom.xml` files. `docker compose build user-service` therefore cannot resolve the module. Docs (`README.md`, `architecture.md`, `deployment.md`) also do not mention User Service. | Root POM and Dockerfile belong to the project lead; a separate approved change is needed. |
| O-2 | Port conflict | `consulting-service` already uses default port `8082` (`CONSULTING_SERVICE_PORT:8082`), the same as `user-service`. | Decide which service keeps 8082 before both run together. |
| O-3 | Error format | The README of user-service describes `errors` as a field-to-message **map** and uses a 422 for age violations. Auth and Gateway use an **array** of `{field, message}` plus `isSuccess`, `errorCode`, `correlationId`, enum error codes and i18n messages. Status 422 has no counterpart in `AuthErrorCode`. | Bring user-service errors to the convention (2.5), and decide the code for the age rule (400 or 422). |
| O-4 | Naming style | Auth uses `...DTO`, `...Entity`, `...Enum`, `domain.entity`, `service.impl`. user-service plans `entity` and unsuffixed DTO records. Changeset author is `zango` in user-service and `nextminds` in Auth. `consulting-service` also uses a different base package (`ir.zango`). | Confirm the convention; follow Auth. |
| O-5 | Leftover test package | `src/test` contains classes under both `ir.nextminds.user` and `com.example.userservice`; main code uses `ir.nextminds.user`. An earlier standalone prototype (`com.example`, own Spring Boot parent, no Liquibase) is not part of the platform. | Remove the old package in an approved step. |
| O-6 | Profile id | The existing schema uses a separate profile `id` plus `auth_user_id`. The specification (2.3) requires the profile UUID to be the Auth UUID, and Auth generates ids. | Decision before Phases 2 and 3. |
| O-7 | Security | `SecurityConfig` is `permitAll`, and the Gateway currently routes `/api/v1/users/**` with the fallback rule (authenticated). Auth also re-validates tokens ("not the only check"), so User Service is expected to do the same. `spring-boot-starter-oauth2-resource-server` is not yet in the user-service POM. | Implemented in Phase 12; no change now. |
| O-8 | Identity propagation | Gateway forwards only the `Authorization` header. The user id must be read from the JWT `sub` claim. | Phase 12 design. |
| O-9 | Observability | Auth ships springdoc/Swagger; user-service has none. Not required by the roadmap until Phase 19. | Phase 19. |
| O-10 | Profile creation flow | REST orchestration, events or client orchestration is undecided (specification 10.2). Not implemented. | Decision before Phase 17. |

## 5. Phase completion report

- **Phase:** 0, Project Context and Architectural Alignment.
- **Summary:** NextMinds conventions documented from the actual repository; mismatches in user-service listed.
- **Files added:** `user-service/docs/phase-0-conventions.md` (this file).
- **Files modified:** none.
- **Domain decisions:** none.
- **Architectural decisions:** none; existing conventions are recorded as-is.
- **Deferred requirements:** all points in section 4.
- **Dependencies on future phases:** O-6 (Phases 2 and 3), O-7 and O-8 (Phase 12), O-9 (Phase 19), O-10 (Phase 17).
- **Changes to approved scope:** none.

Waiting for explicit approval before starting Phase 1.
