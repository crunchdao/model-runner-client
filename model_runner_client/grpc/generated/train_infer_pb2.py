"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 29, 0, '', 'train_infer.proto')
_sym_db = _symbol_database.Default()
from . import commons_pb2 as commons__pb2
from google.protobuf import empty_pb2 as google_dot_protobuf_dot_empty__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x11train_infer.proto\x12\x0btrain_infer\x1a\rcommons.proto\x1a\x1bgoogle/protobuf/empty.proto"2\n\x0cInferRequest\x12"\n\x08argument\x18\x01 \x01(\x0b2\x10.commons.Variant"5\n\rInferResponse\x12$\n\nprediction\x18\x01 \x01(\x0b2\x10.commons.Variant2\xd2\x01\n\x17TrainInferStreamService\x127\n\x05Setup\x12\x16.google.protobuf.Empty\x1a\x16.google.protobuf.Empty\x12>\n\x05Infer\x12\x19.train_infer.InferRequest\x1a\x1a.train_infer.InferResponse\x12>\n\x0cReinitialize\x12\x16.google.protobuf.Empty\x1a\x16.google.protobuf.Empty2\xcc\x01\n\x11TrainInferService\x127\n\x05Setup\x12\x16.google.protobuf.Empty\x1a\x16.google.protobuf.Empty\x12>\n\x05Infer\x12\x19.train_infer.InferRequest\x1a\x1a.train_infer.InferResponse\x12>\n\x0cReinitialize\x12\x16.google.protobuf.Empty\x1a\x16.google.protobuf.Emptyb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'train_infer_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_INFERREQUEST']._serialized_start = 78
    _globals['_INFERREQUEST']._serialized_end = 128
    _globals['_INFERRESPONSE']._serialized_start = 130
    _globals['_INFERRESPONSE']._serialized_end = 183
    _globals['_TRAININFERSTREAMSERVICE']._serialized_start = 186
    _globals['_TRAININFERSTREAMSERVICE']._serialized_end = 396
    _globals['_TRAININFERSERVICE']._serialized_start = 399
    _globals['_TRAININFERSERVICE']._serialized_end = 603