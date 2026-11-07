from sqlalchemy.exc import OperationalError

from core.database import get_session
from main import app


def test_reports_ok_when_database_is_reachable(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


class UnreachableSession:
    def connection(self):
        raise OperationalError("connect", None, Exception("connection refused"))


def test_reports_unavailable_when_database_is_down(client):
    app.dependency_overrides[get_session] = UnreachableSession

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["detail"] == "Database is unavailable."
