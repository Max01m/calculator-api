from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_add():
    resp = client.post("/api/v1/add", json={"a": 2, "b": 3})
    assert resp.status_code == 200
    assert resp.json()["result"] == 5


def test_divide_by_zero():
    resp = client.post("/api/v1/divide", json={"a": 10, "b": 0})
    assert resp.status_code == 400


def test_expression():
    resp = client.post("/api/v1/calculate", json={"expression": "(2 + 3) * 4"})
    assert resp.status_code == 200
    assert resp.json()["result"] == 20


def test_expression_rejects_unsafe_code():
    resp = client.post("/api/v1/calculate", json={"expression": "__import__('os').system('ls')"})
    assert resp.status_code == 400


def test_sqrt_negative():
    resp = client.post("/api/v1/sqrt", json={"a": -4})
    assert resp.status_code == 400
