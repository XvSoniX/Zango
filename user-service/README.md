# user-service

Profile service of the talent assessment platform for children aged 8–16.

## Responsibilities

| Belongs to **Auth Service** | Belongs to **user-service** |
|---|---|
| Accounts, credentials, passwords, tokens, roles | Profile data: first name, last name, date of birth |

user-service never stores or validates passwords. Each profile references its authentication
account through `authUserId` (a UUID). It is a plain column with a unique constraint, **not** a
database foreign key, because the account lives in another service's database.

## Requirements

- JDK 24 (set on the parent POM)
- Maven 3.9+
- PostgreSQL, from the root `docker-compose.yml` (`user-db`)

## Configuration

Settings are in `src/main/resources/application.yml`. Database user and password have no default; set them in the environment (see the root `.env.example`).

| Variable | Default | Purpose |
|---|---|---|
| `USER_SERVICE_PORT` | `8082` | HTTP port |
| `USER_DB_HOST` | `localhost` | Database host |
| `USER_DB_PORT` | `5432` | Database port |
| `USER_DB_NAME` | `nextminds_user` | Database name |
| `USER_DB_USERNAME` | none | Database user |
| `USER_DB_PASSWORD` | none | Database password |
| `USER_DB_SCHEMA` | `public` | Schema for JPA and Liquibase |

Schema changes go through Liquibase. Hibernate `ddl-auto` is `validate`. The accepted age range is `nextminds.user.age-limits.min/max` (8 and 16).

## Run

From the repository root:

```bash
docker compose up -d user-db
mvn -pl user-service -am test
mvn -pl user-service spring-boot:run
```

Or run the jar: `java -jar target/user-service-0.0.1-SNAPSHOT.jar`.

## API (`/api/v1/users`)

| Method | Path | Description | Success |
|---|---|---|---|
| POST | `/api/v1/users` | Create a profile for an Auth Service account | 201 + `Location` |
| GET | `/api/v1/users/{id}` | Get by profile id | 200 |
| GET | `/api/v1/users/by-auth-id/{authUserId}` | Get by Auth Service account id | 200 |
| GET | `/api/v1/users?page=0&size=20&sort=lastName` | Paged list (max size 100) | 200 |
| PUT | `/api/v1/users/{id}` | Replace first name, last name, date of birth | 200 |
| DELETE | `/api/v1/users/{id}` | Delete the profile | 204 |

Create example:

```bash
curl -X POST http://localhost:8082/api/v1/users \
  -H 'Content-Type: application/json' \
  -d '{"authUserId":"3f2b8c1e-5a47-4c0e-9d1a-7b6e2f9a1c11","firstName":"Sara","lastName":"Ahmadi","dateOfBirth":"2015-04-12"}'
```

Errors use RFC 9457 `application/problem+json`:

| Status | When |
|---|---|
| 400 | Validation failure (`errors` maps field → message), malformed JSON, malformed UUID |
| 404 | Profile not found |
| 409 | A profile already exists for that `authUserId` |
| 422 | Age outside the supported range |

## Design decisions

- **`authUserId` is immutable** and unique; `PUT` cannot change it.
- **Table `users`**, because `user` is reserved in PostgreSQL.
- **UUID primary keys** avoid guessable sequential ids for children's profiles.
- **Age rule is configurable** and checked in the service against an injected `Clock`.
- **No MapStruct**: DTOs are records, mapping is one static method. Lombok is on the parent POM; this module does not use it.
- **Gateway is the security boundary**: the parent POM brings Spring Security, so this service defines a stateless filter chain that permits requests. Do not expose port 8082 publicly.

## Open assumptions

- The type of the Auth Service account id is not specified; `UUID` is assumed. If it differs, change `authUserId` in `User`, the DTOs, the repository and the controller path variable.
