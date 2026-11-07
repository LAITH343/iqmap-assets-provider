from enum import StrEnum
from pathlib import Path
from typing import Any

import httpx


class RouteProfile(StrEnum):
    WALK = "walk"
    DRIVE = "drive"


class RoutingEngineUnavailableError(Exception):
    pass


class RoutingEngineError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class RouteNotFoundError(Exception):
    pass


class RoutingEngineClient:
    def __init__(self, base_url: str, timeout: float) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    async def route(
        self,
        graph_path: Path,
        profile: RouteProfile,
        origin: tuple[float, float],
        destination: tuple[float, float],
    ) -> dict[str, Any]:
        payload = {
            "graph_path": str(graph_path),
            "profile": profile.value,
            "from": {"lat": origin[0], "lng": origin[1]},
            "to": {"lat": destination[0], "lng": destination[1]},
        }
        try:
            response = await self._client.post("/route", json=payload)
        except httpx.HTTPError as exc:
            raise RoutingEngineUnavailableError(str(exc)) from exc

        if response.status_code == 404:
            raise RouteNotFoundError()
        if response.is_error:
            raise RoutingEngineError(response.status_code, response.text)
        return response.json()

    async def aclose(self) -> None:
        await self._client.aclose()
