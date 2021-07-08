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

T1 = typing.TypeVar("T1")
T2 = typing.TypeVar("T2")
_OptionalPipelineType = typing.Optional[uuid.UUID]


class PSRPEvent(typing.Generic[T1, T2]):
    """PSRP Event.

    Represents an event based on the various PSRP messages that can be received
    from a peer. It contains information such as the Runspace Pool and Pipeline
    the event is targeted towards as well as the raw PSObject received for
    further parsing.

    Args:
        message_type: The :class:`psrpcore.types.PSRPMessageType` that
            identifies the message type.
        ps_object: The message received from the peer.
        runspace_pool_id: The Runspace Pool the event is for.
        pipeline_id: The Pipeline the event is for, otherwise `None` when the
            event is just for the Runspace Pool.

    Attributes:
        message_type: See args.
        ps_object: See args.
        runspace_pool_id: See args.
        pipeline_id: See args.
    """

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
        """Creates an event for the specific message types - used internally."""
        event_cls = _REGISTRY[message_type]
        return event_cls(message_type, ps_object, runspace_pool_id, pipeline_id)


_REGISTRY: typing.Dict[PSRPMessageType, typing.Type[PSRPEvent]] = {}


def RegisterEvent(cls: typing.Type) -> typing.Type[PSRPEvent]:
    """Registers an event based on the PSRPMessageType."""
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
    """Application Private Data Event.

    Event Information:

        Direction: Server -> Client

        For: Runspace Pool

        Message Type: :class:`psrpcore.types.ApplicationPrivateData`

        Action Required: Share with higher layer

    The server generates this data automatically when receiving an
    :class:`psrpcore.types.InitRunspacePool` or
    :class:`psrpcore.types.ConnectRunspacePool` message from the client.
    """


@RegisterEvent
class ConnectRunspacePoolEvent(PSRPEvent[ConnectRunspacePool, None]):
    """Connect Runspace Pool Event.

    Event Information:

        Direction: Client -> Server

        For: Runspace Pool

        Message Type: :class:`psrpcore.types.ConnectRunspacePool`

        Action Required: Send responses back to the client

    The client sends this message when attempting to connect to a disconnected
    Runspace Pool. The server will generate the
    :class:`psrpcore.types.RunspacePoolInitData`,
    :class:`psrpcore.types.ApplicationPrivateData`, and
    :class:`psrpcore.types.RunspacePoolStateMsg` to send back to the client.
    """


@RegisterEvent
class CreatePipelineEvent(PSRPEvent[CreatePipeline, uuid.UUID]):
    """Create Pipeline Event.

    Event Information:

        Direction: Client -> Server

        For: Pipeline

        Message Type: :class:`psrpcore.types.CreatePipeline`

        Action Required: Process pipeline

    The client sends this message when invoking a new pipeline. There are no
    responses automatically generated to send back to the client as it is up
    to the server to invoke when there are available resources.
    """


@RegisterEvent
class DebugRecordEvent(PSRPEvent[DebugRecordMsg, _OptionalPipelineType]):
    """Debug Record Event.

    Event Information:

        Direction: Server -> Client

        For: Runspace Pool or Pipeline

        Message Type: :class:`psrpcore.types.DebugRecordMsg`

        Action Required: Send to higher layer

    The server sends this message when there is a debug record generated by the
    server. The data should be shared with the higher layer as necessary.
    """


@RegisterEvent
class EncryptedSessionKeyEvent(PSRPEvent[EncryptedSessionKey, _OptionalPipelineType]):
    """Encrypted Session Key Event.

    Event Information:

        Direction: Server -> Client

        For: Runspace Pool

        Message Type: :class:`psrpcore.types.EncryptedSessionKey`

        Action Required: None - secure strings can now be serialized

    The server sends this message after processing the
    :class:`psrpcore.types.PublicKey` message from the client. It contains the
    encrypted session key used when serializing
    :class:`psrpcore.types.PSSecureString` objects.
    """


@RegisterEvent
class EndOfPipelineInputEvent(PSRPEvent[EndOfPipelineInput, uuid.UUID]):
    """End Of Pipeline Input Event.

    Event Information:

        Direction: Client -> Server

        For: Pipeline

        Message Type: :class:`psrpcore.types.EndOfPipeline`

        Action Required: Server notifies the pipeline that no more input is to
        be expected.

    The client sends this message once it has finished sending all the input
    for the pipeline.
    """


