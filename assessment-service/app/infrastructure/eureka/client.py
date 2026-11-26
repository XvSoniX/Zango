import asyncio
import socket
from typing import Optional
import httpx
from app.config import settings
from app.infrastructure.logging.logger import logger

class EurekaClient:
    """
    Asynchronous Eureka Client compatible with Spring Cloud Eureka Registry.
    Handles service registration, periodic heartbeat lease renewal, and graceful deregistration.
    """
    def __init__(self):
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._is_registered: bool = False
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def is_registered(self) -> bool:
        return self._is_registered

    def _resolve_ip(self) -> str:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"

    def _build_instance_id(self) -> str:
        return f"{settings.EUREKA_INSTANCE_HOST}:{settings.EUREKA_INSTANCE_PORT}"

    def _get_registration_payload(self) -> dict:
        instance_id = self._build_instance_id()
        ip_addr = self._resolve_ip()
        return {
            "instance": {
                "instanceId": instance_id,
                "hostName": settings.EUREKA_INSTANCE_HOST,
                "app": settings.EUREKA_APP_NAME.upper(),
                "ipAddr": ip_addr,
                "status": "UP",
                "overriddenStatus": "UNKNOWN",
                "port": {"$": settings.EUREKA_INSTANCE_PORT, "@enabled": "true"},
                "securePort": {"$": 443, "@enabled": "false"},
                "countryId": 1,
                "dataCenterInfo": {
                    "@class": "com.netflix.appinfo.InstanceInfo$DefaultDataCenterInfo",
                    "name": "MyOwn"
                },
                "leaseInfo": {
                    "renewalIntervalInSecs": settings.EUREKA_RENEWAL_INTERVAL_SECS,
                    "durationInSecs": settings.EUREKA_DURATION_SECS
                },
                "metadata": {
                    "framework": "FastAPI",
                    "version": settings.APP_VERSION
                },
                "homePageUrl": f"http://{settings.EUREKA_INSTANCE_HOST}:{settings.EUREKA_INSTANCE_PORT}/",
                "statusPageUrl": f"http://{settings.EUREKA_INSTANCE_HOST}:{settings.EUREKA_INSTANCE_PORT}/docs",
                "healthCheckUrl": f"http://{settings.EUREKA_INSTANCE_HOST}:{settings.EUREKA_INSTANCE_PORT}/health"
            }
        }

    async def start(self) -> None:
        """Starts the Eureka client and registers with the Eureka registry."""
        if not settings.EUREKA_ENABLED:
            logger.info("Eureka registration is disabled via EUREKA_ENABLED=false.")
            return

        self._client = httpx.AsyncClient(timeout=10.0)
        await self.register()

        # Start periodic background heartbeat task
        if self._is_registered:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def register(self) -> bool:
        """Sends registration POST request to Eureka server."""
        url = settings.EUREKA_SERVER_URL.rstrip("/") + f"/apps/{settings.EUREKA_APP_NAME.upper()}"
        payload = self._get_registration_payload()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            response = await self._client.post(url, json=payload, headers=headers)
            if response.status_code in (204, 200, 201):
                self._is_registered = True
                logger.info(f"Successfully registered with Eureka as '{settings.EUREKA_APP_NAME}' at {url} (status: {response.status_code})")
                return True
            else:
                logger.warning(f"Eureka registration returned unexpected status code {response.status_code}: {response.text}")
                return False
        except Exception as e:
            logger.warning(f"Could not connect to Eureka server at {url}: {e}. Service will continue without Eureka.")
            self._is_registered = False
            return False

    async def send_heartbeat(self) -> bool:
        """Sends periodic PUT request to renew lease."""
        instance_id = self._build_instance_id()
        url = settings.EUREKA_SERVER_URL.rstrip("/") + f"/apps/{settings.EUREKA_APP_NAME.upper()}/{instance_id}"
        headers = {"Accept": "application/json"}

        try:
            response = await self._client.put(url, headers=headers)
            if response.status_code == 200:
                logger.debug(f"Eureka lease renewed for instance {instance_id}")
                return True
            elif response.status_code == 404:
                logger.warning("Eureka returned 404 for heartbeat; re-registering instance...")
                return await self.register()
            else:
                logger.warning(f"Eureka heartbeat returned status code {response.status_code}")
                return False
        except Exception as e:
            logger.debug(f"Failed to send Eureka heartbeat: {e}")
            return False

    async def _heartbeat_loop(self) -> None:
        """Background loop renewing lease at renewal interval."""
        interval = max(5, settings.EUREKA_RENEWAL_INTERVAL_SECS)
        while True:
            try:
                await asyncio.sleep(interval)
                await self.send_heartbeat()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected error in Eureka heartbeat loop: {e}")

    async def stop(self) -> None:
        """Gracefully cancels heartbeat and deregisters from Eureka."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        if self._is_registered and self._client:
            instance_id = self._build_instance_id()
            url = settings.EUREKA_SERVER_URL.rstrip("/") + f"/apps/{settings.EUREKA_APP_NAME.upper()}/{instance_id}"
            try:
                response = await self._client.delete(url)
                logger.info(f"Gracefully deregistered instance {instance_id} from Eureka (status: {response.status_code})")
            except Exception as e:
                logger.warning(f"Failed to deregister from Eureka on shutdown: {e}")
            finally:
                self._is_registered = False

        if self._client:
            await self._client.aclose()
            self._client = None

eureka_client = EurekaClient()
