from fastapi.testclient import TestClient


def _get_token(client: TestClient) -> str:
    response = client.post(
        '/api/auth/login',
        json={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    return payload["data"]["access_token"]


def test_health(client: TestClient) -> None:
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_auth_refresh(client: TestClient) -> None:
    token = _get_token(client)
    response = client.post('/api/auth/refresh', headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["access_token"]


def test_devices_crud(client: TestClient) -> None:
    token = _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = client.post('/api/devices', json={"name": "test-device"}, headers=headers)
    assert create_resp.status_code == 200
    created = create_resp.json()["data"]
    assert created["api_key"]
    device_id = created["id"]

    list_resp = client.get('/api/devices', headers=headers)
    assert list_resp.status_code == 200
    assert any(item["id"] == device_id for item in list_resp.json()["data"])

    update_resp = client.put(
        f'/api/devices/{device_id}',
        json={"name": "updated-device", "status": "active"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["data"]["name"] == "updated-device"


def test_settings_stats_alerts(client: TestClient) -> None:
    token = _get_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    settings_resp = client.get('/api/settings', headers=headers)
    assert settings_resp.status_code == 200

    update_resp = client.put(
        '/api/settings',
        json={"max_queue_size": 5, "alert_webhook_enabled": False},
        headers=headers,
    )
    assert update_resp.status_code == 200

    stats_resp = client.get('/api/stats/summary', headers=headers)
    assert stats_resp.status_code == 200

    alerts_resp = client.get('/api/alerts', headers=headers)
    assert alerts_resp.status_code == 200
