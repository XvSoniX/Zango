# Deployment

One Dockerfile at the repository root builds every service. The image uses a JDK stage for Maven and a JRE stage at runtime. The process runs as the non-root user `zango`.

```bash
docker build --build-arg SERVICE=discovery-service --build-arg PORT=8761 -t zango-discovery .
docker build --build-arg SERVICE=gateway-service --build-arg PORT=8080 -t zango-gateway .
docker build --build-arg SERVICE=auth-service --build-arg PORT=8081 -t zango-auth .
```

Compose builds the same images:

```bash
cp .env.example .env
docker compose up -d --build
```

## Startup order

1. Discovery becomes healthy.
2. PostgreSQL becomes healthy.
3. Auth waits for both, runs Liquibase, then registers with Eureka.
4. The gateway waits for Discovery and Auth.

Auth and PostgreSQL restart unless stopped. Auth stops gracefully, with a 30-second stop grace period.

Health checks call `GET /actuator/health` on Discovery, the gateway, and Auth. PostgreSQL uses `pg_isready`.

## Network

| From | To | Address |
| --- | --- | --- |
| Auth | PostgreSQL | `auth-db:5432` |
| Auth | Eureka | `http://discovery-service:8761/eureka/` |
| Gateway | Eureka | `http://discovery-service:8761/eureka/` |
| Gateway | Auth | `lb://AUTH-SERVICE` |

Host ports are `8761`, `8080`, and `8081`. PostgreSQL stays on the Docker network. Its data is the named volume `zango-auth-db`.

Database name, user, and password come from `AUTH_DB_NAME`, `AUTH_DB_USERNAME`, and `AUTH_DB_PASSWORD`. Compose defaults are the local values in `.env.example`. Override them outside development.

## Configuration

Copy `.env.example` to `.env`. Compose reads it from the repository root. Do not commit `.env`.

| Variable | Used for |
| --- | --- |
| `EUREKA_USERNAME`, `EUREKA_PASSWORD` | Registry credentials. |
| `AUTH_DB_*` | PostgreSQL connection. Inside Compose, the host is forced to `auth-db`. |
| `JWT_PRIVATE_KEY_PATH` | Host path of the Auth signing key. |
| `JWT_PUBLIC_KEY_PATH` | Host path of the gateway verification key. |
| `JWT_ISSUER`, `JWT_AUDIENCE`, `JWT_ACCESS_TOKEN_TTL`, `JWT_KEY_ID` | Access-token settings. Issuer and audience must match on Auth and the gateway. |
| `REFRESH_TOKEN_TTL` | Refresh-token lifetime. Default `24h`. |
| `PASSWORD_RESET_TTL` | Reset-token lifetime. Default `30m`. |
| `PASSWORD_RESET_RATE_LIMIT` | Requests allowed per window. Default `5`. |
| `PASSWORD_RESET_RATE_LIMIT_WINDOW` | Rate-limit window. Default `15m`. |
| `FRONTEND_URL` | Gateway CORS origin. Default `http://localhost:3000`. |

## Local process without Compose

Run Discovery, then PostgreSQL, then Auth, then the gateway. Point `AUTH_DB_HOST` at `localhost` and set `AUTH_DB_USERNAME` and `AUTH_DB_PASSWORD`. Auth has no default database password. Place the private key at `gateway-service/keys/private.pem`, or set `JWT_PRIVATE_KEY_PATH`.

```bash
./mvnw -pl discovery-service spring-boot:run
./mvnw -pl auth-service spring-boot:run
./mvnw -pl gateway-service spring-boot:run
```
