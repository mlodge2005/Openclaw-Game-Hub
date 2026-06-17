from __future__ import annotations

import base64
import hashlib
import json
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ED25519_SPKI_PREFIX = bytes.fromhex("302a300506032b6570032100")


@dataclass
class DeviceIdentity:
    device_id: str
    public_key_raw_b64url: str
    private_key_pem: str


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _derive_public_key_raw(public_key_pem: str) -> bytes:
    pub = serialization.load_pem_public_key(public_key_pem.encode("ascii"))
    spki = pub.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    if len(spki) == len(ED25519_SPKI_PREFIX) + 32 and spki[: len(ED25519_SPKI_PREFIX)] == ED25519_SPKI_PREFIX:
        return spki[len(ED25519_SPKI_PREFIX) :]
    return spki


def _identity_from_private_pem(private_key_pem: str) -> DeviceIdentity:
    private_key = serialization.load_pem_private_key(private_key_pem.encode("ascii"), password=None)
    assert isinstance(private_key, Ed25519PrivateKey)
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
    raw = _derive_public_key_raw(public_pem)
    device_id = hashlib.sha256(raw).hexdigest()
    return DeviceIdentity(device_id=device_id, public_key_raw_b64url=_b64url(raw), private_key_pem=private_key_pem)


def generate_device_identity() -> DeviceIdentity:
    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")
    return _identity_from_private_pem(private_pem)


def build_device_auth_payload_v3(
    *,
    device_id: str,
    client_id: str,
    client_mode: str,
    role: str,
    scopes: list[str],
    signed_at_ms: int,
    token: str,
    nonce: str,
    platform_name: str = "",
    device_family: str = "",
) -> str:
    return "|".join(
        [
            "v3",
            device_id,
            client_id,
            client_mode,
            role,
            ",".join(scopes),
            str(signed_at_ms),
            token or "",
            nonce,
            (platform_name or "").strip(),
            (device_family or "").strip(),
        ]
    )


def sign_device_payload(private_key_pem: str, payload: str) -> str:
    private_key = serialization.load_pem_private_key(private_key_pem.encode("ascii"), password=None)
    assert isinstance(private_key, Ed25519PrivateKey)
    signature = private_key.sign(payload.encode("utf-8"))
    return _b64url(signature)


def load_or_create_device_identity(path: Path) -> DeviceIdentity:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        return _identity_from_private_pem(data["private_key_pem"])
    identity = generate_device_identity()
    path.write_text(
        json.dumps(
            {
                "device_id": identity.device_id,
                "private_key_pem": identity.private_key_pem,
                "platform": platform.system().lower(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return identity


def save_device_token(path: Path, device_token: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    data["device_token"] = device_token
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_device_token(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    token = data.get("device_token")
    return token if isinstance(token, str) and token.strip() else None
