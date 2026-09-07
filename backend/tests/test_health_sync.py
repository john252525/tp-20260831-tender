from fastapi.testclient import TestClient

def test_metrics_without_token():
    from app.main import app
    client = TestClient(app)
    response = client.get('/api/v1/metrics')
    assert response.status_code == 200
    assert 'text/plain' in response.headers['content-type']
