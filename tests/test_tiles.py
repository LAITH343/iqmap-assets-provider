import gzip

from conftest import TILE_BYTES

TILE_URL = "/v1/cities/baghdad/tiles/14/10397/6538.pbf"


def test_serves_tile_with_y_flipped_from_tms(client):
    response = client.get(TILE_URL)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/x-protobuf"
    assert response.headers["x-bundle-version"] == "2"
    assert response.content == gzip.decompress(TILE_BYTES)


def test_tile_keeps_gzip_encoding_for_clients(client):
    response = client.get(TILE_URL, headers={"Accept-Encoding": "gzip"})

    assert response.headers["content-encoding"] == "gzip"


def test_missing_tile_returns_no_content(client):
    response = client.get("/v1/cities/baghdad/tiles/14/10397/6539.pbf")

    assert response.status_code == 204
    assert response.content == b""


def test_out_of_range_tile_returns_404(client):
    assert client.get("/v1/cities/baghdad/tiles/1/2/0.pbf").status_code == 404


def test_matching_etag_returns_not_modified(client):
    etag = client.get(TILE_URL).headers["etag"]

    response = client.get(TILE_URL, headers={"If-None-Match": etag})

    assert response.status_code == 304
    assert response.content == b""


def test_tilejson_describes_latest_tiles(client):
    response = client.get("/v1/cities/baghdad/tiles.json")

    assert response.status_code == 200
    assert response.json() == {
        "tilejson": "3.0.0",
        "name": "Baghdad",
        "version": "2",
        "scheme": "xyz",
        "tiles": ["http://testserver/v1/cities/baghdad/tiles/{z}/{x}/{y}.pbf"],
        "format": "pbf",
        "minzoom": 0,
        "maxzoom": 14,
        "bounds": [44.3, 33.2, 44.5, 33.4],
        "center": [44.4, 33.3, 7],
        "vector_layers": [{"id": "transportation"}],
    }
