from __future__ import annotations

import ssl
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class SecureCredentials:
    ca_bytes: bytes
    cert_bytes: bytes
    key_bytes: bytes

    tls_ctx: ssl.SSLContext = field(init=False, repr=False, compare=False)

    @classmethod
    def from_directory(
        cls,
        path: str | Path
    ) -> "SecureCredentials":
        path = Path(path)
        return cls.from_files(
            ca_cert_path=path / "ca.crt",
            tls_cert_path=path / "tls.crt",
            tls_key_path=path / "tls.key",
        )

    @classmethod
    def from_files(
        cls,
        ca_cert_path: str | Path,
        tls_cert_path: str | Path,
        tls_key_path: str | Path,
    ) -> "SecureCredentials":
        ca_cert_path = Path(ca_cert_path)
        tls_cert_path = Path(tls_cert_path)
        tls_key_path = Path(tls_key_path)

        obj = cls(
            ca_bytes=ca_cert_path.read_bytes(),
            cert_bytes=tls_cert_path.read_bytes(),
            key_bytes=tls_key_path.read_bytes(),
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
