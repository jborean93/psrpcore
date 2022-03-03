# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import base64
import typing
import uuid

from psrpcore._pipeline import GetMetadata, PowerShell
from psrpcore.types import (
    ApartmentState,
    ApplicationPrivateData,
    BufferCell,
    ChoiceDescription,
    ConnectRunspacePool,
    ConsoleColor,
    Coordinates,
    CreatePipeline,
    DebugRecord,
    DebugRecordMsg,
    EncryptedSessionKey,
    EndOfPipelineInput,
    ErrorRecord,
    ErrorRecordMsg,
    FieldDescription,
    GetAvailableRunspaces,
    GetCommandMetadata,
    HostInfo,
    HostMethodIdentifier,
    InformationRecord,
    InformationRecordMsg,
    InitRunspacePool,
    KeyInfo,
    PipelineHostCall,
    PipelineHostResponse,
    PipelineState,
    ProgressRecord,
    ProgressRecordMsg,
    PSBool,
    PSCredentialTypes,
    PSCredentialUIOptions,
    PSInvocationState,
    PSObject,
    PSRPMessageType,
    PSThreadOptions,
    PSVersion,
    PublicKey,
    PublicKeyRequest,
    ReadKeyOptions,
    Rectangle,
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
    Size,
    UserEvent,
    VerboseRecord,
    VerboseRecordMsg,
    WarningRecord,
    WarningRecordMsg,
)

T1 = typing.TypeVar("T1")
T2 = typing.TypeVar("T2")
_OptionalPipelineType = typing.Optional[uuid.UUID]


def _decode_host_resp_result(
    method: HostMethodIdentifier,
    result: typing.Any,
) -> typing.Optional[typing.Any]:
    if result is None:
        return None

    elif method in [HostMethodIdentifier.GetForegroundColor, HostMethodIdentifier.GetBackgroundColor]:
        return ConsoleColor(result)

    elif method in [HostMethodIdentifier.GetCursorPosition, HostMethodIdentifier.GetWindowPosition]:
        return Coordinates.FromPSObjectForRemoting(result)

    elif method in [
        HostMethodIdentifier.GetBufferSize,
        HostMethodIdentifier.GetWindowSize,
        HostMethodIdentifier.GetMaxWindowSize,
        HostMethodIdentifier.GetMaxPhysicalWindowSize,
    ]:
        return Size.FromPSObjectForRemoting(result)

    elif method == HostMethodIdentifier.ReadKey:
        return KeyInfo.FromPSObjectForRemoting(result)

    elif method == HostMethodIdentifier.GetBufferContents:
        return _unpack_multi_dimensional_array(result, BufferCell.FromPSObjectForRemoting)

    else:
        return result


def _decode_host_call_parameters(
    method: HostMethodIdentifier,
    parameters: typing.List[typing.Any],
) -> typing.List[typing.Any]:
    if method in [HostMethodIdentifier.Write2, HostMethodIdentifier.WriteLine3]:
        return [ConsoleColor(parameters[0]), ConsoleColor(parameters[1]), parameters[2]]

    elif method == HostMethodIdentifier.WriteProgress:
        return [
            parameters[0],
            ProgressRecord(
                Activity=parameters[1].Activity,
                ActivityId=parameters[1].ActivityId,
                CurrentOperation=parameters[1].CurrentOperation,
                ParentActivityId=parameters[1].ParentActivityId,
                PercentComplete=parameters[1].PercentComplete,
                RecordType=parameters[1].Type,
                SecondsRemaining=parameters[1].SecondsRemaining,
                StatusDescription=parameters[1].StatusDescription,
            ),
        ]

    elif method == HostMethodIdentifier.Prompt:
        return [
            parameters[0],
            parameters[1],
            [FieldDescription.FromPSObjectForRemoting(f) for f in parameters[2]],
        ]

    elif method == HostMethodIdentifier.PromptForCredential2:
        return [
            parameters[0],
            parameters[1],
            parameters[2],
            parameters[3],
            PSCredentialTypes(parameters[4]),
            PSCredentialUIOptions(parameters[5]),
        ]

    elif method in [HostMethodIdentifier.PromptForChoice, HostMethodIdentifier.PromptForChoiceMultipleSelection]:
        return [
            parameters[0],
            parameters[1],
            [ChoiceDescription.FromPSObjectForRemoting(c) for c in parameters[2]],
            parameters[3],
        ]

    elif method in [HostMethodIdentifier.SetForegroundColor, HostMethodIdentifier.SetBackgroundColor]:
        return [ConsoleColor(parameters[0])]

    elif method in [HostMethodIdentifier.SetCursorPosition, HostMethodIdentifier.SetWindowPosition]:
        return [Coordinates.FromPSObjectForRemoting(parameters[0])]

    elif method in [HostMethodIdentifier.SetBufferSize, HostMethodIdentifier.SetWindowSize]:
        return [Size.FromPSObjectForRemoting(parameters[0])]

    elif method == HostMethodIdentifier.ReadKey:
        return [ReadKeyOptions(parameters[0])]

    elif method == HostMethodIdentifier.SetBufferContents1:
        return [Rectangle.FromPSObjectForRemoting(parameters[0]), BufferCell.FromPSObjectForRemoting(parameters[1])]

    elif method == HostMethodIdentifier.SetBufferContents2:
        cells = _unpack_multi_dimensional_array(parameters[1], BufferCell.FromPSObjectForRemoting)
        return [Coordinates.FromPSObjectForRemoting(parameters[0]), cells]

    elif method == HostMethodIdentifier.GetBufferContents:
        return [Rectangle.FromPSObjectForRemoting(parameters[0])]

    elif method == HostMethodIdentifier.ScrollBufferContents:
        return [
            Rectangle.FromPSObjectForRemoting(parameters[0]),
            Coordinates.FromPSObjectForRemoting(parameters[1]),
            Rectangle.FromPSObjectForRemoting(parameters[2]),
            BufferCell.FromPSObjectForRemoting(parameters[3]),
        ]

    else:
        return parameters