@RegisterEvent
class ErrorRecordEvent(PSRPEvent[ErrorRecordMsg, _OptionalPipelineType]):
    """Error Record Event.

    Event Information:

        Direction: Server -> Client

        For: Runspace Pool or Pipeline

        Message Type: :class:`psrpcore.types.ErrorRecordMsg`

        Action Required: Send to higher layer

    The server sends this message when there is an error record generated by the
    server. The data should be shared with the higher layer as necessary.
    """


@RegisterEvent
class GetAvailableRunspacesEvent(PSRPEvent[GetAvailableRunspaces, None]):
    """Get Available Runspaces Event.

    Event Information:

        Direction: Client -> Server

        For: Runspace Pool

        Message Type: :class:`psrpcore.types.GetAvailableRunspaces`

        Action Required: Send response back to the client

    The client sends this to request the number of available runspaces in the
    Runspace Pool. The server automatically generates the
    :class:`psrpcore.types.RunspaceAvailability` as a response to the client.
    """


@RegisterEvent
class GetCommandMetadataEvent(PSRPEvent[GetCommandMetadata, uuid.UUID]):
    """Get Command Metadata Event.

    Event Information:

        Direction: Client -> Server

        For: Pipeline

        Message Type: :class:`psrpcore.types.GetCommandMetadata`

        Action Required: Process pipeline

    The client sends this message when requesting command metadata in a
    Runspace Pool. There are no responses automatically generated to send back
    to the client as it is up to the server to process when there are available
    resources.
    """


@RegisterEvent
class InformationRecordEvent(PSRPEvent[InformationRecordMsg, _OptionalPipelineType]):
    """Information Record Event.

    Event Information:

        Direction: Server -> Client

        For: Runspace Pool or Pipeline

        Message Type: :class:`psrpcore.types.InformationRecordMsg`

        Action Required: Send to higher layer

    The server sends this message when there is an information record generated
    by the server. The data should be shared with the higher layer as necessary.
    """


@RegisterEvent
class InitRunspacePoolEvent(PSRPEvent[InitRunspacePool, None]):
    """Init Runspace Pool Event.

    Event Information:

        Direction: Client -> Server

        For: Runspace Pool

        Message Type: :class:`psrpcore.types.InitRunspacePool`

        Action Required: Send responses back to the client

    The client sends this message when attempting to open a new Runspace Pool.
    The server will generate the :class:`psrpcore.types.ApplicationPrivateData`
    and :class:`psrpcore.types.RunspacePoolStateMsg` to send back to the
    client.
    """


@RegisterEvent
class PipelineHostCallEvent(PSRPEvent[PipelineHostCall, uuid.UUID]):
    """Pipeline Host Call Event.

    Event Information:

        Direction: Server -> Client

        For: Pipeline

        Message Type: :class:`psrpcore.types.PipelineHostCall`

        Action Required: Send to higher layer for processing

    The server sends this message when requesting the host to invoke a
    :class:`psrpcore.types.HostMethodIdentifier` method. It is up to the client
    to send this information to the higher layer and send back a response if
    required.
    """


@RegisterEvent
class PipelineHostResponseEvent(PSRPEvent[PipelineHostResponse, uuid.UUID]):
    """Pipeline Host Response Event.

    Event Information:

        Direction: Client -> Server

        For: Pipeline

        Message Type: :class:`psrpcore.types.PipelineHostResponse`

        Action Required: Send to higher layer for processing

    The client sends this message in response to a
    :class:`PipelineHostCallEvent`. It contains the host response information
    that is processed by the higher layer.
    """


@RegisterEvent
class PipelineInputEvent(PSRPEvent[typing.Any, uuid.UUID]):
    """Pipeline Input Event.

    Event Information:

        Direction: Client -> Server

        For: Pipeline

        Message Type: Any

        Action Required: Send to higher layer for processing

    The client sends any input it desires for the pipeline. It is sent to the
    higher layer to be used with the running Pipeline.
    """


@RegisterEvent
class PipelineOutputEvent(PSRPEvent[typing.Any, uuid.UUID]):
    """Pipeline Output Event.

    Event Information:

        Direction: Server -> Client

        For: Pipeline

        Message Type: Any

        Action Required: Send to higher layer for processing

    The server sends this message when there is output generated from the
    Pipeline. The data should be shared with the higher layer as necessary.
    """


