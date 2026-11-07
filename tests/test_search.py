from services.places import build_match_query


def search(client, **params):
    return client.get("/v1/cities/baghdad/search", params=params)


def test_matches_name_prefixes_across_categories(client):
    response = search(client, q="hosp")

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == 2
    names = [result["name_en"] for result in body["results"]]
    assert sorted(names) == ["Hospital Pharmacy", "Ibn Sina Hospital"]


def test_matches_arabic_names(client):
    results = search(client, q="مستشفى ابن").json()["results"]

    assert [result["name_ar"] for result in results] == ["مستشفى ابن سينا"]
    assert results[0]["lat"] == 33.31
    assert results[0]["lng"] == 44.39


def test_deduplicates_places_listed_in_several_categories(client):
    results = search(client, q="sina").json()["results"]

    assert len(results) == 1


def test_skips_places_without_coordinates(client):
    names = [result["name"] for result in search(client, q="unplaced").json()["results"]]

    assert names == []


def test_filters_by_category(client):
    results = search(client, q="hospital", category="shops").json()["results"]

    assert [result["category"] for result in results] == ["shops"]


def test_unknown_category_is_rejected(client):
    assert search(client, q="hospital", category="buildings; DROP").status_code == 422


def test_respects_limit(client):
    assert len(search(client, q="hospital", limit=1).json()["results"]) == 1


def test_query_with_only_symbols_returns_nothing(client):
    response = search(client, q='"*()')

    assert response.status_code == 200
    assert response.json()["results"] == []


def test_query_terms_are_quoted_for_fts():
    assert build_match_query('ibn "sina" OR') == '"ibn"* "sina"* "OR"*'
