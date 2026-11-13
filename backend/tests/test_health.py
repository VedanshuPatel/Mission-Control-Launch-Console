"""Health endpoint must report the fake provider in tests."""


def test_health_reports_fake_provider(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["provider"] == "fake"
