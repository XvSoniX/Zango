# Zango

Zango is a community platform that connects people through dedicated spaces, starting with schools.

This repository currently contains the platform shell: service discovery, an API gateway, and the authentication service.

## Services

| Service | Port | Role |
| --- | --- | --- |
| Gateway | 8080 | Public entry point. Validates access tokens and routes `/api/v1/auth/**` to Auth. |
| Auth | 8081 | Registration, login, tokens, passwords, and roles. |
| Discovery | 8761 | Eureka registry. |
| PostgreSQL | internal | Auth database. Not published on the host. |

Clients should call the gateway. Auth is also published on `8081` for Swagger and local debugging.

## Stack

- Java 24
- Spring Boot 4.1.0
- Spring Cloud 2025.1.2
- PostgreSQL 16 and Liquibase
- RS256 JWT access tokens and hashed refresh tokens
- Argon2id passwords

## Run with Docker

Generate a matching RSA key pair before the first start. Both files are gitignored.

```bash
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out gateway-service/keys/private.pem
openssl pkey -in gateway-service/keys/private.pem -pubout -out gateway-service/keys/public.pem
chmod 644 gateway-service/keys/private.pem gateway-service/keys/public.pem
```

The private-key path must be a file. If it is missing, Docker creates a directory there and Auth will not start.

```bash
cp .env.example .env
docker compose up -d --build
```

Swagger UI: [http://localhost:8081/swagger-ui.html](http://localhost:8081/swagger-ui.html)

The path `/swagger.html` is not Swagger.

## Documentation

- [Architecture](docs/architecture.md)
- [Auth API](docs/auth-api.md)
- [Security](docs/security.md)
- [Deployment](docs/deployment.md)
