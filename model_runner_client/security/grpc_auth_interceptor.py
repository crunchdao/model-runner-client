import grpc
from typing import Any, Sequence, Tuple

from .wallet_gelegation import verify_wallet_delegation, AuthError

Metadata = Sequence[Tuple[str, Any]]  # values are usually str, or bytes for *-bin


class StaticAuthMetadata(grpc.AuthMetadataPlugin):
    def __init__(self, metadata: tuple[tuple[str, str], ...]):
        self._metadata = metadata

    def __call__(self, context, callback):
        callback(self._metadata, None)


def _md_to_dict(md: Metadata) -> dict[str, Any]:
    # gRPC metadata keys are case-insensitive; normalize to lowercase
    out: dict[str, Any] = {}
    for k, v in md:
        out[str(k).lower()] = v
    return out


class WalletTlsAuthClientInterceptor(
    grpc.aio.UnaryUnaryClientInterceptor,
    grpc.aio.UnaryStreamClientInterceptor,
):
    MESSAGE_KEY = "x-server-auth-message"
    SIGNATURE_KEY = "x-server-auth-signature"
    WALLET_KEY = "x-server-wallet-pubkey"

    def __init__(
        self,
        expected_wallet_pub_b58: str,
        model_id: str,
        tls_pub: bytes,
        protected_prefix: str = "",
    ):
        self.expected_wallet_pub_b58 = expected_wallet_pub_b58
        self.model_id = model_id
        self.tls_pub = tls_pub
        self.protected_prefix = protected_prefix

    def _should_protect(self, method: str) -> bool:
        return not self.protected_prefix or method.startswith(self.protected_prefix)

    async def _verify_from_call_headers(self, method: str, md: Metadata) -> None:
        d = _md_to_dict(md)

        message_b64 = d.get(self.MESSAGE_KEY)
        signature_b64 = d.get(self.SIGNATURE_KEY)
        wallet_pubkey_b58 = d.get(self.WALLET_KEY)

        if not message_b64 or not signature_b64 or not wallet_pubkey_b58:
            raise AuthError(
                "Missing auth metadata "
                f"({self.MESSAGE_KEY}/{self.SIGNATURE_KEY}/{self.WALLET_KEY})"
            )

        # gRPC metadata values for non -bin are usually str.
        if not isinstance(message_b64, str) or not isinstance(signature_b64, str) or not isinstance(wallet_pubkey_b58, str):
            raise AuthError("Auth metadata must be strings (non -bin headers)")

        verify_wallet_delegation(
            message_b64=message_b64,
            signature_b64=signature_b64,
            wallet_pub_b58=wallet_pubkey_b58,
            expected_wallet_pub_b58=self.expected_wallet_pub_b58,
            tls_pub=self.tls_pub,
            expect_model_id=self.model_id
        )

    async def intercept_unary_unary(self, continuation, client_call_details, request):
        call = await continuation(client_call_details, request)

        method = client_call_details.method
        if not self._should_protect(method):
            return call

        try:
            md = await call.initial_metadata()  # server response headers
            await self._verify_from_call_headers(method, md)
        except Exception as e:
            call.cancel()
            raise  # raise AuthError/ValueError/etc.

        return call

    async def intercept_unary_stream(self, continuation, client_call_details, request):
        call = await continuation(client_call_details, request)

        method = client_call_details.method
        if not self._should_protect(method):
            return call

        try:
            md = await call.initial_metadata()
            await self._verify_from_call_headers(method, md)
        except Exception:
            call.cancel()
            raise

        return call
