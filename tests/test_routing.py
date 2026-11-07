import pytest

from services.routing import RouteNotFoundError, RouteProfile, RoutingEngineError, RoutingEngineUnavailableError


def route(client, **params):
    return client.get("/v1/cities/baghdad/route", params=params)


def test_forwards_route_request_to_engine(client, routing_engine, storage):
    response = route(client, **{"from": "33.30,44.40", "to": "33.35, 44.45", "profile": "drive"})

    assert response.status_code == 200
    assert response.headers["x-bundle-version"] == "2"
    assert response.json()["distance_m"] == 1200.0
    assert routing_engine.calls == [
        {
            "graph_path": storage / "bundles" / "baghdad" / "2" / "graph.db",
            "profile": RouteProfile.DRIVE,
            "from": (33.30, 44.40),
            "to": (33.35, 44.45),
        }
    ]


@pytest.mark.parametrize("value", ["33.3", "abc,44.4", "33.3;44.4", ""])
def test_rejects_malformed_coordinates(client, value):
    assert route(client, **{"from": value, "to": "33.35,44.45", "profile": "walk"}).status_code == 422


def test_rejects_points_outside_coverage(client):
    response = route(client, **{"from": "30.5,47.8", "to": "33.35,44.45", "profile": "walk"})

    assert response.status_code == 422
    assert "outside" in response.json()["detail"]


def test_rejects_unknown_profile(client):
    assert route(client, **{"from": "33.3,44.4", "to": "33.35,44.45", "profile": "fly"}).status_code == 422


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (RouteNotFoundError(), 404),
        (RoutingEngineUnavailableError("down"), 503),
        (RoutingEngineError(500, "boom"), 502),
    ],
)
def test_maps_engine_failures(client, routing_engine, error, status_code):
    routing_engine.error = error

    assert route(client, **{"from": "33.3,44.4", "to": "33.35,44.45", "profile": "walk"}).status_code == status_code
