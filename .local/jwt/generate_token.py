import jwt
import time
import uuid
from pathlib import Path
import os

base_url = os.getenv("JWT_SERVER_URL", "http://localhost:8090")
# Assurez-vous que le fichier oidc-private-key.pem est présent dans le même dossier
private_key = Path("oidc-private-key.pem").read_text()

now = int(time.time())
payload = {
    "exp": now + 360000,
    "iat": now,
    "auth_time": now - 60,
    "jti": str(uuid.uuid4()),
    "iss": base_url + "/auth/realms/AP-HP",
    "aud": ["api-fhir", "cohort360", "api-portal"],
    "sub": "test-user-id",
    "username": "4208892",  # Requis par le backend Cohort360
    "preferred_username": "4208892",
    "name": "Nicolas Puchois 4208892",
    "email": "test.user@example.local",
    "b64": True,
    "typ": "Bearer",
    "azp": "cohort360-local",
    "allowed-origins": [base_url + "/auth/realms/master", base_url + "/auth/realms/AP-HP"],
}
token = jwt.encode(payload, private_key, algorithm="RS256", headers={"typ": "JWT", "kid": "local-test-key"})

print(token)
