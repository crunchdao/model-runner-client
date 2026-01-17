import base64
import json
from dataclasses import dataclass
from typing import AnyStr

import base58
from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography.hazmat.primitives.asymmetric import ed25519


class AuthError(Exception):
    """Base error for auth / delegation verification."""


def wallet_verify(wallet_pub_bytes: bytes, message_bytes: bytes, signature: bytes) -> bool:
    """
    Verify wallet signature over message_bytes using Ed25519 (Solana).
    """
    try:
        pub = ed25519.Ed25519PublicKey.from_public_bytes(wallet_pub_bytes)
        pub.verify(signature, message_bytes)
        return True
    except Exception:
        return False


def decode_signed_message(message_bytes: bytes) -> dict:
    """
    Decode the JSON payload signed by the wallet.
    Expected shape:
      {
        "cert_pub": "<base64-encoded TLS client public key>",
        "model_id": "...",
        "expires_at": 1735689600,
        ...
      }
    """
    return json.loads(message_bytes.decode("utf-8"))


def load_pubkey_from_pem_cert(pem_cert: AnyStr) -> bytes:
    cert = x509.load_pem_x509_certificate(pem_cert)

    pub = cert.public_key()

    return pub.public_bytes(
        encoding=Encoding.DER,
        format=PublicFormat.SubjectPublicKeyInfo,
    )


@dataclass
class DelegationInfo:
    """
    Result of verifying the wallet delegation + optional TLS binding.
    """
    message_bytes: bytes  # raw JSON bytes
    payload: dict  # decoded JSON
    wallet_pub_bytes: bytes  # 32 bytes Ed25519 wallet key
    cert_pub_bytes: bytes  # TLS public key bytes from payload (decoded)
    wallet_pub_b58: str  # original wallet pub (b58)
    model_id: str | None = None
    expires_at: int | None = None

def verify_wallet_delegation(
    *,
    message_b64: str,
    signature_b64: str,
    wallet_pub_b58: str,
    expected_wallet_pub_b58: str,
    tls_pub: bytes,
    expected_hotkey: str,
    expected_model_id: str | None = None
) -> DelegationInfo:
    """
    Generic verification logic, independent of gRPC.

    - Decodes base64/base58.
    - Checks wallet pubkey matches expected (if provided).
    - Verifies wallet signature over message_bytes.
    - Decodes JSON and extracts cert_pub (base64) and optional expires_at/model_id.
    - If tls_pub_from_transport is provided, verifies it matches cert_pub from payload.

    Raises AuthError on any problem.
    Returns DelegationInfo on success.
    """
    # 1) Decode message + signature + wallet pub
    try:
        message_bytes = base64.b64decode(message_b64)
        signature = base64.b64decode(signature_b64)
        wallet_pub_bytes = base58.b58decode(wallet_pub_b58)
    except Exception as e:
        raise AuthError(f"Invalid encoding in auth data: {e}") from e

    # 2) Wallet pubkey check (bind delegation to a specific wallet)
    if wallet_pub_b58 != expected_wallet_pub_b58:
        raise AuthError("The provided wallet public key does not match the expected public key.")

    # 3) Check signature
    if not wallet_verify(wallet_pub_bytes, message_bytes, signature):
        raise AuthError("Invalid wallet signature")

    # 4) Decode JSON payload
    try:
        payload = decode_signed_message(message_bytes)
    except Exception as e:
        raise AuthError(f"Bad auth message JSON format: {e}") from e

    cert_pub_b64 = payload.get("cert_pub")
    if not cert_pub_b64:
        raise AuthError("Missing cert_pub in signed message")

    try:
        cert_pub_bytes = base64.b64decode(cert_pub_b64.encode("ascii"))
    except Exception as e:
        raise AuthError(f"Bad cert_pub encoding in message: {e}") from e

    # 5) Binding to TLS transport public key
    if tls_pub != cert_pub_bytes:
        raise AuthError("TLS client key does not match wallet-authorized cert_pub")

    model_id = payload.get("model_id")
    if model_id != expected_model_id:
        raise AuthError("The model_id in the payload does not match the expected model_id.")

    hotkey = payload.get("hotkey")
    if hotkey != expected_hotkey:
        raise AuthError("Hotkey in the payload does not match the expected hotkey.")

    expires_raw = payload.get("expires_at")
    expires_at = int(expires_raw) if expires_raw is not None else None

    return DelegationInfo(
        message_bytes=message_bytes,
        payload=payload,
        wallet_pub_bytes=wallet_pub_bytes,
        cert_pub_bytes=cert_pub_bytes,
        wallet_pub_b58=wallet_pub_b58,
        model_id=model_id,
        expires_at=expires_at,
    )
