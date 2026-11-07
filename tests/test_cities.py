import hashlib


def test_lists_only_cities_with_a_ready_version(client):
    response = client.get("/v1/cities")

    assert response.status_code == 200
    assert response.json() == [
        {
            "slug": "baghdad",
            "name": "Baghdad",
            "center": {"lat": 33.3, "lng": 44.4},
            "bounds": {"min_lat": 33.2, "min_lng": 44.3, "max_lat": 33.4, "max_lng": 44.5},
            "latest_version": 2,
        }
    ]


def test_latest_version_is_the_highest_ready_version(client):
    response = client.get("/v1/cities/baghdad/versions/latest")

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == 2
    assert body["files"]["graph"] == {
        "size": 100,
        "sha256": "c" * 64,
        "url": "http://testserver/v1/cities/baghdad/versions/2/files/graph",
    }
    assert set(body["files"]) == {"tiles", "places", "graph"}


def test_unknown_city_returns_404(client):
    assert client.get("/v1/cities/mosul/versions/latest").status_code == 404


def test_city_without_ready_version_returns_404(client):
    response = client.get("/v1/cities/basra/versions/latest")

    assert response.status_code == 404
    assert response.json()["detail"] == "City has no published version."


def test_unready_version_is_not_exposed(client):
    assert client.get("/v1/cities/baghdad/versions/3").status_code == 404


def test_downloads_whole_file(client, storage):
    response = client.get("/v1/cities/baghdad/versions/2/files/graph")

    assert response.status_code == 200
    assert response.content == (storage / "bundles/baghdad/2/graph.db").read_bytes()
    assert response.headers["etag"] == f'"{"c" * 64}"'
    assert response.headers["accept-ranges"] == "bytes"
    assert "baghdad-v2-graph.db" in response.headers["content-disposition"]


def test_downloads_file_in_chunks(client, storage):
    expected = (storage / "bundles/baghdad/2/graph.db").read_bytes()
    chunks = []
    for start in range(0, len(expected), 32):
        end = min(start + 31, len(expected) - 1)
        response = client.get(
            "/v1/cities/baghdad/versions/2/files/graph",
            headers={"Range": f"bytes={start}-{end}", "If-Range": f'"{"c" * 64}"'},
        )
        assert response.status_code == 206
        assert response.headers["content-range"] == f"bytes {start}-{end}/{len(expected)}"
        chunks.append(response.content)

    assert hashlib.sha256(b"".join(chunks)).digest() == hashlib.sha256(expected).digest()


def test_stale_if_range_returns_whole_file(client):
    response = client.get(
        "/v1/cities/baghdad/versions/2/files/graph",
        headers={"Range": "bytes=0-9", "If-Range": '"stale"'},
    )

    assert response.status_code == 200
    assert len(response.content) == 100


def test_head_returns_size_without_body(client):
    response = client.head("/v1/cities/baghdad/versions/2/files/graph")

    assert response.status_code == 200
    assert response.headers["content-length"] == "100"
    assert response.content == b""


def test_unknown_file_kind_is_rejected(client):
    assert client.get("/v1/cities/baghdad/versions/2/files/secrets").status_code == 422


def test_missing_file_on_disk_returns_404(client):
    assert client.get("/v1/cities/baghdad/versions/1/files/graph").status_code == 404
