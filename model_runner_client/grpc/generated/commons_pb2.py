"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 29, 0, '', 'commons.proto')
_sym_db = _symbol_database.Default()
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\rcommons.proto\x12\x07commons"<\n\x07Variant\x12"\n\x04type\x18\x02 \x01(\x0e2\x14.commons.VariantType\x12\r\n\x05value\x18\x03 \x01(\x0c"<\n\x08Argument\x12\x10\n\x08position\x18\x01 \x01(\r\x12\x1e\n\x04data\x18\x02 \x01(\x0b2\x10.commons.Variant"=\n\nKwArgument\x12\x0f\n\x07keyword\x18\x01 \x01(\t\x12\x1e\n\x04data\x18\x02 \x01(\x0b2\x10.commons.Variant"\'\n\x06Status\x12\x0c\n\x04code\x18\x01 \x01(\t\x12\x0f\n\x07message\x18\x02 \x01(\t*Z\n\x0bVariantType\x12\x08\n\x04NONE\x10\x00\x12\n\n\x06DOUBLE\x10\x01\x12\x07\n\x03INT\x10\x02\x12\n\n\x06STRING\x10\x03\x12\x0b\n\x07PARQUET\x10\x04\x12\t\n\x05ARROW\x10\x05\x12\x08\n\x04JSON\x10\x06b\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'commons_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_VARIANTTYPE']._serialized_start = 254
    _globals['_VARIANTTYPE']._serialized_end = 344
    _globals['_VARIANT']._serialized_start = 26
    _globals['_VARIANT']._serialized_end = 86
    _globals['_ARGUMENT']._serialized_start = 88
    _globals['_ARGUMENT']._serialized_end = 148
    _globals['_KWARGUMENT']._serialized_start = 150
    _globals['_KWARGUMENT']._serialized_end = 211
    _globals['_STATUS']._serialized_start = 213
    _globals['_STATUS']._serialized_end = 252