def _unpack_multi_dimensional_array(
    obj: PSObject,
    unpack_obj: typing.Callable[[PSObject], typing.Any],
) -> typing.List:

    final_list: typing.List[typing.Any] = [unpack_obj(o) for o in obj.mae]
    for count in reversed(obj.mal):
        to_enumerate = final_list
        final_list = []

        entries: typing.Any = []
        for entry in to_enumerate:
            entries.append(entry)
            if len(entries) == count:
                final_list.append(entries)
                entries = []

    return final_list[0]


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
        self.runspace_pool_id = runspace_pool_id
        self.pipeline_id = pipeline_id

        self._ps_object = ps_object

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

    def __repr__(self) -> str:
        return f"<{type(self).__name__} runspace_pool_id={self.runspace_pool_id!r} pipeline_id={self.pipeline_id!r}>"


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

    @property
    def data(self) -> typing.Dict[str, typing.Any]:
        """The private data dictionary returned from the server."""
        return self._ps_object.ApplicationPrivateData

    def __repr__(self) -> str:
        return f"<{type(self).__name__} runspace_pool_id={self.runspace_pool_id!r}: {self.data!r}>"


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

    @property
    def max_runspaces(self) -> typing.Optional[int]:
        """The maximum number of runspaces in the Runspace Pool."""
        return getattr(self._ps_object, "MaxRunspaces", None)

    @property
    def min_runspaces(self) -> typing.Optional[int]:
        """The minimum number of runspaces in the Runspace Pool."""
        return getattr(self._ps_object, "MinRunspaces", None)

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} runspace_pool_id={self.runspace_pool_id!r} "
            f"min_runspaces={self.min_runspaces} max_runspaces={self.max_runspaces}>"
        )


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

    @property
    def pipeline(self) -> PowerShell:
        """The PowerShell pipeline details."""
        return PowerShell.FromPSObjectForRemoting(self._ps_object)

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} runspace_pool_id={self.runspace_pool_id!r} pipeline_id={self.pipeline_id!r} "
            f"pipeline={self.pipeline!r}>"
        )


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

    @property
    def record(self) -> DebugRecord:
        """The DebugRecord emitted by the peer."""
        return self._ps_object

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} runspace_pool_id={self.runspace_pool_id!r} pipeline_id={self.pipeline_id!r} "
            f"record={self.record.Message!r}>"
        )


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

    @property
    def key(self) -> bytes:
        """The session key generated by the peer."""
        return base64.b64decode(self._ps_object.EncryptedSessionKey)


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

    @property
    def record(self) -> ErrorRecord:
        """The ErrorRecord emitted by the peer."""
        return self._ps_object

    def __repr__(self) -> str:
        err = str(self.record)
        return (
            f"<{type(self).__name__} runspace_pool_id={self.runspace_pool_id!r} pipeline_id={self.pipeline_id!r} "
            f"record={err!r}>"
        )


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

    @property
    def ci(self) -> int:
        """The call id associated with the request."""
        return self._ps_object.ci

    def __repr__(self) -> str:
        return f"<{type(self).__name__} runspace_pool_id={self.runspace_pool_id!r} ci={self.ci}>"


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

    @property
    def pipeline(self) -> GetMetadata:
        """The GetCommandMetadata pipeline details."""
        return GetMetadata.FromPSObjectForRemoting(self._ps_object)

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} runspace_pool_id={self.runspace_pool_id!r} pipeline_id={self.pipeline_id!r} "
            f"pipeline={self.pipeline!r}>"
        )


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

    @property
    def record(self) -> InformationRecord:
        """The InformationRecord emitted by the peer."""
        # The raw PSObject generated in an INFORMATION_RECORD msg looks like a Information record but isn't exactly the
        # same. It serialzies with extended props whereas a proper info record uses adapted properties. By creating
        # the object and just copying the properties over as is it will seem like the object is the same as a normal
        # info record as defined in types.
        info = InformationRecord()
        info.PSObject.adapted_properties = self._ps_object.PSObject.extended_properties

        return info

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} runspace_pool_id={self.runspace_pool_id!r} pipeline_id={self.pipeline_id!r} "
            f"record={self.record.MessageData!r}>"
        )


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

    @property
    def max_runspaces(self) -> int:
        """The maximum number of runspaces in the Runspace Pool."""
        return self._ps_object.MaxRunspaces

    @property
    def min_runspaces(self) -> int:
        """The minimum number of runspaces in the Runspace Pool."""
        return self._ps_object.MinRunspaces

    @property
    def ps_thread_options(self) -> PSThreadOptions:
        """The PowerShell thread options specified by the peer."""
        return self._ps_object.PSThreadOptions

    @property
    def apartment_state(self) -> ApartmentState:
        """The apartment state specified by the peer."""
        return self._ps_object.ApartmentState

    @property
    def host_info(self) -> HostInfo:
        """The PSHost info provided by the peer."""
        return HostInfo.FromPSObjectForRemoting(self._ps_object.HostInfo)

    @property
    def application_arguments(self) -> typing.Dict[str, typing.Any]:
        """Higher layer application arguments provided by the peer."""
        return self._ps_object.ApplicationArguments

    def __repr__(self) -> str:
        kw = " ".join(
            [
                f"{k}={getattr(self, k)!r}"
                for k in [
                    "min_runspaces",
                    "max_runspaces",
                    "ps_thread_options",
                    "apartment_state",
                    "host_info",
                    "application_arguments",
                ]
            ]
        )
        return f"<{type(self).__name__} runspace_pool_id={self.runspace_pool_id!r} {kw}>"


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

    @property
    def ci(self) -> int:
        """The call id associated with the request."""
        return self._ps_object.ci

    @property
    def method_identifier(self) -> HostMethodIdentifier:
        """The method that needs to be invoked."""
        return self._ps_object.mi

    @property
    def method_parameters(self) -> typing.List[typing.Any]:
        """List of parameters to invoke the method with."""
        return _decode_host_call_parameters(self._ps_object.mi, self._ps_object.mp or [])

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} runspace_pool_id={self.runspace_pool_id!r} pipeline_id={self.pipeline_id!r} "
            f"ci={self.ci} method_identifier={self.method_identifier!r} method_parameters={self.method_parameters!r}>"
        )


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

    @property
    def ci(self) -> int:
        """The call id associated with the request."""
        return self._ps_object.ci

    @property
    def method_identifier(self) -> HostMethodIdentifier:
        """The method that was invoked."""
        return self._ps_object.mi

    @property
    def result(self) -> typing.Optional[typing.Any]:
        """The result (if any) from the host call."""
        return _decode_host_resp_result(self._ps_object.mi, getattr(self._ps_object, "mr", None))

    @property
    def error(self) -> typing.Optional[ErrorRecord]:
        """The error record if the host call failed."""
        me = getattr(self._ps_object, "me", None)
        if me and not isinstance(me, ErrorRecord):
            return ErrorRecord.FromPSObjectForRemoting(me)
        else:
            return me

    def __repr__(self) -> str:
        error = str(self.error) if self.error else None
        return (
            f"<{type(self).__name__} runspace_pool_id={self.runspace_pool_id!r} pipeline_id={self.pipeline_id!r} "
            f"ci={self.ci} method_identifier={self.method_identifier!r} result={self.result!r} error={error!r}>"
        )


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

    @property
    def data(self) -> typing.Any:
        """The data sent as input."""
        return self._ps_object

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} runspace_pool_id={self.runspace_pool_id!r} pipeline_id={self.pipeline_id!r} "
            f"data={self.data!r}>"
        )


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

    @property
    def data(self) -> typing.Any:
        """The data sent as output."""
        return self._ps_object

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} runspace_pool_id={self.runspace_pool_id!r} pipeline_id={self.pipeline_id!r} "
            f"data={self.data!r}>"
        )


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
        return PSInvocationState(self._ps_object.PipelineState)

    @property
    def reason(self) -> typing.Optional[ErrorRecord]:
        """An error record containing the reason why the pipeline is ``Failed``."""
        return getattr(self._ps_object, "ExceptionAsErrorRecord", None)

    def __repr__(self) -> str:
        reason = str(self.reason) if self.reason else None
        return (
            f"<{type(self).__name__} runspace_pool_id={self.runspace_pool_id!r} pipeline_id={self.pipeline_id!r} "
            f"state={self.state!r} reason={reason!r}>"
        )


