"""
gRPC client interceptor for gateway auth (signed-token in metadata).

On every call the interceptor:
  1. Builds a JSON payload: {"model_id": "...", "timestamp": <unix_epoch>}
  2. Signs it with the coordinator's RSA private key (PKCS#1v15 + SHA-256)
  3. Attaches payload + signature + public key (base64-encoded DER
     SubjectPublicKeyInfo) as gRPC request metadata

The model runner server:
  - Computes SHA-256(public_key_der) and checks it against the on-chain
    cert hashes registered for the coordinator's wallet
    (via cpi.crunchdao.io/certificates?wallet=<wallet>)
  - Verifies the signature against the presented public key
  - Checks timestamp freshness
"""
from __future__ import annotations

import base64
import collections
import json
import logging
import time

import grpc

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

logger = logging.getLogger("model_runner_client.gateway_auth")

# Metadata keys (no -bin suffix → ASCII / base64-encoded)
AUTH_MESSAGE_KEY = "x-gateway-auth-message"
AUTH_SIGNATURE_KEY = "x-gateway-auth-signature"
AUTH_PUBKEY_KEY = "x-gateway-auth-pubkey"  # base64(DER-encoded SubjectPublicKeyInfo)


# ---------------------------------------------------------------------------
# Signing
# ---------------------------------------------------------------------------

def _sign(private_key: rsa.RSAPrivateKey, data: bytes) -> bytes:
    """Sign *data* with RSA PKCS#1 v1.5 + SHA-256."""
    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise TypeError(f"Expected RSA private key, got {type(private_key).__name__}")
    return private_key.sign(data, padding.PKCS1v15(), hashes.SHA256())


def _public_key_der(private_key: rsa.RSAPrivateKey) -> bytes:
    """Extract the DER-encoded SubjectPublicKeyInfo from a private key."""
    return private_key.public_key().public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)


# ---------------------------------------------------------------------------
# gRPC client interceptor
# ---------------------------------------------------------------------------

class _ClientCallDetails(
    collections.namedtuple(
        "_ClientCallDetails",
        ("method", "timeout", "metadata", "credentials", "wait_for_ready"),
    ),
    grpc.aio.ClientCallDetails,
):
    """Mutable-ish wrapper so we can inject metadata."""


class GatewayAuthClientInterceptor(
    grpc.aio.UnaryUnaryClientInterceptor,
    grpc.aio.UnaryStreamClientInterceptor,
):
    """
    Client interceptor that attaches a signed auth token to every gRPC call.

    The token contains the model_id and a timestamp, signed with the
    coordinator's RSA private key.  The model runner server verifies this
    using the coordinator's public key (checked against on-chain cert hash).
    """

    def __init__(self, private_key: rsa.RSAPrivateKey, model_id: str):
        self.private_key = private_key
        self.model_id = model_id
        # Pre-compute the base64-encoded DER public key (doesn't change per call)
        self._pubkey_b64 = base64.b64encode(_public_key_der(private_key)).decode()

    def _build_auth_metadata(self) -> list[tuple[str, str]]:
        payload = json.dumps(
            {"model_id": self.model_id, "timestamp": int(time.time())},
            separators=(",", ":"),
        ).encode()
        signature = _sign(self.private_key, payload)
        return [
            (AUTH_MESSAGE_KEY, base64.b64encode(payload).decode()),
            (AUTH_SIGNATURE_KEY, base64.b64encode(signature).decode()),
            (AUTH_PUBKEY_KEY, self._pubkey_b64),
        ]

    def _enrich_metadata(
        self, client_call_details: grpc.aio.ClientCallDetails,
    ) -> _ClientCallDetails:
        metadata = list(client_call_details.metadata or [])
        metadata.extend(self._build_auth_metadata())
        return _ClientCallDetails(
            method=client_call_details.method,
            timeout=client_call_details.timeout,
            metadata=metadata,
            credentials=client_call_details.credentials,
            wait_for_ready=client_call_details.wait_for_ready,
        )

    async def intercept_unary_unary(self, continuation, client_call_details, request):
        return await continuation(self._enrich_metadata(client_call_details), request)

    async def intercept_unary_stream(self, continuation, client_call_details, request):
        return await continuation(self._enrich_metadata(client_call_details), request)
