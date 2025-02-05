from google.protobuf import empty_pb2 as _empty_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class DataType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DOUBLE: _ClassVar[DataType]
    INT: _ClassVar[DataType]
    STRING: _ClassVar[DataType]
    PARQUET: _ClassVar[DataType]
    ARROW: _ClassVar[DataType]
    JSON: _ClassVar[DataType]
DOUBLE: DataType
INT: DataType
STRING: DataType
PARQUET: DataType
ARROW: DataType
JSON: DataType

class InferRequest(_message.Message):
    __slots__ = ("type", "argument")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    ARGUMENT_FIELD_NUMBER: _ClassVar[int]
    type: DataType
    argument: bytes
    def __init__(self, type: _Optional[_Union[DataType, str]] = ..., argument: _Optional[bytes] = ...) -> None: ...

class InferResponse(_message.Message):
    __slots__ = ("type", "prediction")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    PREDICTION_FIELD_NUMBER: _ClassVar[int]
    type: DataType
    prediction: bytes
    def __init__(self, type: _Optional[_Union[DataType, str]] = ..., prediction: _Optional[bytes] = ...) -> None: ...