@RegisterEvent
class ProgressRecordEvent(PSRPEvent[ProgressRecordMsg, _OptionalPipelineType]):
    """Progress Record Event.

    Event Information:

        Direction: Server -> Client

        For: Runspace Pool or Pipeline

        Message Type: :class:`psrpcore.types.ProgressRecordMsg`

        Action Required: Send to higher layer

    The server sends this message when there is a progress record generated by
    the server. The data should be shared with the higher layer as necessary.
    """

    @property
    def record(self) -> ProgressRecord:
        """The progress record emitted by the peer."""
        return ProgressRecord(
            Activity=self._ps_object.Activity,
            ActivityId=self._ps_object.ActivityId,
            CurrentOperation=self._ps_object.CurrentOperation,
            ParentActivityId=self._ps_object.ParentActivityId,
            PercentComplete=self._ps_object.PercentComplete,
            RecordType=self._ps_object.Type,
            SecondsRemaining=self._ps_object.SecondsRemaining,
            StatusDescription=self._ps_object.StatusDescription,
        )


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

    @property
    def key(self) -> bytes:
        """The public key bytes from the peer."""
        return base64.b64decode(self._ps_object.PublicKey)


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

    @property
    def ci(self) -> int:
        """The call id associated with the request."""
        return self._ps_object.ci

    def __repr__(self) -> str:
        return f"<{type(self).__name__} runspace_pool_id={self.runspace_pool_id!r} ci={self.ci}>"


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

    @property
    def ci(self) -> int:
        """The call id associated with the request."""
        return self._ps_object.ci