@RegisterEvent
class PipelineStateEvent(PSRPEvent[PipelineState, uuid.UUID]):
    """Pipeline State Event.

    Event Information:

        Direction: Server -> Client

        For: Pipeline

        Message Type: :class:`psrpcore.types.PipelineState`

        Action Required: Send to higher layer for processing

    The server sends this msg in response to a pipeline state change. The
    client should share this with the higher layer which checks whether it is
    ``Failed`` and use the reason to see why it did.
    """

    @property
    def state(self) -> PSInvocationState:
        """The Pipeline state."""
        return PSInvocationState(self.ps_object.PipelineState)

    @property
    def reason(self) -> typing.Optional[ErrorRecord]:
        """An error record containing the reason why the pipeline is ``Failed``."""
        return getattr(self.ps_object, "ExceptionAsErrorRecord", None)


@RegisterEvent
class ProgressRecordEvent(PSRPEvent[ProgressRecord, _OptionalPipelineType]):
    """Progress Record Event.

    Event Information:

        Direction: Server -> Client

        For: Runspace Pool or Pipeline

        Message Type: :class:`psrpcore.types.ProgressRecord`

        Action Required: Send to higher layer

    The server sends this message when there is a progress record generated by
    the server. The data should be shared with the higher layer as necessary.
    """


@RegisterEvent
class PublicKeyEvent(PSRPEvent[PublicKey, None]):
    """Public Key Event.

    Event Information:

        Direction: Client -> Server

        For: Runspace Pool

        Message Type: :class:`psrpcore.types.PublicKey`

        Action Required: Send response back to the client

    The client sends this message when it requests the encrypted session key
    used when serializing :class:`psrpcore.types.PSSecureString` objects. The
    server automatically generates the
    :class:`psrpcore.types.EncryptedSessionKey` as a response to the client.
    """


@RegisterEvent
class PublicKeyRequestEvent(PSRPEvent[PublicKeyRequest, None]):
    """Public Key Request Event.

    Event Information:

        Direction: Server -> Client

        For: Runspace Pool

        Message Type: :class:`psrpcore.types.PublicKeyRequest`

        Action Required: Send response back to the server

    The server sends this message when it wants to serialize a
    :class:`psrpcore.types.PSSecureString` object. The client automatically
    generates the :class:`psrpcore.types.PublicKey` as a response to the
    server.
    """


@RegisterEvent
class ResetRunspaceStateEvent(PSRPEvent[ResetRunspaceState, None]):
    """Reset Runspace State Event.

    Event Information:

        Direction: Client -> Server

        For: Runspace Pool

        Message Type: :class:`psrpcore.types.ResetRunspaceState`

        Action Required: Send to higher layer


    The client sends this message when it wants to reset the Runspace Pool
    state.
    """


