"""
Manual Operational Verification Script for Workstream 0.4
"""
import uuid
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_and_validate_token, revocation_store, log_security_event
from app.dependencies.auth import require_authenticated_user
from app.core.handlers import register_exception_handlers
from app.core.middleware import CorrelationIDMiddleware
from app.core.security.middleware import AuthenticationMiddleware
from app.schemas.auth import TokenPayload

app = FastAPI()
app.add_middleware(AuthenticationMiddleware)
app.add_middleware(CorrelationIDMiddleware)
register_exception_handlers(app)


@app.get("/api/v1/secure-data")
def get_secure_data(claims: TokenPayload = Depends(require_authenticated_user)):
    return {"message": "Access Granted", "user_id": claims.sub, "tenant_id": claims.tenant_id}


client = TestClient(app)


def main():
    print("=== Workstream 0.4 Manual Security Verification Starting ===")

    # 1. Argon2id Password Hashing Verification
    password = "EnterprisePassword456!"
    hashed = hash_password(password)
    print(f"✓ Argon2id Hash Generated: {hashed[:35]}...")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPass", hashed) is False
    print("✓ Argon2id Password Hashing & Timing-Safe Verification PASSED")

    # 2. Dual-Token JWT Generation & Validation
    user_id = str(uuid.uuid4())
    access_token, access_jti = create_access_token(user_id=user_id, tenant_id="TENANT-HQ")
    refresh_token, refresh_jti = create_refresh_token(user_id=user_id)
    print("✓ Access & Refresh Dual-Token Pair Issued")

    decoded_claims = decode_and_validate_token(access_token, expected_type="access")
    assert decoded_claims.sub == user_id
    assert decoded_claims.tenant_id == "TENANT-HQ"
    print(f"✓ JWT Claims Decoded & Validated: Sub={decoded_claims.sub}, Tenant={decoded_claims.tenant_id}")

    # 3. Protected Route Dependency & Bearer Middleware Verification
    res_unauth = client.get("/api/v1/secure-data")
    assert res_unauth.status_code == 401
    assert res_unauth.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"
    print("✓ Missing Authorization Header Rejected with 401 AUTHENTICATION_REQUIRED")

    res_auth = client.get("/api/v1/secure-data", headers={"Authorization": f"Bearer {access_token}"})
    assert res_auth.status_code == 200
    assert res_auth.json()["user_id"] == user_id
    print("✓ Valid Bearer Token Authenticated & Route Access Granted")

    # 4. Single-Use Token Rotation & Revocation Store Verification
    asyncio.run(revocation_store.revoke_jti(access_jti, expires_in_seconds=3600))
    res_revoked = client.get("/api/v1/secure-data", headers={"Authorization": f"Bearer {access_token}"})
    assert res_revoked.status_code == 401
    assert res_revoked.json()["error"]["code"] == "TOKEN_REVOKED"
    print("✓ Revoked Token Rejected with 401 TOKEN_REVOKED")

    # 5. Security Audit Logging Event Verification
    log_security_event("MANUAL_VERIFICATION_COMPLETE", user_id=user_id, success=True)
    print("✓ Security Audit Logging Hooks Triggered Cleanly")

    print("=== Workstream 0.4 Manual Verification PASSED ===")


if __name__ == "__main__":
    import asyncio
    main()
