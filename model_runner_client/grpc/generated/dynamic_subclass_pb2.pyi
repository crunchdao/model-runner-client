import commons_pb2 as _commons_pb2
from google.protobuf import empty_pb2 as _empty_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union
DESCRIPTOR: _descriptor.FileDescriptor

class SetupRequest(_message.Message):
    __slots__ = ('className', 'instanceArguments', 'instanceKwArguments')
    CLASSNAME_FIELD_NUMBER: _ClassVar[int]
    INSTANCEARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    INSTANCEKWARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    className: str
    instanceArguments: _containers.RepeatedCompositeFieldContainer[_commons_pb2.Argument]
    instanceKwArguments: _containers.RepeatedCompositeFieldContainer[_commons_pb2.KwArgument]

    def __init__(self, className: _Optional[str]=..., instanceArguments: _Optional[_Iterable[_Union[_commons_pb2.Argument, _Mapping]]]=..., instanceKwArguments: _Optional[_Iterable[_Union[_commons_pb2.KwArgument, _Mapping]]]=...) -> None:
        ...

class SetupResponse(_message.Message):
    __slots__ = ('status',)
    STATUS_FIELD_NUMBER: _ClassVar[int]
    status: _commons_pb2.Status

    def __init__(self, status: _Optional[_Union[_commons_pb2.Status, _Mapping]]=...) -> None:
        ...

class CallRequest(_message.Message):
    __slots__ = ('methodName', 'methodArguments', 'methodKwArguments')
    METHODNAME_FIELD_NUMBER: _ClassVar[int]
    METHODARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    METHODKWARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    methodName: str
    methodArguments: _containers.RepeatedCompositeFieldContainer[_commons_pb2.Argument]
    methodKwArguments: _containers.RepeatedCompositeFieldContainer[_commons_pb2.KwArgument]

    def __init__(self, methodName: _Optional[str]=..., methodArguments: _Optional[_Iterable[_Union[_commons_pb2.Argument, _Mapping]]]=..., methodKwArguments: _Optional[_Iterable[_Union[_commons_pb2.KwArgument, _Mapping]]]=...) -> None:
        ...

class CallResponse(_message.Message):
    __slots__ = ('status', 'methodResponse')
    STATUS_FIELD_NUMBER: _ClassVar[int]
    METHODRESPONSE_FIELD_NUMBER: _ClassVar[int]
    status: _commons_pb2.Status
    methodResponse: _commons_pb2.Variant

    def __init__(self, status: _Optional[_Union[_commons_pb2.Status, _Mapping]]=..., methodResponse: _Optional[_Union[_commons_pb2.Variant, _Mapping]]=...) -> None:
        ...

class RestResponse(_message.Message):
    __slots__ = ('status',)
    STATUS_FIELD_NUMBER: _ClassVar[int]
    status: _commons_pb2.Status

    def __init__(self, status: _Optional[_Union[_commons_pb2.Status, _Mapping]]=...) -> None:
        ...