class SetRunspaceAvailabilityEvent(RunspaceAvailabilityEvent):
    """Set Runspace Availability Event.

    Event Information:

        Direction: Server -> Client

        For: Runspace Pool

        Message Type: :class:`psrpcore.types.RunspaceAvailability`

        Action Required: Send to higher layer

    The server sends this message in resposne to a
    :class:`psrpcore.types.SetMaxRunspaces`,
    :class:`psrpcore.types.SetMinRunspaces`, or
    :class:`psrpcore.types.ResetRunspaceState` message. The client
    automatically adjusts the runspace limits based on the response.
    """

    @property
    def success(self) -> bool:
        """Whether the request suceeded or not."""
        return self._ps_object.SetMinMaxRunspacesResponse

    def __repr__(self) -> str:
        return f"<{type(self).__name__} runspace_pool_id={self.runspace_pool_id!r} ci={self.ci} success={self.success}>"


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
        return int(self._ps_object.SetMinMaxRunspacesResponse)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} runspace_pool_id={self.runspace_pool_id!r} ci={self.ci} count={self.count}>"


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

    @property
    def ci(self) -> int:
        """The call id associated with the request."""
        return self._ps_object.ci

    @property
    def method_identifier(self) -> HostMethodIdentifier:
        """The method that needs to be invoked."""
        return self._ps_object.mi

    @property
    def method_parameters(self) -> typing.List[typing.Any]:
        """List of parameters to invoke the method with."""
        return _decode_host_call_parameters(self._ps_object.mi, self._ps_object.mp or [])

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} runspace_pool_id={self.runspace_pool_id!r} ci={self.ci} "
            f"method_identifier={self.method_identifier!r} method_parameters={self.method_parameters!r}>"
        )


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

    @property
    def ci(self) -> int:
        """The call id associated with the request."""
        return self._ps_object.ci

    @property
    def method_identifier(self) -> HostMethodIdentifier:
        """The method that was invoked."""
        return self._ps_object.mi

    @property
    def result(self) -> typing.Optional[typing.Any]:
        """The result (if any) from the host call."""
        return _decode_host_resp_result(self._ps_object.mi, getattr(self._ps_object, "mr", None))

    @property
    def error(self) -> typing.Optional[ErrorRecord]:
        """The error record if the host call failed."""
        return getattr(self._ps_object, "me", None)

    def __repr__(self) -> str:
        error = str(self.error) if self.error else None
        return (
            f"<{type(self).__name__} runspace_pool_id={self.runspace_pool_id!r} ci={self.ci} "
            f"method_identifier={self.method_identifier!r} result={self.result!r} error={error!r}>"
        )


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

    @property
    def max_runspaces(self) -> int:
        """The maximum number of runspaces in the Runspace Pool."""
        return self._ps_object.MaxRunspaces

    @property
    def min_runspaces(self) -> int:
        """The minimum number of runspaces in the Runspace Pool."""
        return self._ps_object.MinRunspaces

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} runspace_pool_id={self.runspace_pool_id!r} "
            f"min_runspaces={self.min_runspaces} max_runspaces={self.max_runspaces}>"
        )


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
        return RunspacePoolState(self._ps_object.RunspaceState)

    @property
    def reason(self) -> typing.Optional[ErrorRecord]:
        """An error record containing the reason why the runspace is ``Broken``."""
        return getattr(self._ps_object, "ExceptionAsErrorRecord", None)

    def __repr__(self) -> str:
        reason = str(self.reason) if self.reason else None
        return (
            f"<{type(self).__name__} runspace_pool_id={self.runspace_pool_id!r} state={self.state!r} "
            f"reason={reason!r}>"
        )


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

    @property
    def ps_version(self) -> PSVersion:
        """The PowerShell version of the peer."""
        return self._ps_object.PSVersion

    @property
    def protocol_version(self) -> PSVersion:
        """The protocol version of the peer."""
        return self._ps_object.protocolversion

    @property
    def serialization_version(self) -> PSVersion:
        """The version of the peer's serializer."""
        return self._ps_object.SerializationVersion

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} runspace_pool_id={self.runspace_pool_id!r} ps_version={self.ps_version} "
            f"protocol_version={self.protocol_version} serialization_version={self.serialization_version}>"
        )


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

    @property
    def ci(self) -> int:
        """The call id associated with the request."""
        return self._ps_object.ci

    @property
    def count(self) -> int:
        """The maximum runspace count to set."""
        return self._ps_object.MaxRunspaces

    def __repr__(self) -> str:
        return f"<{type(self).__name__} runspace_pool_id={self.runspace_pool_id!r} ci={self.ci} count={self.count}>"


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

    @property
    def ci(self) -> int:
        """The call id associated with the request."""
        return self._ps_object.ci

    @property
    def count(self) -> int:
        """The minimum runspace count to set."""
        return self._ps_object.MinRunspaces

    def __repr__(self) -> str:
        return f"<{type(self).__name__} runspace_pool_id={self.runspace_pool_id!r} ci={self.ci} count={self.count}>"


@RegisterEvent
class UserEventEvent(PSRPEvent[UserEvent, None]):
    """User Event Event.

    Event Information:

        Direction: Server -> Client

        For: Runspace Pool or Pipeline

        Message Type: :class:`psrpcore.types.UserEvent`

        Action Required: Send to higher layer

    The server sends this message when reporting a user defined event from the
    runspace. The data should be shared with the higher layer as necessary.
    """

    @property
    def event(self) -> UserEvent:
        """The user event received from the peer."""
        return UserEvent.FromPSObjectForRemoting(self._ps_object)


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

    @property
    def record(self) -> VerboseRecord:
        """The VerboseRecord emitted by the peer."""
        return self._ps_object

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} runspace_pool_id={self.runspace_pool_id!r} pipeline_id={self.pipeline_id!r} "
            f"record={self.record.Message!r}>"
        )


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

    @property
    def record(self) -> WarningRecord:
        """The WarningRecord emitted by the peer."""
        return self._ps_object

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} runspace_pool_id={self.runspace_pool_id!r} pipeline_id={self.pipeline_id!r} "
            f"record={self.record.Message!r}>"
        )
