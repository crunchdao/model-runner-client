from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union
DESCRIPTOR: _descriptor.FileDescriptor

class VariantType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    NONE: _ClassVar[VariantType]
    DOUBLE: _ClassVar[VariantType]
    INT: _ClassVar[VariantType]
    STRING: _ClassVar[VariantType]
    PARQUET: _ClassVar[VariantType]
    ARROW: _ClassVar[VariantType]
    JSON: _ClassVar[VariantType]
NONE: VariantType
DOUBLE: VariantType
INT: VariantType
STRING: VariantType
PARQUET: VariantType
ARROW: VariantType
JSON: VariantType

class Variant(_message.Message):
    __slots__ = ('type', 'value')
    TYPE_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    type: VariantType
    value: bytes

    def __init__(self, type: _Optional[_Union[VariantType, str]]=..., value: _Optional[bytes]=...) -> None:
        ...

class Argument(_message.Message):
    __slots__ = ('position', 'data')
    POSITION_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    position: int
    data: Variant

    def __init__(self, position: _Optional[int]=..., data: _Optional[_Union[Variant, _Mapping]]=...) -> None:
        ...

class KwArgument(_message.Message):
    __slots__ = ('keyword', 'data')
    KEYWORD_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    keyword: str
    data: Variant

    def __init__(self, keyword: _Optional[str]=..., data: _Optional[_Union[Variant, _Mapping]]=...) -> None:
        ...

class Status(_message.Message):
    __slots__ = ('code', 'message')
    CODE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    code: str
    message: str

    def __init__(self, code: _Optional[str]=..., message: _Optional[str]=...) -> None:
        ...