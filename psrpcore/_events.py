# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import typing
import uuid

from psrpcore.types import (
    ApplicationPrivateData,
    ConnectRunspacePool,
    CreatePipeline,
    DebugRecordMsg,
    EncryptedSessionKey,
    EndOfPipelineInput,
    ErrorRecord,
    ErrorRecordMsg,
    GetAvailableRunspaces,
    GetCommandMetadata,
    InformationRecordMsg,
    InitRunspacePool,
    PipelineHostCall,
    PipelineHostResponse,
    PipelineState,
    ProgressRecord,
    PSBool,
    PSInvocationState,
    PSObject,
    PSRPMessageType,
    PublicKey,
    PublicKeyRequest,
    ResetRunspaceState,
    RunspaceAvailability,
    RunspacePoolHostCall,
    RunspacePoolHostResponse,
    RunspacePoolInitData,
    RunspacePoolState,
    RunspacePoolStateMsg,
    SessionCapability,
    SetMaxRunspaces,
    SetMinRunspaces,
    UserEvent,
    VerboseRecordMsg,
    WarningRecordMsg,
)

if typing.TYPE_CHECKING:
    from psrpcore._server import ServerGetCommandMetadata, ServerPowerShell

T1 = typing.TypeVar("T1")
T2 = typing.TypeVar("T2")
_OptionalPipelineType = typing.Optional[uuid.UUID]


class PSRPEvent(typing.Generic[T1, T2]):
    def __init__(
        self,
        message_type: PSRPMessageType,
        ps_object: T1,
        runspace_pool_id: uuid.UUID,
        pipeline_id: T2,
    ):
        self.message_type = message_type
        self.ps_object = ps_object
        self.runspace_pool_id = runspace_pool_id
        self.pipeline_id = pipeline_id

    @classmethod
    def create(
        cls,
        message_type: PSRPMessageType,
        ps_object: T1,
        runspace_pool_id: uuid.UUID,
        pipeline_id: T2 = None,
    ) -> "PSRPEvent":
        event_cls = _REGISTRY[message_type]
        return event_cls(message_type, ps_object, runspace_pool_id, pipeline_id)


_REGISTRY: typing.Dict[PSRPMessageType, typing.Type[PSRPEvent]] = {}


def RegisterEvent(cls: typing.Type) -> typing.Type[PSRPEvent]:
    msg_type = cls.__orig_bases__[0].__args__[0]

    # PipelineInput and PipelineOutput can accept anything.
    msg_id = None
    if msg_type != typing.Any:
        msg_id = PSRPMessageType.get_message_id(msg_type)

    elif cls.__module__ in RegisterEvent.__module__:
        msg_id = {
            "PipelineInputEvent": PSRPMessageType.PipelineInput,
            "PipelineOutputEvent": PSRPMessageType.PipelineOutput,
        }[cls.__qualname__]

    if msg_id:
        _REGISTRY[msg_id] = cls

    return cls


@RegisterEvent
class ApplicationPrivateDataEvent(PSRPEvent[ApplicationPrivateData, None]):
    pass


@RegisterEvent
class ConnectRunspacePoolEvent(PSRPEvent[ConnectRunspacePool, None]):
    pass


@RegisterEvent
class CreatePipelineEvent(PSRPEvent[CreatePipeline, uuid.UUID]):
    def __init__(
        self,
        message_type: PSRPMessageType,
        ps_object: CreatePipeline,
        runspace_pool_id: uuid.UUID,
        pipeline_id: uuid.UUID,
    ):
        super().__init__(message_type, ps_object, runspace_pool_id, pipeline_id=pipeline_id)
        self.pipeline: typing.Optional["ServerPowerShell"] = None


@RegisterEvent
class DebugRecordEvent(PSRPEvent[DebugRecordMsg, _OptionalPipelineType]):
    pass


@RegisterEvent
class EncryptedSessionKeyEvent(PSRPEvent[EncryptedSessionKey, _OptionalPipelineType]):
    pass


@RegisterEvent
class EndOfPipelineInputEvent(PSRPEvent[EndOfPipelineInput, uuid.UUID]):
    pass


@RegisterEvent
class ErrorRecordEvent(PSRPEvent[ErrorRecordMsg, _OptionalPipelineType]):
    pass


@RegisterEvent
class GetAvailableRunspacesEvent(PSRPEvent[GetAvailableRunspaces, None]):
    pass


