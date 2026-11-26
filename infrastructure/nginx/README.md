# NextMinds Nginx

Nginx is the public HTTP entry point for the NextMinds frontend and Gateway. It uses Docker DNS on the existing `nextminds` network and forwards paths without rewriting them.

```text
Client / next-minds.ir
         |
      Nginx :80
       /      \
Frontend      Gateway
  :3000        :8080 → microservices
```

| Request path | Destination |
| --- | --- |
| `/api`, `/api/...` | Gateway, including existing `/api/v1/...` routes |
| `/actuator`, `/actuator/...` | Gateway actuator endpoints |
| `/swagger-ui.html`, `/swagger-ui/...`, `/v3/api-docs`, `/v3/api-docs/...` | Gateway documentation endpoints |
| All other paths, including `/` and frontend assets | Frontend |

Gateway currently routes the Auth, User, and Admin API prefixes. Sending another API path to Gateway does not create a downstream route for it. In particular, the frontend's Vite development proxy has separate Assessment routes that Gateway does not currently declare; those paths require a Gateway route before they work through Nginx. Gateway and its downstream services continue to enforce their own security and timeouts.

`Dockerfile` builds the official Nginx Alpine image. `nginx.conf` contains shared HTTP and WebSocket configuration; `conf.d/default.conf` is rendered by the image entrypoint using the environment. Nginx forwards `Host`, `X-Real-IP`, `X-Forwarded-For`, and `X-Forwarded-Proto`, with HTTP/1.1 and WebSocket upgrades. It replaces an incoming `X-Forwarded-For` with the connecting peer address to avoid trusting a client-supplied chain. Configure a trusted real-IP chain if another proxy is deployed in front of Nginx.

## Configuration

Set these in the root `.env` or the environment running Compose. `.env.example` provides a starting point; replace its example credentials and supply the required JWT key files before starting the backend.

| Variable | Default | Purpose |
| --- | --- | --- |
| `NGINX_HTTP_PORT` | `80` | Host port mapped to Nginx container port 80. |
| `FRONTEND_HOST` | `frontend` | Frontend service DNS name or network alias on `nextminds`. |
| `FRONTEND_PORT` | `3000` | Frontend's internal HTTP port. |
| `GATEWAY_PORT` | `8080` | Gateway's internal listening port. |
| `GRAFANA_PORT` | `3001` | Host-local Grafana port; Grafana still listens on 3000 inside its container. |
| `NGINX_PROXY_CONNECT_TIMEOUT` | `3s` | Upstream connection timeout. |
| `NGINX_PROXY_READ_TIMEOUT` | `60s` | Maximum interval between upstream reads, including idle WebSockets. |
| `NGINX_PROXY_SEND_TIMEOUT` | `60s` | Maximum interval between upstream writes. |
| `NGINX_CLIENT_MAX_BODY_SIZE` | `0` | Request body limit; `0` disables Nginx's limit. Set a suitable deployment limit. |

Timeouts and sizes use Nginx syntax. For long API requests, adjust the Nginx timeout and, separately, Gateway's `GATEWAY_RESPONSE_TIMEOUT` (default `5s`) and any downstream timeouts. Increasing the Nginx timeout alone does not extend the Gateway timeout.

## Run

From the repository root:

```bash
docker compose up -d --build nginx
```

Compose starts Gateway and its declared dependencies and waits for Gateway to become healthy. Admin is not a Gateway startup dependency and must be started separately for Admin routes. Gateway, Auth, Admin, Discovery, Grafana, and Prometheus have host-local port mappings; Nginx is the public HTTP entry point. Grafana is available at `http://localhost:3001` by default. If an existing `.env` sets `GRAFANA_PORT=3000`, update it to `3001` to use the new host port.

The frontend is not currently a Compose service and is not started by this command. Nginx does not depend on frontend availability: API routes can work while frontend requests return a gateway error until the frontend is reachable. Docker resolves upstream names at request time, so the frontend can be added later without rebuilding Nginx.

For an independent Nginx instance with the network and Gateway already available:

```bash
docker build -t nextminds-nginx infrastructure/nginx
docker run -d --name nextminds-nginx-standalone --network nextminds \
  -p 8088:80 -e GATEWAY_PORT=8080 \
  -e FRONTEND_HOST=frontend -e FRONTEND_PORT=3000 nextminds-nginx
```

Use an available host port; the standalone container is separate from the Compose service.

## Connect the frontend

The existing `frontend/` is a Vite application, not currently Dockerized in the root Compose file. Add or run a frontend container on the existing `nextminds` network with the DNS name or alias `frontend`, listening on `0.0.0.0:3000` inside the container. Set `FRONTEND_HOST` and `FRONTEND_PORT` if its name or internal port differs. No frontend host port is needed for Nginx to reach it. If running Vite on the host instead, Docker must be configured with a host-reachable address; `localhost` inside Nginx refers to the Nginx container itself.

Set the frontend's `VITE_API_BASE_URL=/api` when building or starting Vite so browser requests use the same origin and Nginx routes them to Gateway. Vite embeds `VITE_` variables in the frontend bundle, so rebuild the frontend after changing build-time values. The existing `frontend/.env.example` points directly to localhost Gateway for standalone development; change the frontend's local environment for the proxied deployment. Do not place secrets in `VITE_` variables. The root `FRONTEND_URL` controls Gateway's allowed CORS origin for cross-origin clients; match it to the frontend's browser origin when cross-origin access is required.

At default ports, the proxied frontend is `http://localhost/` and the API is `http://localhost/api/`. `http://localhost:3000` is the frontend only if a separate development server is explicitly published there; Nginx does not publish it. Point `next-minds.ir` to the host and allow port 80 to use `http://next-minds.ir/` and `http://next-minds.ir/api/`. WebSocket upgrades are proxied for Vite HMR and Next.js development; configure the frontend HMR client host and public port if its development server advertises an inaccessible address.

## Logs and configuration

```bash
docker compose logs -f nginx
docker compose exec nginx nginx -t
docker compose exec nginx nginx -T
```

`nginx -T` prints the rendered configuration. To apply configuration or environment changes, rebuild and recreate Nginx with `docker compose up -d --build nginx`, then check its configuration and logs. Compose may recreate changed containers; it does not require deleting databases or volumes.

## HTTPS later

The current listener is HTTP only. Point the domain at the host, obtain certificates through the deployment's certificate manager, mount certificate and key files read-only, and add a TLS listener and HTTPS port mapping. Decide whether to redirect HTTP to HTTPS and configure trusted proxy headers if TLS terminates upstream. Never commit private keys or certificates containing secrets. Ensure the forwarded scheme reflects the actual client connection after introducing TLS.
