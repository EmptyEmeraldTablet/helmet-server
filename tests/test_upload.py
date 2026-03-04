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


def _create_device(client: TestClient) -> dict:
    token = _get_token(client)
    response = client.post(
        '/api/devices',
        json={"name": "upload-test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    return response.json()["data"]


def test_upload_flow(client: TestClient) -> None:
    device = _create_device(client)

    files = {
        "file": ("test.jpg", b"fake-image-bytes", "image/jpeg"),
    }
    data = {
        "device_id": device["id"],
    }
    response = client.post(
        '/api/upload',
        files=files,
        data=data,
        headers={"X-API-Key": device["api_key"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["status"] == "completed"
    assert payload["data"]["task_id"]
    assert payload["data"]["detections"]
    assert payload["data"]["has_violation"] is True

    token = _get_token(client)
    alerts = client.get('/api/alerts', headers={"Authorization": f"Bearer {token}"})
    assert alerts.status_code == 200
    assert any(item["device_id"] == device["id"] for item in alerts.json()["data"]["items"])
