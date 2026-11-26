# Deployment

One Dockerfile at the repository root builds every service. The image uses a JDK stage for Maven and a JRE stage at runtime. The process runs as the non-root user `nextminds`.

```bash
docker build --build-arg SERVICE=discovery-service --build-arg PORT=8761 -t nextminds-discovery .
docker build --build-arg SERVICE=gateway-service --build-arg PORT=8080 -t nextminds-gateway .
docker build --build-arg SERVICE=auth-service --build-arg PORT=8081 -t nextminds-auth .
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

Host ports are `8761`, `8080`, and `8081`. PostgreSQL stays on the Docker network. Its data is the named volume `nextminds-auth-db`.

Database name, user, and password come from `AUTH_DB_NAME`, `AUTH_DB_USERNAME`, and `AUTH_DB_PASSWORD`. Compose defaults are the local values in `.env.example`. Override them outside development.

## Configuration

Copy `.env.example` to `.env`. Compose reads it from the repository root. Do not commit `.env` or `*.pem`.

The `dev` profile keeps local defaults, including the sample Eureka password in application configuration. The `stage` and `prod` profiles do not. They require `EUREKA_SERVER_URL`, and Discovery requires `EUREKA_USERNAME` and `EUREKA_PASSWORD`, with no password embedded in those profiles. Compose does not substitute a password when one of the variables below is missing.

Development-only lifetime defaults remain: `JWT_ACCESS_TOKEN_TTL` `15m`, `REFRESH_TOKEN_TTL` `24h`, `PASSWORD_RESET_TTL` `30m`, `PASSWORD_RESET_RATE_LIMIT` `5`, `PASSWORD_RESET_RATE_LIMIT_WINDOW` `15m`.

### Required for production

Set `SPRING_PROFILES_ACTIVE=prod` and replace every sample value from `.env.example`.

| Variable | Required value |
| --- | --- |
| `EUREKA_SERVER_URL` | Registry URL, including credentials, for example `http://user:password@discovery-service:8761/eureka/`. |
| `EUREKA_USERNAME`, `EUREKA_PASSWORD` | Discovery basic-auth credentials. Required by Compose and by the stage and prod Discovery profiles. |
| `AUTH_DB_PASSWORD` | Auth database password. No application or Compose default. |
| `ADMIN_DB_PASSWORD` | Admin database password. No application or Compose default. |
| `USER_DB_PASSWORD` | User database password. No Compose default. |
| `AUTH_DB_USERNAME`, `ADMIN_DB_USERNAME`, `USER_DB_USERNAME` | Database users. Compose defaults the user name to `nextminds` for local use; set them explicitly in production. |
| `JWT_PRIVATE_KEY_FILE` | Host path of the Auth signing key. Compose default: `gateway-service/keys/private.pem`. |
| `JWT_PUBLIC_KEY_FILE` | Host path of the matching public key. Compose default: `gateway-service/keys/public.pem`. |
| `JWT_ISSUER`, `JWT_AUDIENCE` | Must be the same on Auth, Gateway, and Admin. |
| `FRONTEND_URL` | The one browser origin allowed by Gateway CORS. Credentials are not allowed. |
| `GRAFANA_ADMIN_USER`, `GRAFANA_ADMIN_PASSWORD` | Required by Compose. Grafana has no built-in password. |

PostgreSQL is not published on a host port. Application ports are published for local use. In production, publish only the Gateway and terminate TLS at the edge proxy. Prod and stage set `server.forward-headers-strategy: framework`, so that proxy must send `X-Forwarded-Proto`. The application does not enable HSTS, because local HTTP would then be cached as HTTPS. Gateway responses set `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and `Referrer-Policy: no-referrer`.

## Local process without Compose

Run Discovery, then PostgreSQL, then Auth, then the gateway. Point `AUTH_DB_HOST` at `localhost` and set `AUTH_DB_USERNAME` and `AUTH_DB_PASSWORD`. Auth has no default database password. Place the private key at `gateway-service/keys/private.pem`, or set `JWT_PRIVATE_KEY_PATH`.

```bash
./mvnw -pl discovery-service spring-boot:run
./mvnw -pl auth-service spring-boot:run
./mvnw -pl gateway-service spring-boot:run
```
