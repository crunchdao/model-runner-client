"""Client and server classes corresponding to protobuf-defined services."""
import grpc
import warnings
from google.protobuf import empty_pb2 as google_dot_protobuf_dot_empty__pb2
from . import train_infer_pb2 as train__infer__pb2
GRPC_GENERATED_VERSION = '1.69.0'
GRPC_VERSION = grpc.__version__
_version_not_supported = False
try:
    from grpc._utilities import first_version_is_lower
    _version_not_supported = first_version_is_lower(GRPC_VERSION, GRPC_GENERATED_VERSION)
except ImportError:
    _version_not_supported = True
if _version_not_supported:
    raise RuntimeError(f'The grpc package installed is at version {GRPC_VERSION},' + f' but the generated code in train_infer_pb2_grpc.py depends on' + f' grpcio>={GRPC_GENERATED_VERSION}.' + f' Please upgrade your grpc module to grpcio>={GRPC_GENERATED_VERSION}' + f' or downgrade your generated code using grpcio-tools<={GRPC_VERSION}.')

class TrainInferStreamServiceStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.Setup = channel.unary_unary('/train_infer.TrainInferStreamService/Setup', request_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString, response_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString, _registered_method=True)
        self.Infer = channel.unary_unary('/train_infer.TrainInferStreamService/Infer', request_serializer=train__infer__pb2.InferRequest.SerializeToString, response_deserializer=train__infer__pb2.InferResponse.FromString, _registered_method=True)
        self.Reinitialize = channel.unary_unary('/train_infer.TrainInferStreamService/Reinitialize', request_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString, response_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString, _registered_method=True)

class TrainInferStreamServiceServicer(object):
    """Missing associated documentation comment in .proto file."""

    def Setup(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def Infer(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def Reinitialize(self, request, context):
        """rpc Train(TrainRequest) returns (TrainResponse);
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

def add_TrainInferStreamServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {'Setup': grpc.unary_unary_rpc_method_handler(servicer.Setup, request_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString, response_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString), 'Infer': grpc.unary_unary_rpc_method_handler(servicer.Infer, request_deserializer=train__infer__pb2.InferRequest.FromString, response_serializer=train__infer__pb2.InferResponse.SerializeToString), 'Reinitialize': grpc.unary_unary_rpc_method_handler(servicer.Reinitialize, request_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString, response_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString)}
    generic_handler = grpc.method_handlers_generic_handler('train_infer.TrainInferStreamService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))
    server.add_registered_method_handlers('train_infer.TrainInferStreamService', rpc_method_handlers)

class TrainInferStreamService(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def Setup(request, target, options=(), channel_credentials=None, call_credentials=None, insecure=False, compression=None, wait_for_ready=None, timeout=None, metadata=None):
        return grpc.experimental.unary_unary(request, target, '/train_infer.TrainInferStreamService/Setup', google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString, google_dot_protobuf_dot_empty__pb2.Empty.FromString, options, channel_credentials, insecure, call_credentials, compression, wait_for_ready, timeout, metadata, _registered_method=True)

    @staticmethod
    def Infer(request, target, options=(), channel_credentials=None, call_credentials=None, insecure=False, compression=None, wait_for_ready=None, timeout=None, metadata=None):
        return grpc.experimental.unary_unary(request, target, '/train_infer.TrainInferStreamService/Infer', train__infer__pb2.InferRequest.SerializeToString, train__infer__pb2.InferResponse.FromString, options, channel_credentials, insecure, call_credentials, compression, wait_for_ready, timeout, metadata, _registered_method=True)

    @staticmethod
    def Reinitialize(request, target, options=(), channel_credentials=None, call_credentials=None, insecure=False, compression=None, wait_for_ready=None, timeout=None, metadata=None):
        return grpc.experimental.unary_unary(request, target, '/train_infer.TrainInferStreamService/Reinitialize', google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString, google_dot_protobuf_dot_empty__pb2.Empty.FromString, options, channel_credentials, insecure, call_credentials, compression, wait_for_ready, timeout, metadata, _registered_method=True)

class TrainInferServiceStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.Setup = channel.unary_unary('/train_infer.TrainInferService/Setup', request_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString, response_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString, _registered_method=True)
        self.Infer = channel.unary_unary('/train_infer.TrainInferService/Infer', request_serializer=train__infer__pb2.InferRequest.SerializeToString, response_deserializer=train__infer__pb2.InferResponse.FromString, _registered_method=True)
        self.Reinitialize = channel.unary_unary('/train_infer.TrainInferService/Reinitialize', request_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString, response_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString, _registered_method=True)

class TrainInferServiceServicer(object):
    """Missing associated documentation comment in .proto file."""

    def Setup(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def Infer(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def Reinitialize(self, request, context):
        """rpc Train(TrainRequest) returns (TrainResponse);
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

def add_TrainInferServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {'Setup': grpc.unary_unary_rpc_method_handler(servicer.Setup, request_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString, response_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString), 'Infer': grpc.unary_unary_rpc_method_handler(servicer.Infer, request_deserializer=train__infer__pb2.InferRequest.FromString, response_serializer=train__infer__pb2.InferResponse.SerializeToString), 'Reinitialize': grpc.unary_unary_rpc_method_handler(servicer.Reinitialize, request_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString, response_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString)}
    generic_handler = grpc.method_handlers_generic_handler('train_infer.TrainInferService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))
    server.add_registered_method_handlers('train_infer.TrainInferService', rpc_method_handlers)

class TrainInferService(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def Setup(request, target, options=(), channel_credentials=None, call_credentials=None, insecure=False, compression=None, wait_for_ready=None, timeout=None, metadata=None):
        return grpc.experimental.unary_unary(request, target, '/train_infer.TrainInferService/Setup', google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString, google_dot_protobuf_dot_empty__pb2.Empty.FromString, options, channel_credentials, insecure, call_credentials, compression, wait_for_ready, timeout, metadata, _registered_method=True)

    @staticmethod
    def Infer(request, target, options=(), channel_credentials=None, call_credentials=None, insecure=False, compression=None, wait_for_ready=None, timeout=None, metadata=None):
        return grpc.experimental.unary_unary(request, target, '/train_infer.TrainInferService/Infer', train__infer__pb2.InferRequest.SerializeToString, train__infer__pb2.InferResponse.FromString, options, channel_credentials, insecure, call_credentials, compression, wait_for_ready, timeout, metadata, _registered_method=True)

    @staticmethod
    def Reinitialize(request, target, options=(), channel_credentials=None, call_credentials=None, insecure=False, compression=None, wait_for_ready=None, timeout=None, metadata=None):
        return grpc.experimental.unary_unary(request, target, '/train_infer.TrainInferService/Reinitialize', google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString, google_dot_protobuf_dot_empty__pb2.Empty.FromString, options, channel_credentials, insecure, call_credentials, compression, wait_for_ready, timeout, metadata, _registered_method=True)