@RegisterEvent
class GetCommandMetadataEvent(PSRPEvent[GetCommandMetadata, uuid.UUID]):
    def __init__(
        self,
        message_type: PSRPMessageType,
        ps_object: GetCommandMetadata,
        runspace_pool_id: uuid.UUID,
        pipeline_id: uuid.UUID,
    ):
        super().__init__(message_type, ps_object, runspace_pool_id, pipeline_id=pipeline_id)
        self.pipeline: typing.Optional["ServerGetCommandMetadata"] = None


@RegisterEvent
class InformationRecordEvent(PSRPEvent[InformationRecordMsg, _OptionalPipelineType]):
    pass


@RegisterEvent
class InitRunspacePoolEvent(PSRPEvent[InitRunspacePool, None]):
    pass


@RegisterEvent
class PipelineHostCallEvent(PSRPEvent[PipelineHostCall, uuid.UUID]):
    pass


@RegisterEvent
class PipelineHostResponseEvent(PSRPEvent[PipelineHostResponse, uuid.UUID]):
    pass


@RegisterEvent
class PublicKeyEvent(PSRPEvent[PublicKey, None]):
    pass


@RegisterEvent
class PublicKeyRequestEvent(PSRPEvent[PublicKeyRequest, None]):
    pass


@RegisterEvent
class PipelineInputEvent(PSRPEvent[typing.Any, uuid.UUID]):
    pass


@RegisterEvent
class PipelineOutputEvent(PSRPEvent[typing.Any, uuid.UUID]):
    pass


@RegisterEvent
class PipelineStateEvent(PSRPEvent[PipelineState, uuid.UUID]):
    @property
    def state(self) -> PSInvocationState:
        return PSInvocationState(self.ps_object.PipelineState)

    @property
    def reason(self) -> typing.Optional[ErrorRecord]:
        return getattr(self.ps_object, "ExceptionAsErrorRecord", None)


@RegisterEvent
class ProgressRecordEvent(PSRPEvent[ProgressRecord, _OptionalPipelineType]):
    pass


@RegisterEvent
class ResetRunspaceStateEvent(PSRPEvent[ResetRunspaceState, None]):
    pass


@RegisterEvent
class RunspaceAvailabilityEvent(PSRPEvent[RunspaceAvailability, None]):
    def __new__(
        cls,
        message_type: PSRPMessageType,
        ps_object: PSObject,
        runspace_pool_id: uuid.UUID,
        pipeline_id: None = None,
    ) -> "RunspaceAvailabilityEvent":
        # Special case, this message has a boolean value when in response to Set[Max|Min]Runspaces and an Int64
        # value when in response to GetAvailableRunspaces. We want to make sure our event is clear what it is in
        # response to.
        if isinstance(ps_object.SetMinMaxRunspacesResponse, PSBool):
            return super().__new__(SetRunspaceAvailabilityEvent)
        else:
            return super().__new__(GetRunspaceAvailabilityEvent)


class SetRunspaceAvailabilityEvent(RunspaceAvailabilityEvent):
    @property
    def success(self) -> bool:
        return self.ps_object.SetMinMaxRunspacesResponse


class GetRunspaceAvailabilityEvent(RunspaceAvailabilityEvent):
    @property
    def count(self) -> int:
        return int(self.ps_object.SetMinMaxRunspacesResponse)


@RegisterEvent
class RunspacePoolHostCallEvent(PSRPEvent[RunspacePoolHostCall, None]):
    pass


@RegisterEvent
class RunspacePoolHostResponseEvent(PSRPEvent[RunspacePoolHostResponse, None]):
    pass


@RegisterEvent
class RunspacePoolInitDataEvent(PSRPEvent[RunspacePoolInitData, None]):
    pass


@RegisterEvent
class RunspacePoolStateEvent(PSRPEvent[RunspacePoolStateMsg, None]):
    @property
    def state(self) -> RunspacePoolState:
        return RunspacePoolState(self.ps_object.RunspaceState)

    @property
    def reason(self) -> typing.Optional[ErrorRecord]:
        return getattr(self.ps_object, "ExceptionAsErrorRecord", None)


@RegisterEvent
class SessionCapabilityEvent(PSRPEvent[SessionCapability, None]):
    pass


@RegisterEvent
class SetMaxRunspacesEvent(PSRPEvent[SetMaxRunspaces, None]):
    pass


@RegisterEvent
class SetMinRunspacesEvent(PSRPEvent[SetMinRunspaces, None]):
    pass


@RegisterEvent
class UserEventEvent(PSRPEvent[UserEvent, None]):
    pass


@RegisterEvent
class VerboseRecordEvent(PSRPEvent[VerboseRecordMsg, _OptionalPipelineType]):
    pass


@RegisterEvent
class WarningRecordEvent(PSRPEvent[WarningRecordMsg, _OptionalPipelineType]):
    pass
