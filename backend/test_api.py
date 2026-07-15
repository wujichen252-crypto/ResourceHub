"""Test registration endpoint and show full error."""
import httpx

response = httpx.post(
    "http://localhost:8000/api/auth/register",
    json={"username": "testuser", "password": "test123456", "email": "test@test.com"},
)
print(f"Status: {response.status_code}")
print(f"Body: {response.text}")
print(f"Headers: {dict(response.headers)}")