@RegisterEvent
class RunspaceAvailabilityEvent(PSRPEvent[RunspaceAvailability, None]):
    def __new__(
        cls,
        message_type: PSRPMessageType,
        ps_object: RunspaceAvailability,
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
    """Set Runspace Availability Event.

    Event Information:

        Direction: Server -> Client

        For: Runspace Pool

        Message Type: :class:`psrpcore.types.RunspaceAvailability`

        Action Required: Send to higher layer

    The server sends this message in resposne to a
    :class:`psrpcore.types.SetMaxRunspaces` or
    :class:`psrpcore.types.SetMinRunspaces` message. The client automatically
    adjusts the runspace limits based on the response.
    """

    @property
    def success(self) -> bool:
        """Whether the request suceeded or not."""
        return self.ps_object.SetMinMaxRunspacesResponse


class GetRunspaceAvailabilityEvent(RunspaceAvailabilityEvent):
    """Get Runspace Availability Event.

    Event Information:

        Direction: Server -> Client

        For: Runspace Pool

        Message Type: :class:`psrpcore.types.RunspaceAvailability`

        Action Required: Send to higher layer

    The server sends this message in resposne to a
    :class:`psrpcore.types.GetAvailableRunspaces` message.
    """

    @property
    def count(self) -> int:
        """The available runspaces specified by the server."""
        return int(self.ps_object.SetMinMaxRunspacesResponse)


@RegisterEvent
class RunspacePoolHostCallEvent(PSRPEvent[RunspacePoolHostCall, None]):
    """Runspace Pool Host Call Event.

    Event Information:

        Direction: Server -> Client

        For: Runspace Pool

        Message Type: :class:`psrpcore.types.RunspacePoolHostCall`

        Action Required: Send to higher layer for processing

    The server sends this message when requesting the host to invoke a
    :class:`psrpcore.types.HostMethodIdentifier` method. It is up to the client
    to send this information to the higher layer and send back a response if
    required.
    """


@RegisterEvent
class RunspacePoolHostResponseEvent(PSRPEvent[RunspacePoolHostResponse, None]):
    """Runspace Pool Host Response Event.

    Event Information:

        Direction: Client -> Server

        For: Runspace Pool

        Message Type: :class:`psrpcore.types.RunspacePoolHostResponse`

        Action Required: Send to higher layer for processing

    The client sends this message in response to a
    :class:`RunspacePoolHostCall`. It contains the host response information
    that is processed by the higher layer.
    """


@RegisterEvent
class RunspacePoolInitDataEvent(PSRPEvent[RunspacePoolInitData, None]):
    """Runspace Pool Init Data Event

    Event Information:

        Direction: Server -> Client

        For: Runspace Pool

        Message Type: :class:`psrpcore.types.`

        Action Required: Send to higher layer

    The server sends this message in response to the
    :class:`psrpcore.types.ConnectRunspacePool` message. The client adjusts the
    Runspace Pool min/max limits and the higher layer can process the data as
    required.
    """


@RegisterEvent
class RunspacePoolStateEvent(PSRPEvent[RunspacePoolStateMsg, None]):
    """Runspace Pool State Event.

    Event Information:

        Direction: Server -> Client

        For: Runspace Pool

        Message Type: :class:`psrpcore.types.RunspacePoolStateMsg`

        Action Required: Send to higher layer for processing

    The server sends this msg in response to a runspace state change. The
    client should share this with the higher layer which checks whether it is
    ``Broken`` and use the reason to see why it did.
    """

    @property
    def state(self) -> RunspacePoolState:
        """The Runspace Pool state."""
        return RunspacePoolState(self.ps_object.RunspaceState)

    @property
    def reason(self) -> typing.Optional[ErrorRecord]:
        """An error record containing the reason why the runspace is ``Broken``."""
        return getattr(self.ps_object, "ExceptionAsErrorRecord", None)


@RegisterEvent
class SessionCapabilityEvent(PSRPEvent[SessionCapability, None]):
    """Session Capability Event.

    Event Information:

        Direction: Both

        For: Runspace Pool

        Message Type: :class:`psrpcore.types.SessionCapability`

        Action Required: Nothing for client, send response back to the client

    The initial message received by both the client and server to state what
    protocol versions they understand. The server will automatically generate
    a :class:`psrpcore.types.SessionCapability` message that must be sent back
    to the client.
    """


@RegisterEvent
class SetMaxRunspacesEvent(PSRPEvent[SetMaxRunspaces, None]):
    """Set Max Runspaces Event.

    Event Information:

        Direction: Client -> Server

        For: Runspace Pool

        Message Type: :class:`psrpcore.types.SetMaxRunspaces`

        Action Required:

    The client sends this when trying to adjust the maximum available runspaces
    in a pool.
    """


@RegisterEvent
class SetMinRunspacesEvent(PSRPEvent[SetMinRunspaces, None]):
    """Set Min Runspaces Event.

    Event Information:

        Direction: Client -> Server

        For: Runspace Pool

        Message Type: :class:`psrpcore.types.SetMinRunspaces`

        Action Required:

    The client sends this when trying to adjust the minimum available runspaces
    in a pool.
    """


@RegisterEvent
class UserEventEvent(PSRPEvent[UserEvent, None]):
    """User Event Event.

    Event Information:

        Direction: Server -> Client

        For: Runspace Pool or Pipeline

        Message Type: :class:`psrpcore.types.UserEvent`

        Action Required: Send to higher layer

    The server sends this message when reporting a user defined event from the
    runspace. THe data should be shared with the higher layer as necessary.
    """


@RegisterEvent
class VerboseRecordEvent(PSRPEvent[VerboseRecordMsg, _OptionalPipelineType]):
    """Verbose Record Event.

    Event Information:

        Direction: Server -> Client

        For: Runspace Pool or Pipeline

        Message Type: :class:`psrpcore.types.VerboseRecordMsg`

        Action Required: Send to higher layer

    The server sends this message when there is a verbose record generated by
    the server. The data should be shared with the higher layer as necessary.
    """


@RegisterEvent
class WarningRecordEvent(PSRPEvent[WarningRecordMsg, _OptionalPipelineType]):
    """Warning Record Event.

    Event Information:

        Direction: Server -> Client

        For: Runspace Pool or Pipeline

        Message Type: :class:`psrpcore.types.WarningRecordMsg`

        Action Required: Send to higher layer

    The server sends this message when there is a warning record generated by
    the server. The data should be shared with the higher layer as necessary.
    """
