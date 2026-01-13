import asyncio
import ssl
from dataclasses import dataclass
from typing import Optional

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

class TlsProbeError(RuntimeError):
    pass


def _fmt_ssl_error(e: BaseException) -> str:
    # Best-effort formatting across SSLError/SSLCertVerificationError/etc.
    if isinstance(e, ssl.SSLCertVerificationError):
        # Python provides verify_code/verify_message here
        return f"certificate verification failed (code={e.verify_code} msg={e.verify_message})"
    if isinstance(e, ssl.CertificateError):
        # Often hostname mismatch
        return f"certificate/hostname error: {e}"
    if isinstance(e, ssl.SSLError):
        return f"SSL error: {e}"
    return str(e)


@dataclass(frozen=True)
class PeerTlsRsaKey:
    leaf_cert_pem: bytes
    spki_der: bytes


async def is_tls_connection(
    host: str,
    port: int,
    timeout: float = 5,
):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.set_alpn_protocols(["h2"])  # gRPC uses HTTP/2
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        peer_tls = await fetch_peer_rsa_spki_mtls(host, port, tls_ctx=ctx, timeout=timeout, check_tls_client_auth=False)
        return peer_tls is not None
    except (TlsProbeError, asyncio.TimeoutError):
        return False


async def fetch_peer_rsa_spki_mtls(
    host: str,
    port: int,
    *,
    tls_ctx: ssl.SSLContext,
    server_hostname: Optional[str] = None,
    timeout: float = 5,
    check_tls_client_auth: bool = True,
) -> PeerTlsRsaKey | None:
    """
    TLS Probe
    Workaround for gRPC Python limitation.

    grpcio (client-side) does not expose the server peer certificate / public key
    negotiated during TLS/mTLS, so we use a small verified TLS probe (ssl) to
    retrieve the server leaf cert and extract its public key (SPKI).

    mTLS probe: verifies the server using ca_pem AND presents a client cert/key.
    Returns the server leaf cert PEM + RSA public key (SPKI DER).
    """
    if server_hostname is None:
        server_hostname = host

    async def _connect():
        try:
            reader, writer = await asyncio.open_connection(
                host=host,
                port=port,
                ssl=tls_ctx,
                server_hostname=server_hostname
            )

            if check_tls_client_auth:
                # gRPC server may close the connection if the TLS handshake fails
                b = await asyncio.wait_for(reader.read(1), timeout=timeout)
                if not b:
                    raise TlsProbeError("Server terminated the connection immediately after TLS handshake. This may indicate invalid TLS certificates")

        except (ssl.SSLCertVerificationError, ssl.CertificateError, ssl.SSLError) as e:
            raise TlsProbeError(
                f"TLS handshake failed to {host}:{port} (server_hostname={server_hostname!r}): "
                f"{_fmt_ssl_error(e)}"
            ) from e
        except (ConnectionRefusedError, OSError) as e:
            raise TlsProbeError(
                f"TCP connect failed to {host}:{port}: {e}"
            ) from e

        try:
            sslobj: ssl.SSLObject = writer.get_extra_info("ssl_object")
            if sslobj is None:
                raise TlsProbeError("TLS handshake did not produce an ssl_object")

            leaf_der = sslobj.getpeercert(binary_form=True)
            if not leaf_der:
                raise TlsProbeError("No peer certificate returned by TLS layer")

            cert = x509.load_der_x509_certificate(leaf_der)
            pub = cert.public_key()
            if not isinstance(pub, rsa.RSAPublicKey):
                raise TlsProbeError(f"Server public key is not RSA (got {type(pub)!r})")

            spki_der = pub.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)
            leaf_pem = cert.public_bytes(Encoding.PEM)
            return PeerTlsRsaKey(leaf_cert_pem=leaf_pem, spki_der=spki_der)
        finally:
            transport = writer.transport
            transport.abort()

    return await asyncio.wait_for(_connect(), timeout=timeout)
