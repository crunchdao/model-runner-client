"""Client and server classes corresponding to protobuf-defined services."""
import grpc
import warnings
from . import dynamic_subclass_pb2 as dynamic__subclass__pb2
from google.protobuf import empty_pb2 as google_dot_protobuf_dot_empty__pb2
GRPC_GENERATED_VERSION = '1.69.0'
GRPC_VERSION = grpc.__version__
_version_not_supported = False
try:
    from grpc._utilities import first_version_is_lower
    _version_not_supported = first_version_is_lower(GRPC_VERSION, GRPC_GENERATED_VERSION)
except ImportError:
    _version_not_supported = True
if _version_not_supported:
    raise RuntimeError(f'The grpc package installed is at version {GRPC_VERSION},' + f' but the generated code in dynamic_subclass_pb2_grpc.py depends on' + f' grpcio>={GRPC_GENERATED_VERSION}.' + f' Please upgrade your grpc module to grpcio>={GRPC_GENERATED_VERSION}' + f' or downgrade your generated code using grpcio-tools<={GRPC_VERSION}.')

class DynamicSubclassServiceStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.Setup = channel.unary_unary('/dynamic_subclass.DynamicSubclassService/Setup', request_serializer=dynamic__subclass__pb2.SetupRequest.SerializeToString, response_deserializer=dynamic__subclass__pb2.SetupResponse.FromString, _registered_method=True)
        self.Call = channel.unary_unary('/dynamic_subclass.DynamicSubclassService/Call', request_serializer=dynamic__subclass__pb2.CallRequest.SerializeToString, response_deserializer=dynamic__subclass__pb2.CallResponse.FromString, _registered_method=True)
        self.Rest = channel.unary_unary('/dynamic_subclass.DynamicSubclassService/Rest', request_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString, response_deserializer=dynamic__subclass__pb2.RestResponse.FromString, _registered_method=True)

class DynamicSubclassServiceServicer(object):
    """Missing associated documentation comment in .proto file."""

    def Setup(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def Call(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def Rest(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

def add_DynamicSubclassServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {'Setup': grpc.unary_unary_rpc_method_handler(servicer.Setup, request_deserializer=dynamic__subclass__pb2.SetupRequest.FromString, response_serializer=dynamic__subclass__pb2.SetupResponse.SerializeToString), 'Call': grpc.unary_unary_rpc_method_handler(servicer.Call, request_deserializer=dynamic__subclass__pb2.CallRequest.FromString, response_serializer=dynamic__subclass__pb2.CallResponse.SerializeToString), 'Rest': grpc.unary_unary_rpc_method_handler(servicer.Rest, request_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString, response_serializer=dynamic__subclass__pb2.RestResponse.SerializeToString)}
    generic_handler = grpc.method_handlers_generic_handler('dynamic_subclass.DynamicSubclassService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))
    server.add_registered_method_handlers('dynamic_subclass.DynamicSubclassService', rpc_method_handlers)

class DynamicSubclassService(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def Setup(request, target, options=(), channel_credentials=None, call_credentials=None, insecure=False, compression=None, wait_for_ready=None, timeout=None, metadata=None):
        return grpc.experimental.unary_unary(request, target, '/dynamic_subclass.DynamicSubclassService/Setup', dynamic__subclass__pb2.SetupRequest.SerializeToString, dynamic__subclass__pb2.SetupResponse.FromString, options, channel_credentials, insecure, call_credentials, compression, wait_for_ready, timeout, metadata, _registered_method=True)

    @staticmethod
    def Call(request, target, options=(), channel_credentials=None, call_credentials=None, insecure=False, compression=None, wait_for_ready=None, timeout=None, metadata=None):
        return grpc.experimental.unary_unary(request, target, '/dynamic_subclass.DynamicSubclassService/Call', dynamic__subclass__pb2.CallRequest.SerializeToString, dynamic__subclass__pb2.CallResponse.FromString, options, channel_credentials, insecure, call_credentials, compression, wait_for_ready, timeout, metadata, _registered_method=True)

    @staticmethod
    def Rest(request, target, options=(), channel_credentials=None, call_credentials=None, insecure=False, compression=None, wait_for_ready=None, timeout=None, metadata=None):
        return grpc.experimental.unary_unary(request, target, '/dynamic_subclass.DynamicSubclassService/Rest', google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString, dynamic__subclass__pb2.RestResponse.FromString, options, channel_credentials, insecure, call_credentials, compression, wait_for_ready, timeout, metadata, _registered_method=True)