"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 29, 0, '', 'dynamic_subclass.proto')
_sym_db = _symbol_database.Default()
from . import commons_pb2 as commons__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x16dynamic_subclass.proto\x12\x10dynamic_subclass\x1a\rcommons.proto"\x81\x01\n\x0cSetupRequest\x12\x11\n\tclassName\x18\x01 \x01(\t\x12,\n\x11instanceArguments\x18\x02 \x03(\x0b2\x11.commons.Argument\x120\n\x13instanceKwArguments\x18\x03 \x03(\x0b2\x13.commons.KwArgument"\x0f\n\rSetupResponse"}\n\x0bCallRequest\x12\x12\n\nmethodName\x18\x01 \x01(\t\x12*\n\x0fmethodArguments\x18\x02 \x03(\x0b2\x11.commons.Argument\x12.\n\x11methodKwArguments\x18\x03 \x03(\x0b2\x13.commons.KwArgument"8\n\x0cCallResponse\x12(\n\x0emethodResponse\x18\x01 \x01(\x0b2\x10.commons.Variant2\xa9\x01\n\x16DynamicSubclassService\x12H\n\x05Setup\x12\x1e.dynamic_subclass.SetupRequest\x1a\x1f.dynamic_subclass.SetupResponse\x12E\n\x04Call\x12\x1d.dynamic_subclass.CallRequest\x1a\x1e.dynamic_subclass.CallResponseb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'dynamic_subclass_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_SETUPREQUEST']._serialized_start = 60
    _globals['_SETUPREQUEST']._serialized_end = 189
    _globals['_SETUPRESPONSE']._serialized_start = 191
    _globals['_SETUPRESPONSE']._serialized_end = 206
    _globals['_CALLREQUEST']._serialized_start = 208
    _globals['_CALLREQUEST']._serialized_end = 333
    _globals['_CALLRESPONSE']._serialized_start = 335
    _globals['_CALLRESPONSE']._serialized_end = 391
    _globals['_DYNAMICSUBCLASSSERVICE']._serialized_start = 394
    _globals['_DYNAMICSUBCLASSSERVICE']._serialized_end = 563