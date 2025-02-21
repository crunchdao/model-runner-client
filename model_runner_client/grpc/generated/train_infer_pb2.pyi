import commons_pb2 as _commons_pb2
from google.protobuf import empty_pb2 as _empty_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union
DESCRIPTOR: _descriptor.FileDescriptor

class InferRequest(_message.Message):
    __slots__ = ('argument',)
    ARGUMENT_FIELD_NUMBER: _ClassVar[int]
    argument: _commons_pb2.Variant

    def __init__(self, argument: _Optional[_Union[_commons_pb2.Variant, _Mapping]]=...) -> None:
        ...

class InferResponse(_message.Message):
    __slots__ = ('prediction',)
    PREDICTION_FIELD_NUMBER: _ClassVar[int]
    prediction: _commons_pb2.Variant

    def __init__(self, prediction: _Optional[_Union[_commons_pb2.Variant, _Mapping]]=...) -> None:
        ...