"""
Gateway credentials for Phala CVM (or any TLS-terminating proxy) connections.

Transport uses standard TLS (system CAs) to the gateway.
Authentication uses a signed token in gRPC metadata:
  - Client signs (model_id, timestamp) with its RSA private key
  - Server verifies the signature with the corresponding public key
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.x509 import load_pem_x509_certificate


@dataclass(frozen=True)
class GatewayCredentials:
    """Credentials for gateway TLS mode: standard TLS + signed-token auth.

    Only RSA keys are supported (matches the on-chain cert hash registry).
    """

    private_key: rsa.RSAPrivateKey

    @classmethod
    def from_files(
        cls,
        cert_path: str | Path,
        key_path: str | Path,
    ) -> GatewayCredentials:
        key_path = Path(key_path)
        return cls.from_pem(key_pem=key_path.read_bytes())

    @classmethod
    def from_pem(
        cls,
        key_pem: bytes,
    ) -> GatewayCredentials:
        private_key = load_pem_private_key(key_pem, password=None)
        if not isinstance(private_key, rsa.RSAPrivateKey):
            raise TypeError(
                f"Only RSA keys are supported, got {type(private_key).__name__}"
            )
        return cls(private_key=private_key)
