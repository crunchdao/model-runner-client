from __future__ import annotations

import base64
import json
import ssl
from dataclasses import dataclass, field
from pathlib import Path

from model_runner_client.security.wallet_gelegation import load_pubkey_from_pem_cert

Metadata = tuple[tuple[str, str], ...]

@dataclass(frozen=True)
class SecureCredentials:
    # Certs raw data  (bytes)
    ca_bytes: bytes
    cert_bytes: bytes
    key_bytes: bytes

    # Signed auth payload
    signed_message: dict[str, any]

    # Computed gRPC metadata
    metadata: Metadata = field(default=(), init=False)
    tls_ctx: ssl.SSLContext = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        self.validate_signature()

        md: Metadata = (
            ("x-auth-message", self.signed_message["message_b64"]),
            ("x-auth-signature", self.signed_message["signature_b64"]),
            ("x-auth-wallet-pubkey", self.signed_message["wallet_pubkey_b58"]),
        )
        object.__setattr__(self, "metadata", md)

    @classmethod
    def from_files(
        cls,
        ca_cert_path: str | Path,
        tls_cert_path: str | Path,
        tls_key_path: str | Path,
        signed_message_json: str | Path,
    ) -> "SecureCredentials":
        ca_cert_path = Path(ca_cert_path)
        tls_cert_path = Path(tls_cert_path)
        tls_key_path = Path(tls_key_path)
        signed_message_json = Path(signed_message_json)

        obj = cls(
            ca_bytes=ca_cert_path.read_bytes(),
            cert_bytes=tls_cert_path.read_bytes(),
            key_bytes=tls_key_path.read_bytes(),
            signed_message=json.loads(signed_message_json.read_text(encoding="utf-8")),
        )

        object.__setattr__(
            obj,
            "tls_ctx",
            cls.build_ssl_context(ca_cert_path, tls_cert_path, tls_key_path),
        )
        return obj

    @staticmethod
    def build_ssl_context(
        ca_cert_path: Path,
        tls_cert_path: Path,
        tls_key_path: Path,
    ) -> ssl.SSLContext:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.set_alpn_protocols(["h2"])  # gRPC uses HTTP/2
        ctx.verify_mode = ssl.CERT_REQUIRED
        ctx.check_hostname = True
        ctx.load_verify_locations(cafile=str(ca_cert_path))
        ctx.load_cert_chain(certfile=str(tls_cert_path), keyfile=str(tls_key_path))
        return ctx

    def validate_signature(self) -> bool:
        message = json.loads(base64.b64decode(self.signed_message["message_b64"]))
        cert_pub_b64 = message.get("cert_pub")
        cert_pub_bytes = base64.b64decode(cert_pub_b64.encode("ascii"))

        if load_pubkey_from_pem_cert(self.cert_bytes) != cert_pub_bytes:
            raise ValueError("Certificate public key does not match with the one in the signed message. Check if the signed message was generated with the correct certificate.")
        return True

