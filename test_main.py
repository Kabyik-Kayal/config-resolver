import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_base_effective_config():
    response = client.get("/effective-config")
    assert response.status_code == 200
    data = response.json()
    
    # 1. Defaults: port=8000, workers=1, debug=False, log_level="info", api_key="default-secret-000"
    # 2. YAML: workers=14, debug=False, log_level="error"
    # 3. .env: APP_PORT=8655 -> port=8655, NUM_WORKERS=15 -> workers=15, APP_LOG_LEVEL=debug -> log_level="debug"
    # 4. OS env: APP_LOG_LEVEL=warning -> log_level="warning", APP_API_KEY=key-1ofuzbiwmu
    # Expected base:
    assert data["port"] == 8655
    assert data["workers"] == 15
    assert data["debug"] is False
    assert data["log_level"] == "warning"
    assert data["api_key"] == "****"

def test_single_cli_override():
    response = client.get("/effective-config?set=port=9000")
    assert response.status_code == 200
    data = response.json()
    assert data["port"] == 9000
    assert data["workers"] == 15

def test_multiple_cli_overrides():
    response = client.get("/effective-config?set=port=9000&set=debug=true&set=workers=2")
    assert response.status_code == 200
    data = response.json()
    assert data["port"] == 9000
    assert data["debug"] is True
    assert data["workers"] == 2
    assert data["api_key"] == "****"

def test_boolean_coercion():
    for val, expected in [("true", True), ("1", True), ("yes", True), ("on", True), ("TRUE", True),
                          ("false", False), ("0", False), ("no", False), ("off", False)]:
        r = client.get(f"/effective-config?set=debug={val}")
        assert r.status_code == 200
        assert r.json()["debug"] is expected, f"Failed for debug={val}"

def test_api_key_override_remains_masked():
    response = client.get("/effective-config?set=api_key=new-secret-123")
    assert response.status_code == 200
    data = response.json()
    assert data["api_key"] == "****"

def test_cors_headers():
    response = client.get("/effective-config", headers={"Origin": "https://example.com"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") in ["*", "https://example.com"]

if __name__ == "__main__":
    test_base_effective_config()
    test_single_cli_override()
    test_multiple_cli_overrides()
    test_boolean_coercion()
    test_api_key_override_remains_masked()
    test_cors_headers()
    print("ALL TESTS PASSED SUCCESSFULLY!")
