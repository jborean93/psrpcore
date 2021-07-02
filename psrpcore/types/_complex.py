# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

"""PSRP/.NET Complex Types.

The PSRP/.NET Complex Type class definitions. A complex type is pretty much
anything that isn't a primitive type as known to the protocol. Most of the
types defined here are defined in `MS-PSRP 2.2.3 Other Object Types`_ but some
are also just other .NET objects that are used in the PSRP protocol. Some types
are a PSRP specific representation of an actual .NET type but with a few minor
differences. These types are prefixed with `PSRP` to differentiate between the
PSRP specific ones and the actual .NET types.

.. _MS-PSRP 2.2.3 Other Object Types:
    https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/e41c4a38-a821-424b-bc1c-89f8478c39ae
"""

import collections
import ntpath
import posixpath
import typing

from psrpcore.types._base import (
    PSAliasProperty,
    PSNoteProperty,
    PSObject,
    PSScriptProperty,
    PSType,
    add_note_property,
)
from psrpcore.types._collection import PSDict, PSList
from psrpcore.types._enum import PSEnumBase, PSFlagBase
from psrpcore.types._primitive import (
    PSBool,
    PSChar,
    PSDateTime,
    PSInt,
    PSInt64,
    PSSecureString,
    PSString,
    PSUInt,
)

# We are just using a named tuple for now, this should be a class in the future
# if CommandInfo is ever implemented.
RemoteCommandInfo = collections.namedtuple("RemoteCommandInfo", ["CommandType", "Name", "Definition", "Visibility"])


@PSType(["System.Management.Automation.PSCustomObject"])
class PSCustomObject(PSObject):
    """PSCustomObject

    This is a PSCustomObject that can be created with an arbitrary amount of
    extended properties. It acts like a generic property bag and is designed to
    replicate the PSCustomObject syntax in PowerShell:

    .. code-block:: powershell

        $obj = [PSCustomObject]@{
            Property = 'value'
        }

    Examples:
        >>> obj = PSCustomObject(Property='value')
        >>> print(obj.Property)
        abc

    Note:
        The property `PSTypeName` is a special property used to define a custom
        PS type name to the instance. It will not add a property with the name
        `PSTypeName`.
    """

    def __init__(self, **kwargs: typing.Any) -> None:
        for prop_name, prop_value in kwargs.items():
            # Special use case with [PSCustomObject]@{PSTypeName = 'TypeName'} in PowerShell where the value is
            # added to the top of the objects type names.
            if prop_name == "PSTypeName":
                self.PSObject.type_names.insert(0, prop_value)

            else:
                self.PSObject.extended_properties.append(PSNoteProperty(prop_name, value=prop_value))


@PSType(["System.ConsoleColor"])
class ConsoleColor(PSEnumBase):
    """System.ConsoleColor enum.

    Specifies constants that define foreground and background colors for the
    console. This is also documented under `[MS-PSRP] 2.2.3.3 Color`_ but in
    the :class:`HostInfo` default data format.

    Note:
        This is an auto-generated Python class for the `System.ConsoleColor`_
        .NET class.

    .. _System.ConsoleColor:
        https://docs.microsoft.com/en-us/dotnet/api/system.consolecolor?view=net-5.0

    .. _[MS-PSRP] 2.2.3.3 Color:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/d7edefec-41b1-465d-bc07-2a8ec9d727a1
    """

    Black = 0
    DarkBlue = 1
    DarkGreen = 2
    DarkCyan = 3
    DarkRed = 4
    DarkMagenta = 5
    DarkYellow = 6
    Gray = 7
    DarkGray = 8
    Blue = 9
    Green = 10
    Cyan = 11
    Red = 12
    Magenta = 13
    Yellow = 14
    White = 15


@PSType(["System.Management.Automation.ProgressRecordType"])
class ProgressRecordType(PSEnumBase):
    """System.Management.Automation.ProgressRecordType enum.

    Defines two types of progress record that refer to the beginning
    (or middle) and end of an operation.

    Note:
        This is an auto-generated Python class for the
        `System.Management.Automation.ProgressRecordType`_ .NET class.

    .. _System.Management.Automation.ProgressRecordType:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.progressrecordtype
    """

    Processing = 0  #: Operation just started or is not yet complete.
    Completed = 1  #: Operation is complete.


@PSType(["System.Management.Automation.PSCredentialTypes"])
class PSCredentialTypes(PSFlagBase):
    """System.Management.Automation.PSCredentialTypes enum flags.

    Defines the valid types of credentials. Used by
    :meth:`psrp.host.PSHostUI.prompt_for_credential2` calls.

    Note:
        This is an auto-generated Python class for the
        `System.Management.Automation.PSCredentialTypes`_ .NET class.

    .. _System.Management.Automation.PSCredentialTypes:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.pscredentialtypes
    """

    Generic = 1  #: Generic credentials.
    Domain = 2  #: Credentials valid for a domain.
    Default = Generic | Domain  #: Default credentials (Generic | Domain).


@PSType(["System.Management.Automation.PSCredentialUIOptions"])
class PSCredentialUIOptions(PSFlagBase):
    """System.Management.Automation.PSCredentialUIOptions enum flags.

    Defines the options available when prompting for credentials. Used by
    :meth:`psrp.host.PSHostUI.prompt_for_credential2` calls.

    Note:
        This is an auto-generated Python class for the
        `System.Management.Automation.PSCredentialUIOptions`_ .NET class.

    .. _System.Management.Automation.PSCredentialUIOptions:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.pscredentialuioptions
    """

    none = 0  #: Performs no validation.
    ValidateUserNameSyntax = 1  #: Validates the username, but not its existence or correctness.
    AlwaysPrompt = 2  #: Always prompt, even if a persisted credential was available.
    ReadOnlyUsername = 3  #: Username is read-only, and the user may not modify it.
    Default = ValidateUserNameSyntax  #: Validates the username, but not its existence or correctness.


@PSType(["System.Management.Automation.SessionStateEntryVisibility"])
class SessionStateEntryVisibility(PSEnumBase):
    """System.Management.Automation.SessionStateEntryVisibility enum.

    Defines the visibility of execution environment elements.

    Note:
        This is an auto-generated Python class for the
        `System.Management.Automation.SessionStateEntryVisibility`_ .NET class.

    .. _System.Management.Automation.SessionStateEntryVisibility:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.sessionstateentryvisibility
    """

    Public = 0  #: Entries are visible to requests from outside the runspace.
    Private = 1  #: Entries are not visible to requests from outside the runspace.


@PSType(["System.Management.Automation.Runspaces.RunspacePoolState"])
class RunspacePoolState(PSEnumBase):
    """RunspacePoolState enum.

    Defines the current state of the Runspace Pool. It is documented in PSRP
    under `[MS-PSRP] 2.2.3.4 RunspacePoolState`_ and while it shares the same
    name as the .NET type
    `System.Management.Automation.Runspaces.RunspacePoolState`_ it has a few
    values that do not match. The .NET values are favoured here and any ones
    that are in the PSRP docs and not in the enum have been manually defined.

    .. _[MS-PSRP] 2.2.3.4 RunspacePoolState:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/b05495bc-a9b2-4794-9f43-4bf1f3633900

    .. _System.Management.Automation.Runspaces.RunspacePoolState:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.runspaces.runspacepoolstate
    """

    BeforeOpen = 0  #: Beginning state upon creation.
    Opening = 1  #: A RunspacePool is being created.
    Opened = 2  #: The RunspacePool is created and valid.
    Closed = 3  #: The RunspacePool is closed.
    Closing = 4  #: The RunspacePool is being closed.
    Broken = 5  #: The RunspacePool has been disconnected abnormally.
    Disconnecting = 6  #: The RunspacePool is being disconnected.
    # 9 in PSRP
    Disconnected = 7  #: The RunspacePool has been disconnected.
    Connecting = 8  #: The RunspacePool is being connected.
    # Referenced as 6 and 7 in MS-PSRP but are internal only so just use a random value
    NegotiationSent = 100  #: :class:`psrp.dotnet.psrp_messages.SessionCapability` sent to peer.
    NegotiationSucceeded = 101  #: :class:`psrp.dotnet.psrp_messages.SessionCapability` received from peer.


@PSType(["System.Management.Automation.PSInvocationState"])
class PSInvocationState(PSEnumBase):
    """PSInvocationState enum.

    Defines the current state of the Pipeline. It is documented in PSRP under
    `[MS-PSRP] 2.2.3.5 PSInvocationState`_.

    Note:
        This is an auto-generated Python class for the
        `System.Management.Automation.PSInvocationState`_ .NET class.

    .. _[MS-PSRP] 2.2.3.5 PSInvocationState:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/acaa253a-29be-45fd-911c-6715515a28b9

    .. _System.Management.Automation.PSInvocationState:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.psinvocationstate
    """

    NotStarted = 0  #: Pipeline has not been started
    Running = 1  #: Pipeline is executing.
    Stopping = 2  #: Pipeline is stopping execution.
    Stopped = 3  #: Pipeline is completed due to a stop request.
    Completed = 4  #: Pipeline has completed executing a command.
    Failed = 5  #: Pipeline completed abnormally due to an error.
    Disconnected = 6  #: Pipeline is in disconnected state.


@PSType(["System.Management.Automation.Runspaces.PSThreadOptions"])
class PSThreadOptions(PSEnumBase):
    """System.Management.Automation.Runspaces.PSThreadOptions enum.

    Control whether a new thread is created when a command is executed within a
    Runspace. It is documented in PSRP under
    `[MS-PSRP] 2.2.3.6 PSThreadOptions`_.

    Note:
        This is an auto-generated Python class for the
        `System.Management.Automation.Runspaces.PSThreadOptions`_ .NET class.

    .. _[MS-PSRP] 2.2.3.6 PSThreadOptions:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/bfc63adb-d6f1-4ccc-9bd8-73de6cc78dda

    .. _System.Management.Automation.Runspaces.PSThreadOptions:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.runspaces.psthreadoptions
    """

    Default = 0  #: Use the server thread option settings.
    UseNewThread = 1  #: Creates a new thread for each invocation.
    ReuseThread = 2
    """ Creates a new thread for the first invocation and then re-uses that thread in subsequent invocations. """
    UseCurrentThread = 3  #: Doesn't create a new thread; the execution occurs on the thread that called Invoke.


@PSType(["System.Threading.ApartmentState"])
class ApartmentState(PSEnumBase):
    """System.Management.Automation.Runspaces.ApartmentState enum.

    Specifies the apartment state of a Thread. It is documented in PSRP under
    `[MS-PSRP] 2.2.3.7 ApartmentState`_.

    Note:
        This is an auto-generated Python class for the
        `System.Threading.ApartmentState`_ .NET class.

    .. _[MS-PSRP] 2.2.3.7 ApartmentState:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/6845133d-7503-450d-a74e-388cdd3b2386

    .. _System.Threading.ApartmentState:
        https://docs.microsoft.com/en-us/dotnet/api/system.threading.apartmentstate?view=net-5.0
    """

    STA = 0  #: The thread will create and enter a multi-threaded apartment.
    MTA = 1  #: The thread will create and enter a single-threaded apartment.
    Unknown = 2  #: The ApartmentState property has not been set.


@PSType(["System.Management.Automation.RemoteStreamOptions"])
class RemoteStreamOptions(PSFlagBase):
    """System.Management.Automation.RemoteStreamOptions enum flags.

    Control whether InvocationInfo is added to items in the Error, Warning,
    Verbose and Debug streams during remote calls. It is documented in PSRP
    under `[MS-PSRP] 2.2.3.8 RemoteStreamOptions`_.

    Note:
        This is an auto-generated Python class for the
        `System.Management.Automation.RemoteStreamOptions`_ .NET class.

    .. _[MS-PSRP] 2.2.3.8 RemoteStreamOptions:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/4941e59c-ce01-4549-8eb5-372b8eb6dd12

    .. _System.Management.Automation.RemoteStreamOptions:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.remotestreamoptions
    """

    none = 0  #: InvocationInfo is not added to any stream record.
    AddInvocationInfoToErrorRecord = 1  #: InvocationInfo is added to any :class:`ErrorRecord`.
    AddInvocationInfoToWarningRecord = 2  #: InvocationInfo is added to any `Warning` :class:`InformationalRecord`.
    AddInvocationInfoToDebugRecord = 4  #: InvocationInfo is added to any `Debug` :class:`InformationalRecord`.
    AddInvocationInfoToVerboseRecord = 8  #: InvocationInfo is added to any `Verbose` :class:`InformationalRecord`.
    AddInvocationInfo = 15  #: InvocationInfo is added to all stream records.


@PSType(["System.Management.Automation.ErrorCategory"])
class ErrorCategory(PSEnumBase):
    """System.Management.Automation.ErrorCategory enum.

    Errors reported by PowerShell will be in one of these categories. It is
    documented in PSRP under `[MS-PSRP] 2.2.3.9 ErrorCategory`_.

    Note:
        This is an auto-generated Python class for the
        `System.Management.Automation.ErrorCategory`_ .NET class.

    .. _[MS-PSRP] 2.2.3.9 ErrorCategory:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/ae7d6061-15c8-4184-a05e-1033dbb7228b

    .. _System.Management.Automation.ErrorCategory:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.errorcategory
    """

    NotSpecified = 0  #: No error category is specified, or the error category is invalid.
    OpenError = 1
    CloseError = 2
    DeviceError = 3
    DeadlockDetected = 4
    InvalidArgument = 5
    InvalidData = 6
    InvalidOperation = 7
    InvalidResult = 8
    InvalidType = 9
    MetadataError = 10
    NotImplemented = 11
    NotInstalled = 12
    ObjectNotFound = 13  #: Object can not be found (file, directory, computer, system resource, etc.).
    OperationStopped = 14
    OperationTimeout = 15
    SyntaxError = 16
    ParserError = 17
    PermissionDenied = 18  #: Operation not permitted.
    ResourceBusy = 19
    ResourceExists = 20
    ResourceUnavailable = 21
    ReadError = 22
    WriteError = 23
    FromStdErr = 24  #: A non-PowerShell command reported an error to its STDERR pipe.
    SecurityError = 25  #: Used for security exceptions.
    ProtocolError = 26  #: The contract of a protocol is not being followed.
    ConnectionError = 27  #: The operation depends on a network connection that cannot be established or maintained.
    AuthenticationError = 28  #: Could not authenticate the user to the service.
    LimitsExceeded = 29  #: Internal limits prevent the operation from being executed.
    QuotaExceeded = 30  #: Controls on the use of traffic or resources prevent the operation from being executed.
    NotEnabled = 31  #: The operation attempted to use functionality that is currently disabled.


@PSType(["System.Management.Automation.Remoting.RemoteHostMethodId"])
class HostMethodIdentifier(PSEnumBase):
    """Host Method Identifier enum.

    This is an enum class for the
    System.Management.Automation.Remoting.RemoteHostMethodId .NET class. It is
    documented in PSRP under `[MS-PSRP] 2.2.3.17 Host Method Identifier`_.

    The values are used to reference what method to invoke on
    :class:`psrp.host.PSHost`.

    .. _[MS-PSRP] 2.2.3.17 Host Method Identifier:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/ddd2a4d1-797d-4d73-8372-7a77a62fb204
    """

    GetName = 1
    GetVersion = 2
    GetInstanceId = 3
    GetCurrentCulture = 4
    GetCurrentUICulture = 5
    SetShouldExit = 6
    EnterNestedPrompt = 7
    ExitNestedPrompt = 8
    NotifyBeginApplication = 9
    NotifyEndApplication = 10
    ReadLine = 11
    ReadLineAsSecureString = 12
    Write1 = 13
    Write2 = 14
    WriteLine1 = 15
    WriteLine2 = 16
    WriteLine3 = 17
    WriteErrorLine = 18
    WriteDebugLine = 19
    WriteProgress = 20
    WriteVerboseLine = 21
    WriteWarningLine = 22
    Prompt = 23
    PromptForCredential1 = 24
    PromptForCredential2 = 25
    PromptForChoice = 26
    GetForegroundColor = 27
    SetForegroundColor = 28
    GetBackgroundColor = 29
    SetBackgroundColor = 30
    GetCursorPosition = 31
    SetCursorPosition = 32
    GetWindowPosition = 33
    SetWindowPosition = 34
    GetCursorSize = 35
    SetCursorSize = 36
    GetBufferSize = 37
    SetBufferSize = 38
    GetWindowSize = 39
    SetWindowSize = 40
    GetWindowTitle = 41
    SetWindowTitle = 42
    GetMaxWindowSize = 43
    GetMaxPhysicalWindowSize = 44
    GetKeyAvailable = 45
    ReadKey = 46
    FlushInputBuffer = 47
    SetBufferContents1 = 48
    SetBufferContents2 = 49
    GetBufferContents = 50
    ScrollBufferContents = 51
    PushRunspace = 52
    PopRunspace = 53
    GetIsRunspacePushed = 54
    GetRunspace = 55
    PromptForChoiceMultipleSelection = 56


@PSType(["System.Management.Automation.CommandTypes"])
class CommandTypes(PSFlagBase):
    """System.Management.Automation.CommandTypes enum flags.

    Defines the types of commands that PowerShell can execute. It is documented
    in PSRP under `[MS-PSRP] 2.2.3.19 CommandType`_.

    Note:
        This is an auto-generated Python class for the
        `System.Management.Automation.CommandTypes`_ .NET class.

    .. _[MS-PSRP] 2.2.3.19 CommandType:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/a038c5c9-a220-4064-aa78-ed9cf5a2893c

    .. _System.Management.Automation.CommandTypes:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.commandtypes
    """

    Alias = 1  #: Aliases create a name that refers to other command types.
    Function = 2  #: Script functions that are defined by a script block.
    Filter = 4  #: Script filters that are defined by a script block.
    Cmdlet = 8  #: A cmdlet.
    ExternalScript = 16  #: A PowerShell script (`*.ps1` file).
    Application = 32  #: Any existing application (can be console or GUI).
    Script = 64  #: A script that is built into the runspace configuration.
    Configuration = 256  #: A configuration.
    All = 383  #: All possible command types.


@PSType(["System.Management.Automation.Host.ControlKeyStates"])
class ControlKeyStates(PSFlagBase):
    """System.Management.Automation.Host.ControlKeyStates enum flags.

    Defines the state of the control key. It is documented in PSRP under
    `[MS-PSRP] 2.2.3.27 ControlKeyStates`_.

    Note:
        This is an auto-generated Python class for the
        `System.Management.Automation.Host.ControlKeyStates`_ .NET class.

    .. _[MS-PSRP] 2.2.3.27 ControlKeyStates:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/bd7241a2-4ba0-4db1-a2b3-77ea1a8a4cbf

    .. _System.Management.Automation.Host.ControlKeyStates:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.controlkeystates
    """

    RightAltPressed = 1  #: The right alt key is pressed.
    LeftAltPressed = 2  #: The left alt key is pressed.
    RightCtrlPressed = 4  #: The right ctrl key is pressed.
    LeftCtrlPressed = 8  #: The left ctrl key is pressed.
    ShiftPressed = 16  #: The shift key is pressed.
    NumLockOn = 32  #: The numlock light is on.
    ScrollLockOn = 64  #: The scrolllock light is on.
    CapsLockOn = 128  #: The capslock light is on.
    EnhancedKey = 256  #: The key is enhanced.


@PSType(["System.Management.Automation.Host.ControlKeyStates"])
class BufferCellType(PSFlagBase):
    """System.Management.Automation.Host.BufferCellType enum flags.

    Defines three types of BufferCells to accommodate for hosts that use up to
    two cells to display a character in some languages such as Chinese and
    Japanese. It is documented in PSRP under
    `[MS-PSRP] 2.2.3.29 BufferCellType`_.

    Note:
        This is an auto-generated Python class for the
        `System.Management.Automation.Host.BufferCellType`_ .NET class.

    .. _[MS-PSRP] 2.2.3.29 BufferCellType:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/99938ede-6d84-422e-b75d-ace93ea85ea2

    .. _System.Management.Automation.Host.BufferCellType:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.buffercelltype
    """

    Complete = 0  #: Character occupies one BufferCell.
    Leading = 1  #: Character occupies two BufferCells and this is the leading one.
    Trailing = 2  #: Preceded by a Leading BufferCell.


@PSType(["System.Management.Automation.CommandOrigin"])
class CommandOrigin(PSEnumBase):
    """System.Management.Automation.CommandOrigin enum.

    Defines the dispatch origin of a command. It is documented in PSRP under
    `[MS-PSRP] 2.2.3.30 CommandOrigin`_.

    Note:
        This is an auto-generated Python class for the
        `System.Management.Automation.CommandOrigin`_ .NET class.

    .. _[MS-PSRP] 2.2.3.30 CommandOrigin:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/6c35a5de-d063-4097-ace5-002a0c5e452d

    .. _System.Management.Automation.CommandOrigin:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.commandorigin
    """

    Runspace = 0  #: The command was submited via a runspace.
    Internal = 1  #: The command was dispatched by the PowerShell engine.


@PSType(["System.Management.Automation.Runspaces.PipelineResultTypes"])
class PipelineResultTypes(PSFlagBase):
    """System.Management.Automation.Runspaces.PipelineResultTypes enum flags.

    Defines the types of streams coming out of a pipeline. It is documented in
    PSRP under `[MS-PSRP] 2.2.3.31 PipelineResultTypes`_. .NET and MS-PSRP have
    separate values but .NET is used as it is the correct source.
    Technically the values are not designed as flags but there are some older
    APIs that combine Output | Error together.

    Note:
        This is an auto-generated Python class for the
        `System.Management.Automation.Runspaces.PipelineResultTypes`_ .NET
        class.

    .. _[MS-PSRP] 2.2.3.31 PipelineResultTypes:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/efdce0ba-531e-4904-9cab-b65c476c649a

    .. _System.Management.Automation.Runspaces.PipelineResultTypes:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.runspaces.pipelineresulttypes
    """

    none = 0  #: Default streaming behaviour.
    Output = 1  #: Output stream.
    Error = 2  #: Error stream.
    Warning = 3  #: Warning stream.
    Verbose = 4  #: Verbose stream.
    Debug = 5  #: Debug stream.
    Information = 6  #: Information stream.
    All = 7  #: All streams.
    Null = 8  #: Redirect to nothing.


@PSType(
    type_names=[
        "System.Management.Automation.Host.Coordinates",
        "System.ValueType",
    ],
    adapted_properties=[
        PSNoteProperty("X", mandatory=True, ps_type=PSInt),
        PSNoteProperty("Y", mandatory=True, ps_type=PSInt),
    ],
)
class Coordinates(PSObject):
    """Coordinates

    Represents an x,y coordinate pair. This is the actual .NET type
    `System.Management.Automation.Host.Coordinates`_. It is documented under
    `[MS-PSRP] 2.2.3.1 Coordinates`_ but the PSRP documentation represents how
    this value is serialized under :class:`HostDefaultData`.

    Args:
        X: X coordinate (0 is the leftmost column).
        Y: Y coordinate (0 is the topmost row).

    .. _[MS-PSRP] 2.2.3.1 Coordinates:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/05db8994-ec5c-485c-9e91-3a398e461d38

    .. _System.Management.Automation.Host.Coordinates:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.coordinates
    """


@PSType(
    type_names=[
        "System.Management.Automation.Host.Size",
        "System.ValueType",
    ],
    adapted_properties=[
        PSNoteProperty("Width", mandatory=True, ps_type=PSInt),
        PSNoteProperty("Height", mandatory=True, ps_type=PSInt),
    ],
)
class Size(PSObject):
    """Size

    Represents a width and height pair. This is the actual .NET type
    `System.Management.Automation.Host.Size`_. It is documented under
    `[MS-PSRP] 2.2.3.2 Size`_ but the PSRP documentation represents how this
    value is serialized under :class:`HostDefaultData`.

    Args:
        Width: The width of an area.
        Height: The height of an area.

    .. _[MS-PSRP] 2.2.3.2 Size:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/98cd950f-cc12-4ab4-955d-c389e3089856

    .. _System.Management.Automation.Host.Size:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.size
    """


@PSType(
    extended_properties=[
        PSAliasProperty("data", "_default_data"),
    ],
    skip_inheritance=True,
)
class HostDefaultData(PSObject):
    """HostInfo default data.

    This defines the default data for a PSHost when creating a RunspacePool or
    Pipeline. This does not represent an actual .NET type but is an internal
    object representation used by PSRP itself. This type represents the
    `hostDefaultData` property documented at `[MS-PSRP] 2.2.3.14 HostInfo`_.

    Args:
        foreground_color (:class:`ConsoleColor`): Color of the character on the
            screen buffer.
        background_color (:class:`ConsoleColor`): Color behind characters on
            the screen buffer.
        cursor_position (:class:`Coordinates`): Cursor position in the screen
            buffer.
        window_position (:class:`Coordinates`): Position of the view window
            relative to the screen buffer.
        cursor_size (:class:`Union[PSInt, int]`): Cursor size as a percentage
            0..100.
        buffer_size (:class:`Size`): Current size of the screen buffer,
            measured in character cells.
        window_size (:class:`Size`): Current view window size, measured in
            character cells.
        max_window_size (:class:`Size`):  Size of the largest window position
            for the current buffer.
        max_physical_window_size (:class:`Size`): Largest window possible
            ignoring the current buffer dimensions.
        window_title (:class:`Union[PSString, str]`) The titlebar text of the
            current view window.

    .. _[MS-PSRP] 2.2.3.14 HostInfo:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/510fd8f3-e3ac-45b4-b622-0ad5508a5ac6
    """

    def __init__(
        self,
        foreground_color: ConsoleColor,
        background_color: ConsoleColor,
        cursor_position: Coordinates,
        window_position: Coordinates,
        cursor_size: int,
        buffer_size: Size,
        window_size: Size,
        max_window_size: Size,
        max_physical_window_size: Size,
        window_title: str,
    ):
        super().__init__()

        self.foreground_color = foreground_color
        self.background_color = background_color
        self.cursor_position = cursor_position
        self.window_position = window_position
        self.cursor_size = cursor_size
        self.buffer_size = buffer_size
        self.window_size = window_size
        self.max_window_size = max_window_size
        self.max_physical_window_size = max_physical_window_size
        self.window_title = window_title

    @property
    def _default_data(self) -> typing.Dict[int, PSObject]:
        def dict_value(value: typing.Union[int, str, PSObject], value_type: str) -> PSObject:
            dict_obj = PSObject()
            add_note_property(dict_obj, "T", value_type, ps_type=PSString)
            add_note_property(dict_obj, "V", value)
            return dict_obj

        def color(value: ConsoleColor) -> PSObject:
            return dict_value(PSInt(value), value.PSObject.type_names[0])

        def coordinates(value: Coordinates) -> PSObject:
            raw = PSObject()
            add_note_property(raw, "x", value.X, ps_type=PSInt)
            add_note_property(raw, "y", value.Y, ps_type=PSInt)
            return dict_value(raw, value.PSObject.type_names[0])

        def size(value: Size) -> PSObject:
            raw = PSObject()
            add_note_property(raw, "width", value.Width, ps_type=PSInt)
            add_note_property(raw, "height", value.Height, ps_type=PSInt)
            return dict_value(raw, value.PSObject.type_names[0])

        return {
            0: color(self.foreground_color),
            1: color(self.background_color),
            2: coordinates(self.cursor_position),
            3: coordinates(self.window_position),
            4: dict_value(self.cursor_size, PSInt.PSObject.type_names[0]),
            5: size(self.buffer_size),
            6: size(self.window_size),
            7: size(self.max_window_size),
            8: size(self.max_physical_window_size),
            9: dict_value(self.window_title, PSString.PSObject.type_names[0]),
        }

    @classmethod
    def FromPSObjectForRemoting(
        cls,
        obj: PSObject,
        **kwargs: typing.Any,
    ) -> "HostDefaultData":
        def coordinates(value: PSObject) -> Coordinates:
            return Coordinates(X=value.x, Y=value.y)

        def size(value: PSObject) -> Size:
            return Size(Width=value.width, Height=value.height)

        return HostDefaultData(
            foreground_color=obj.data[0].V,
            background_color=obj.data[1].V,
            cursor_position=coordinates(obj.data[2].V),
            window_position=coordinates(obj.data[3].V),
            cursor_size=obj.data[4].V,
            buffer_size=size(obj.data[5].V),
            window_size=size(obj.data[6].V),
            max_window_size=size(obj.data[7].V),
            max_physical_window_size=size(obj.data[8].V),
            window_title=obj.data[9].V,
        )


@PSType(
    extended_properties=[
        PSAliasProperty("_isHostNull", "is_host_null", ps_type=PSBool),
        PSAliasProperty("_isHostUINull", "is_host_ui_null", ps_type=PSBool),
        PSAliasProperty("_isHostRawUINull", "is_host_raw_ui_null", ps_type=PSBool),
        PSAliasProperty("_useRunspaceHost", "use_runspace_host", ps_type=PSBool),
        PSAliasProperty("_hostDefaultData", "host_default_data", optional=True, ps_type=HostDefaultData),
    ],
    skip_inheritance=True,
)
class HostInfo(PSObject):
    """HostInfo.

    Defines the PSHost information. Message is defined in
    `[MS-PSRP] 2.2.3.14 HostInfo`_.

    Args:
        is_host_null (:class:`PSBool`): Whether there is a PSHost ``False`` or
            not ``True``.
        is_host_ui_null (:class:`PSBool`): Whether the PSHost implements the `UI`
            implementation methods ``False`` or not ``True``.
        is_host_raw_ui_null (:class:`PSBool`): Whether the PSHost UI implements
            the ``RawUI`` implementation methods ``False`` or not ``True``.
        use_runspace_host (:class:`PSBool`): When creating a pipeline, set this
            to ``True`` to get it to use the associated RunspacePool host.
        host_default_data (:class:`HostDefaultData`): Host default data
            associated with the :class:`psrp.host.PSHostRawUI` implementation.
            Can be ``None`` if not implemented.

    .. _[MS-PSRP] 2.2.3.14 HostInfo:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/510fd8f3-e3ac-45b4-b622-0ad5508a5ac6
    """

    def __init__(
        self,
        is_host_null: bool = True,
        is_host_ui_null: bool = True,
        is_host_raw_ui_null: bool = True,
        use_runspace_host: bool = True,
        host_default_data: typing.Optional[HostDefaultData] = None,
    ):
        super().__init__()

        self.is_host_null = is_host_null
        self.is_host_ui_null = is_host_ui_null
        self.is_host_raw_ui_null = is_host_raw_ui_null
        self.use_runspace_host = use_runspace_host
        self.host_default_data = host_default_data

    @classmethod
    def FromPSObjectForRemoting(
        cls,
        obj: PSObject,
        **kwargs: typing.Any,
    ) -> "HostInfo":
        """Convert the raw HostInfo PSObject back to this easier to use object."""
        host_data = getattr(obj, "_hostDefaultData", None)
        if host_data is not None:
            host_data = HostDefaultData.FromPSObjectForRemoting(host_data)

        return HostInfo(
            is_host_null=obj._isHostNull,
            is_host_ui_null=obj._isHostUINull,
            is_host_raw_ui_null=obj._isHostRawUINull,
            use_runspace_host=obj._useRunspaceHost,
            host_default_data=host_data,
        )


@PSType(
    type_names=[
        "System.Management.Automation.Language.ScriptPosition",
    ],
    adapted_properties=[
        PSNoteProperty("File", ps_type=PSString),
        PSNoteProperty("LineNumber", ps_type=PSInt),
        PSNoteProperty("ColumnNumber", ps_type=PSInt),
        PSNoteProperty("Line", ps_type=PSString),
        PSScriptProperty("Offset", lambda o: 0, ps_type=PSInt),  # Not used in pwsh.
    ],
)
class ScriptPosition(PSObject):
    """ScriptPosition.

    Represents a single point in a script. This script may come from a file or
    interactive input. This is the actual .NET type
    `System.Management.Automation.Language.ScriptPosition`_.

    Args:
        File: The name of the file, or if the script did not come from a file, then null.
        LineNumber: The line number of the position, with the value 1 being the first line.
        ColumnNumber: The column number of the position, with the value 1 being the first column.
        Line: The complete text of the line that this position is included on.

    .. _System.Management.Automation.Language.ScriptPosition:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.language.scriptposition
    """


@PSType(
    type_names=[
        "System.Management.Automation.Language.ScriptExtent",
    ],
    adapted_properties=[
        PSScriptProperty("File", lambda o: o._start.File, ps_type=PSString),
        PSScriptProperty("StartScriptPosition", lambda o: o._start, ps_type=PSString),
        PSScriptProperty("EndScriptPosition", lambda o: o._end, ps_type=PSString),
        PSScriptProperty("StartLineNumber", lambda o: o._start.LineNumber, ps_type=PSInt),
        PSScriptProperty("StartColumnNumber", lambda o: o._start.ColumnNumber, ps_type=PSInt),
        PSScriptProperty("EndLineNumber", lambda o: o._end.LineNumber, ps_type=PSInt),
        PSScriptProperty("EndColumnNumber", lambda o: o._end.ColumnNumber, ps_type=PSInt),
        PSScriptProperty("StartOffset", lambda o: o._start.Offset, ps_type=PSInt),
        PSScriptProperty("EndOffset", lambda o: o._end.Offset, ps_type=PSInt),
        PSAliasProperty("Text", "_text", ps_type=PSString),
    ],
)
class ScriptExtent(PSObject):
    """ScriptExtent.

    A script extend used to customize the display of error location
    information. This is the actual .NET type
    `System.Management.Automation.Language.ScriptExtent`_.

    Args:
        StartPosition: The position beginning the extent.
        EndPosition: The position ending the extent.

    .. _System.Management.Automation.Language.ScriptExtent:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.language.scriptextent
    """

    def __init__(
        self,
        StartPosition: ScriptPosition,
        EndPosition: ScriptPosition,
    ):
        super().__init__()
        self._start = StartPosition
        self._end = EndPosition

    @property
    def _text(self) -> PSString:
        if self.EndColumnNumber < 1:
            val = ""

        elif self.StartLineNumber == self.EndLineNumber:
            val = self._start.Line[max(self.StartColumnNumber - 1, 0) : self.EndColumnNumber]

        else:
            start = self._start.Line[self.StartColumnNumber :]
            end = self._end.Line[self.EndColumnNumber :]
            val = f"{start}...{end}"

        return PSString(val)


def _script_extent_from_ps_object(
    obj: PSObject,
) -> ScriptExtent:
    """Used by ErrorRecord and InformationalRecord to deserialize the invocation info details."""
    file = obj.ScriptExtent_File
    start_line = obj.ScriptExtent_StartLineNumber
    end_line = obj.ScriptExtent_EndLineNumber
    start_column = obj.ScriptExtent_StartColumnNumber
    end_column = obj.ScriptExtent_EndColumnNumber

    return ScriptExtent(
        StartPosition=ScriptPosition(file, start_line, start_column, ""),
        EndPosition=ScriptPosition(file, end_line, end_column, ""),
    )


def _script_extent_to_ps_object(
    script_extent: ScriptExtent,
    obj: PSObject,
) -> None:
    """Used by InvocationInfo to serialize the script extent details."""
    add_note_property(obj, "ScriptExtent_File", script_extent.File)
    add_note_property(obj, "ScriptExtent_StartLineNumber", script_extent.StartLineNumber)
    add_note_property(obj, "ScriptExtent_StartColumnNumber", script_extent.StartColumnNumber)
    add_note_property(obj, "ScriptExtent_EndLineNumber", script_extent.EndLineNumber)
    add_note_property(obj, "ScriptExtent_EndColumnNumber", script_extent.EndColumnNumber)


@PSType(
    type_names=[
        "System.Management.Automation.InvocationInfo",
    ],
    adapted_properties=[
        PSNoteProperty("BoundParameters", ps_type=PSDict),
        PSNoteProperty("CommandOrigin", ps_type=CommandOrigin),
        PSNoteProperty("DisplayScriptPosition", ps_type=ScriptExtent),
        PSNoteProperty("ExpectingInput", ps_type=PSBool),
        PSNoteProperty("HistoryId", ps_type=PSInt64),
        PSNoteProperty("InvocationName", ps_type=PSString),
        PSNoteProperty("Line", ps_type=PSString),
        PSNoteProperty("MyCommand"),  # CommandInfo,
        PSNoteProperty("OffsetInLine", ps_type=PSInt),
        PSNoteProperty("PipelineLength", ps_type=PSInt),
        PSNoteProperty("PipelinePosition", ps_type=PSInt),
        PSNoteProperty("PositionMessage", ps_type=PSString),
        PSNoteProperty("PSCommandPath", ps_type=PSString),
        PSNoteProperty("PSScriptRoot", ps_type=PSString),
        PSNoteProperty("ScriptLineNumber", ps_type=PSInt),
        PSNoteProperty("ScriptName", ps_type=PSString),
        PSNoteProperty("UnboundArguments", ps_type=PSList),
    ],
)
class InvocationInfo(PSObject):
    """InvocationInfo.

    Describes how and where this command was invoked. This is the actual .NET
    type `System.Management.Automation.InvocationInfo`_.

    Args:
        BoundParameters: Dictionary of parameters that were bound for this
            script or command.
        CommandOrigin: Command was being invoked inside the runspace or if it
            was an external request.
        DisplayScriptPosition: The position for the invocation or error.
        ExpectingInput: The command is expecting input.
        HistoryId: History that represents the command, if unavailable this
            will be ``-1``.
        InvocationName: Command name used to invoke this script. If invoked
            through an alias then this would be the alias name.
        Line: The text of the line that contained this cmdlet invocation.
        MyCommand: Basic information about the command.
        OffsetInLine: Command's character offset in that line. If the command
            was executed directly through the host interfaces, this will be -1.
        PipelineLength: How many elements are in the containing pipeline.
        PipelinePosition: Which element this command was in the containing
            pipeline.
        PositionMessage: Formatted message indicating where the cmdlet appeared
            in the line.
        PSCommandPath: The full path to the command from where it was being
            invoked.
        PSScriptRoot: The directory from where the command was being invoked.
        ScriptLineNumber: The line number in the executing script that contains
            this cmdlet.
        ScriptName: The name of the script containing the cmdlet.
        UnboundArguments: The list of arguments that were not bound to any
            parameter.

    .. _System.Management.Automation.InvocationInfo:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.invocationinfo
    """


def _invocation_info_from_ps_object(
    obj: PSObject,
) -> InvocationInfo:
    """Used by ErrorRecord and InformationalRecord to deserialize the invocation info details."""
    line = getattr(obj, "InvocationInfo_Line", None) or ""
    ps_command_path = ""
    ps_script_root = ""

    if getattr(obj, "SerializeExtent") or False:
        display_script_position = _script_extent_from_ps_object(obj)

    else:
        script_name = obj.InvocationInfo_ScriptName or ""
        script_line_number = obj.InvocationInfo_ScriptLineNumber
        offset_in_line = obj.InvocationInfo_OffsetInLine
        start_position = ScriptPosition(script_name, script_line_number, offset_in_line, line)

        end_position = start_position
        if line:
            end_position = ScriptPosition(script_name, script_line_number, len(line) + 1, line)

        display_script_position = ScriptExtent(start_position, end_position)

        ps_command_path = display_script_position.File
        if posixpath.sep in ps_command_path:  # pragma: no cover
            ps_script_root = posixpath.dirname(ps_command_path)
        else:  # pragma: no cover
            ps_script_root = ntpath.dirname(ps_command_path)

    my_command = None
    command_type = getattr(obj, "CommandInfo_CommandType", None)
    if command_type is not None:
        my_command = RemoteCommandInfo(
            CommandType=CommandTypes(command_type),
            Name=obj.CommandInfo_Name,
            Definition=obj.CommandInfo_Definition,
            Visibility=SessionStateEntryVisibility(obj.CommandInfo_Visibility),
        )

    return InvocationInfo(
        BoundParameters=getattr(obj, "InvocationInfo_BoundParameters", None) or PSDict(),
        CommandOrigin=CommandOrigin(obj.InvocationInfo_CommandOrigin),
        DisplayScriptPosition=display_script_position,
        ExpectingInput=obj.InvocationInfo_ExpectingInput,
        HistoryId=obj.InvocationInfo_HistoryId,
        InvocationName=obj.InvocationInfo_InvocationName,
        Line=line,
        MyCommand=my_command,
        OffsetInLine=obj.InvocationInfo_OffsetInLine,
        PipelineLength=obj.InvocationInfo_PipelineLength,
        PipelinePosition=obj.InvocationInfo_PipelinePosition,
        PSCommandPath=ps_command_path,
        PSScriptRoot=ps_script_root,
        ScriptLineNumber=obj.InvocationInfo_ScriptLineNumber,
        ScriptName=obj.InvocationInfo_ScriptName,
        UnboundArguments=getattr(obj, "InvocationInfo_UnboundArguments", None) or PSList(),
    )


def _invocation_info_to_ps_object(
    invocation_info: InvocationInfo,
    obj: PSObject,
) -> None:
    """Used by ErrorRecord and InformationalRecord to serialize the invocation info details."""
    add_note_property(obj, "InvocationInfo_BoundParameters", invocation_info.BoundParameters)
    add_note_property(obj, "InvocationInfo_CommandOrigin", invocation_info.CommandOrigin)
    add_note_property(obj, "InvocationInfo_ExpectingInput", invocation_info.ExpectingInput)
    add_note_property(obj, "InvocationInfo_InvocationName", invocation_info.InvocationName)
    add_note_property(obj, "InvocationInfo_Line", invocation_info.Line)
    add_note_property(obj, "InvocationInfo_OffsetInLine", invocation_info.OffsetInLine)
    add_note_property(obj, "InvocationInfo_HistoryId", invocation_info.HistoryId)
    add_note_property(obj, "InvocationInfo_PipelineIterationInfo", [])  # List of PSInt32
    add_note_property(obj, "InvocationInfo_PipelineLength", invocation_info.PipelineLength)
    add_note_property(obj, "InvocationInfo_PipelinePosition", invocation_info.PipelinePosition)
    add_note_property(obj, "InvocationInfo_PSScriptRoot", invocation_info.PSScriptRoot)
    add_note_property(obj, "InvocationInfo_PSCommandPath", invocation_info.PSCommandPath)
    add_note_property(obj, "InvocationInfo_PositionMessage", invocation_info.PositionMessage)
    add_note_property(obj, "InvocationInfo_ScriptLineNumber", invocation_info.ScriptLineNumber)
    add_note_property(obj, "InvocationInfo_ScriptName", invocation_info.ScriptName)
    add_note_property(obj, "InvocationInfo_UnboundArguments", invocation_info.UnboundArguments)

    if invocation_info.DisplayScriptPosition:
        _script_extent_to_ps_object(invocation_info.DisplayScriptPosition, obj)
        add_note_property(obj, "SerializeExtent", True)

    else:
        add_note_property(obj, "SerializeExtent", False)

    if invocation_info.MyCommand:
        # This should be a CommandInfo type but we are being pretty lax with the property checks.
        my_command = invocation_info.MyCommand
        add_note_property(obj, "CommandInfo_CommandType", getattr(my_command, "CommandType", CommandTypes.Application))
        add_note_property(obj, "CommandInfo_Definition", getattr(my_command, "Definition", ""))
        add_note_property(obj, "CommandInfo_Name", getattr(my_command, "Name", ""))
        add_note_property(
            obj, "CommandInfo_Visibility", getattr(my_command, "Visibility", SessionStateEntryVisibility.Public)
        )


@PSType(
    type_names=[
        "System.Management.Automation.ErrorCategoryInfo",
    ],
    adapted_properties=[
        # Technically a string in .NET but it's easier for the end user to be an enum.
        PSNoteProperty("Category", value=ErrorCategory.NotSpecified, ps_type=ErrorCategory),
        PSNoteProperty("Activity", ps_type=PSString),
        PSNoteProperty("Reason", ps_type=PSString),
        PSNoteProperty("TargetName", ps_type=PSString),
        PSNoteProperty("TargetType", ps_type=PSString),
    ],
)
class ErrorCategoryInfo(PSObject):
    """ErrorCategoryInfo.

    Contains auxiliary information about an ErrorRecord. This is the actual
    .NET type `System.Management.Automation.ErrorCategoryInfo`_.

    Args:
        Category: The error category.
        Activity: Description of the operation which encountered the error.
        Reason: Description of the error.
        TargetName: Description of the target object.
        TargetType: Description of the type of the target object.

    .. _System.Management.Automation.ErrorCategoryInfo:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.errorcategoryinfo
    """

    def __str__(self) -> str:
        return (
            f'{self.Category.name!s} ({self.TargetName or ""}:{self.TargetType or ""}) '
            f'[{self.Activity or ""}], {self.Reason or ""}'
        )


@PSType(
    type_names=[
        "System.Management.Automation.ErrorDetails",
    ],
    adapted_properties=[
        PSNoteProperty("Message", ps_type=PSString),
        PSNoteProperty("RecommendedAction", ps_type=PSString),
    ],
)
class ErrorDetails(PSObject):
    """ErrorDetails.

    ErrorDetaisl represents additional details about an :class:`ErrorRecord`,
    starting with a replacement Message. Clients can use ErrorDetails when they
    want to display a more specific message than the one contained in a
    particular Exception, without having to create a new Exception or define a
    new Exception class. This is the actual
    .NET type `System.Management.Automation.ErrorDetails`_.

    Args:
        Message: Message with replaces Message in Exception.
        RecommendedAction: Describes the recommended action in the event this
            error occurs. This can be empty if not applicable.

    .. _System.Management.Automation.ErrorDetails:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.errordetails
    """


@PSType(
    type_names=[
        "System.Management.Automation.ErrorRecord",
    ],
    adapted_properties=[
        PSNoteProperty("Exception", mandatory=True),
        PSNoteProperty("CategoryInfo", mandatory=True, ps_type=ErrorCategoryInfo),
        PSNoteProperty("TargetObject"),
        PSNoteProperty("FullyQualifiedErrorId", ps_type=PSString),
        PSNoteProperty("InvocationInfo", ps_type=InvocationInfo),
        PSNoteProperty("ErrorDetails", ps_type=ErrorDetails),
        PSNoteProperty("PipelineIterationInfo", ps_type=PSList),
        PSNoteProperty("ScriptStackTrace", ps_type=PSString),
    ],
)
class ErrorRecord(PSObject):
    """ErrorRecord.

    The data type that represents information about an error. It is documented
    in PSRP under `[MS-PSRP] 2.2.3.15 ErrorRecord`_. The invocation specific
    properties are documented under `[MS-PSRP] 2.2.3.15.1 InvocationInfo`_.
    This is the actual .NET type `System.Management.Automation.ErrorRecord`_

    Args:
        Exception: An exception describing the error.
        TargetObject: The object against which the error occurred.
        FullyQualifiedErrorId: String which uniquely identifies this error
            condition.
        CategoryInfo: Information regarding the ErrorCategory associated with
            this error.
        ErrorDetails: Additional information about the error.
        InvocationInfo: Identifies the cmdlet, script, or other command which
            caused the error.
        PipelineIterationInfo: The status of the pipeline when this record was
            created. Each entry represents the number of inputs the command[i]
            in the statement has processed when the record was created.
        ScriptStackTrace: The object against which the error occurred.

    .. _[MS-PSRP] 2.2.3.15 ErrorRecord:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/0fe855a7-d13c-44e2-aa88-291e2054ae3a

    .. _[MS-PSRP] 2.2.3.15.1 InvocationInfo:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/000363b7-e2f9-4a34-94f5-d540a15aee7b

    .. _System.Management.Automation.ErrorRecord:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.errorrecord
    """

    def __init__(
        self,
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.serialize_extended_info = False

    def __str__(self) -> str:
        if self.ErrorDetails and self.ErrorDetails.Message:
            return self.ErrorDetails.Message

        else:
            return self.Exception.Message

    @classmethod
    def FromPSObjectForRemoting(
        cls,
        obj: PSObject,
        **kwargs: typing.Any,
    ) -> "ErrorRecord":
        category_info = ErrorCategoryInfo(
            Category=ErrorCategory(obj.ErrorCategory_Category),
            Activity=obj.ErrorCategory_Activity,
            Reason=obj.ErrorCategory_Reason,
            TargetName=obj.ErrorCategory_TargetName,
            TargetType=obj.ErrorCategory_TargetType,
        )
        category_info.PSObject.to_string = obj.ErrorCategory_Message

        error_details = None
        error_details_message = getattr(obj, "ErrorDetails_Message", None)
        error_details_action = getattr(obj, "ErrorDetails_RecommendedAction", None)
        if error_details_message or error_details_action:
            error_details = ErrorDetails(
                Message=error_details_message,
                RecommendedAction=error_details_action,
            )

        # Technically PowerShell wraps the exception in a RemoteException class which contains
        # 'SerializedRemoteException' and 'SerializedRemoteInvocationInfo'. To make things simple we just use the
        # serialized exception as the actual Exception value and add the invocation info to that.
        add_note_property(obj.Exception, "SerializedRemoteInvocationInfo", obj.InvocationInfo)

        invocation_info = None
        pipeline_iteration_info = None
        if obj.SerializeExtendedInfo:
            pipeline_iteration_info = obj.PipelineIterationInfo
            invocation_info = _invocation_info_from_ps_object(obj)

        record = cls(
            Exception=obj.Exception,
            TargetObject=obj.TargetObject,
            FullyQualifiedErrorId=obj.FullyQualifiedErrorId,
            InvocationInfo=invocation_info,
            CategoryInfo=category_info,
            ErrorDetails=error_details,
            PipelineIterationInfo=pipeline_iteration_info,
            ScriptStackTrace=getattr(obj, "ErrorDetails_ScriptStackTrace", None),
        )
        record.serialize_extended_info = obj.SerializeExtendedInfo
        return record

    @classmethod
    def ToPSObjectForRemoting(
        cls,
        instance: "ErrorRecord",
        **kwargs: typing.Any,
    ) -> PSObject:
        obj = PSObject()
        add_note_property(obj, "Exception", instance.Exception)
        add_note_property(obj, "TargetObject", instance.TargetObject)
        add_note_property(obj, "FullyQualifiedErrorId", instance.FullyQualifiedErrorId)
        add_note_property(obj, "InvocationInfo", instance.InvocationInfo)
        add_note_property(obj, "ErrorCategory_Category", instance.CategoryInfo.Category.value)
        add_note_property(obj, "ErrorCategory_Activity", instance.CategoryInfo.Activity)
        add_note_property(obj, "ErrorCategory_Reason", instance.CategoryInfo.Reason)
        add_note_property(obj, "ErrorCategory_TargetName", instance.CategoryInfo.TargetName)
        add_note_property(obj, "ErrorCategory_TargetType", instance.CategoryInfo.TargetType)
        add_note_property(obj, "ErrorCategory_Message", str(instance.CategoryInfo))

        if instance.ErrorDetails:
            add_note_property(obj, "ErrorDetails_Message", instance.ErrorDetails.Message)
            add_note_property(obj, "ErrorDetails_RecommendedAction", instance.ErrorDetails.RecommendedAction)

        if instance.ScriptStackTrace:
            add_note_property(obj, "ErrorDetails_ScriptStackTrace", instance.ScriptStackTrace)

        if instance.serialize_extended_info and instance.InvocationInfo:
            add_note_property(obj, "SerializeExtendedInfo", True)
            _invocation_info_to_ps_object(instance.InvocationInfo, obj)
            add_note_property(obj, "PipelineIterationInfo", instance.PipelineIterationInfo)

        else:
            add_note_property(obj, "SerializeExtendedInfo", False)

        return obj


@PSType(
    type_names=[
        "System.Management.Automation.InformationalRecord",
    ],
    adapted_properties=[
        PSNoteProperty("Message", ps_type=PSString),
        PSNoteProperty("InvocationInfo", ps_type=InvocationInfo),
        PSNoteProperty("PipelineIterationInfo", ps_type=PSList),
    ],
)
class InformationalRecord(PSObject):
    """PowerShell InformationalRecord.

    InformationalRecord (that is Debug, Warning, or Verbose) is a structure
    that contains additional information that a pipeline can output in addition
    to the regular data output. It is documented in PSRP under
    `[MS-PSRP] 2.2.3.16 InformationalRecord`_. The invocation specific
    properties are documented under `[MS-PSRP] 2.2.3.15.1 InvocationInfo`_.
    This also represents the
    `System.Management.Automation.InformationalRecord`_ .NET type.

    Args:
        Message: The message writen by the command that created this record.
        InvocationInfo: The invocation info of the command that created this
            record.
        PipelineIterationInfo: The status of the pipeline when this record was
            created.

    .. _[MS-PSRP] 2.2.3.16 InformationalRecord:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/97cad2dc-c34a-4db6-bfa1-cbf196853937

    .. _[MS-PSRP] 2.2.3.15.1 InvocationInfo:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/000363b7-e2f9-4a34-94f5-d540a15aee7b

    .. _System.Management.Automation.InformationalRecord:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.informationalrecord
    """

    def __init__(
        self,
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.serialize_extended_info = False

    @classmethod
    def FromPSObjectForRemoting(
        cls,
        obj: PSObject,
        **kwargs: typing.Any,
    ) -> "InformationalRecord":
        invocation_info = None
        pipeline_iteration_info = None
        if obj.InformationalRecord_SerializeInvocationInfo:
            pipeline_iteration_info = obj.InformationalRecord_PipelineIterationInfo
            invocation_info = _invocation_info_from_ps_object(obj)

        record = cls(
            Message=obj.InformationalRecord_Message,
            InvocationInfo=invocation_info,
            PipelineIterationInfo=pipeline_iteration_info,
        )
        record.serialize_extended_info = obj.InformationalRecord_SerializeInvocationInfo

        return record

    @classmethod
    def ToPSObjectForRemoting(
        cls,
        instance: "ErrorRecord",
        **kwargs: typing.Any,
    ) -> PSObject:
        obj = PSObject()
        add_note_property(obj, "InformationalRecord_Message", instance.Message)

        if instance.serialize_extended_info and instance.InvocationInfo:
            add_note_property(obj, "InformationalRecord_SerializeInvocationInfo", True)
            _invocation_info_to_ps_object(instance.InvocationInfo, obj)
            add_note_property(obj, "InformationalRecord_PipelineIterationInfo", instance.PipelineIterationInfo)

        else:
            add_note_property(obj, "InformationalRecord_SerializeInvocationInfo", False)

        return obj


@PSType(["System.Management.Automation.DebugRecord"])
class DebugRecord(InformationalRecord):
    """DebugRecord.

    A debug record in the PSInformationalBuffers. This represents the
    `System.Management.Automation.DebugRecord`_ .NET type.

    .. _System.Management.Automation.DebugRecord:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.debugrecord?view=powershellsdk-7.0.0
    """


@PSType(["System.Management.Automation.VerboseRecord"])
class VerboseRecord(InformationalRecord):
    """VerboseRecord.

    A verbose record in the PSInformationalBuffers. This represents the
    `System.Management.Automation.VerboseRecord`_ .NET type.

    .. _System.Management.Automation.DebugRecord:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.verboserecord?view=powershellsdk-7.0.0
    """


@PSType(["System.Management.Automation.WarningRecord"])
class WarningRecord(InformationalRecord):
    """WarningRecord.

    A warning record in the PSInformationalBuffers. This represents the
    `System.Management.Automation.WarningRecord`_ .NET type.

    .. _System.Management.Automation.WarningRecord:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.warningrecord?view=powershellsdk-7.0.0
    """


@PSType(
    [
        "System.Management.Automation.InformationRecord",
    ],
    extended_properties=[
        PSNoteProperty("MessageData"),
        PSNoteProperty("Source", ps_type=PSString),
        PSNoteProperty("TimeGenerated", ps_type=PSDateTime),
        PSNoteProperty("Tags", ps_type=PSList),
        PSNoteProperty("User", ps_type=PSString),
        PSNoteProperty("Computer", ps_type=PSString),
        PSNoteProperty("ProcessId", ps_type=PSUInt),
        PSNoteProperty("NativeThreadId", ps_type=PSUInt),
        PSNoteProperty("ManagedThreadId", ps_type=PSUInt),
    ],
)
class InformationRecord(PSObject):
    """InformationRecord.

    Defines a data structure used to represent informational context destined
    for the host or user. This represents the
    `System.Management.Automation.InformationRecord`_ .NET type.

    .. _System.Management.Automation.InformationRecord:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.informationrecord?view=powershellsdk-7.0.0
    """


@PSType(type_names=["System.Management.Automation.PSPrimitiveDictionary"])
class PSPrimitiveDictionary(PSDict):
    """Primitive Dictionary.

    A primitive dictionary represents a dictionary which contains only objects
    that are primitive types. While Python does not place any limitations on
    the types this object can contain, trying to serialize a
    PSPrimitiveDictionary with complex types to PowerShell will fail. The types
    that are allowed can be found at `[MS-PSRP] 2.2.3.18 Primitive Dictionary`_.

    .. _[MS-PSRP] 2.2.3.18 Primitive Dictionary:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/7779aa42-6927-4225-b31c-2771fd869546
    """


@PSType(
    type_names=[
        "Selected.Microsoft.PowerShell.Commands.GenericMeasureInfo",
    ],
    extended_properties=[
        PSNoteProperty("Count", mandatory=True, ps_type=PSInt),
    ],
)
class CommandMetadataCount(PSCustomObject):
    """CommandMetadataCount.

    Special data type used by the command metadata messages. It is documented
    in PSRP under `[MS-PSRP] 2.2.3.21 CommandMetadataCount`_.

    Args:
        Count: The count.

    .. _[MS-PSRP] 2.2.3.21 CommandMetadataCount:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/4647da0c-18e6-496c-9d9e-c669d40dc1db
    """


@PSType(
    type_names=[
        "System.Management.Automation.PSCredential",
    ],
    adapted_properties=[
        PSNoteProperty("UserName", mandatory=True, ps_type=PSString),
        PSNoteProperty("Password", mandatory=True, ps_type=PSSecureString),
    ],
)
class PSCredential(PSObject):
    """PSCredential.

    Represents a username and a password. It is documented in PSRP under
    `[MS-PSRP] 2.2.3.25 PSCredential`_. It also represents the
    `System.Management.Automation.PSCredential`_ .NET type.

    Note:
        To be able to serialize this object, a session key is exchanged between
        the host and the peer. If the peer does not support the session key
        exchange then this cannot be serialized.

    Args:
        UserName: The username for the credential.
        Password: The password for the credential.

    .. _[MS-PSRP] 2.2.3.25 PSCredential:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/a7c91a93-ee59-4af0-8a67-a9361af9870e

    .. _System.Management.Automation.PSCredential:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.pscredential
    """


@PSType(
    extended_properties=[
        PSNoteProperty("virtualKeyCode", ps_type=PSInt),
        PSNoteProperty("character", ps_type=PSChar),
        PSNoteProperty("controlKeyState", ps_type=PSInt),  # ControlKeyStates as integer.
        PSNoteProperty("keyDown", ps_type=PSBool),
    ],
    skip_inheritance=True,
)
class PSRPKeyInfo(PSObject):
    """KeyInfo.

    Represents information of a keystroke. It is documented in PSRP under
    `[MS-PSRP] 2.2.3.26 KeyInfo`_. This is not the same as the actual
    `System.Management.Automation.Host.KeyInfo`_ .NET type but rather a custom
    format used by PSRP.

    Args:
        virtualKeyCode: A virtual key code that identifies the given key in a device-independent manner.
        character: Character corresponding to the pressed keys.
        controlKeyState: State of the control keys.
        keyDown: True if the event was generated when a key was pressed.

    .. _[MS-PSRP] 2.2.3.26 KeyInfo:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/481442e2-5304-4679-b16d-6e53c351339d

    .. _System.Management.Automation.Host.KeyInfo:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.keyinfo
    """


@PSType(
    adapted_properties=[
        PSNoteProperty("character", ps_type=PSChar),
        PSNoteProperty("foregroundColor", ps_type=ConsoleColor),
        PSNoteProperty("backgroundColor", ps_type=ConsoleColor),
        PSNoteProperty("bufferCellType", ps_type=PSInt),  # BufferCellType as integer.
    ],
    skip_inheritance=True,
)
class PSRPBufferCell(PSObject):
    """BufferCell.

    Represents the contents of a cell of a Host's screen buffer. It is
    documented in PSRP under `[MS-PSRP] 2.2.3.28 BufferCell`_. This is not the
    same as the actual `System.Management.Automation.Host.BufferCell`_ .NET
    type but rather a custom format used by PSRP.

    Args:
        character: Character visible in the cell.
        foregroundColor: Foreground color.
        backgroundColor: Background color.
        bufferCellType: Type of the buffer cell.

    .. _[MS-PSRP] 2.2.3.28 BufferCell:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/d6270c27-8855-46b6-834c-5a5d188bfe70

    .. _System.Management.Automation.Host.BufferCell:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.buffercell
    """


@PSType(
    extended_properties=[
        PSNoteProperty("helpMessage", ps_type=PSString),
        PSNoteProperty("label", ps_type=PSString),
    ],
    skip_inheritance=True,
)
class PSRPChoiceDescription(PSObject):
    """ChoiceDescription.

    Represents a description of a field for use by
    :class:`psrp.host.PSHostUI.prompt_for_choice`.. It isn't documented in
    MS-PSRP but the properties are based on what has been seen across the wire.
    This is not the same as the actual
    `System.Management.Automation.Host.ChoiceDescription`_ .NET type but rather
    a custom format used by PSRP.

    Args:
        helpMessage: Help message for the choice.
        label: Short human-presentable to describe and identify the choice.

    .. _System.Management.Automation.Host.ChoiceDescription:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.choicedescription
    """


@PSType(
    extended_properties=[
        PSNoteProperty("name", ps_type=PSString),
        PSNoteProperty("label", ps_type=PSString),
        PSNoteProperty("parameterTypeName", ps_type=PSString),
        PSNoteProperty("parameterTypeFullName", ps_type=PSString),
        PSNoteProperty("parameterAssemblyFullName", ps_type=PSString),
        PSNoteProperty("helpMessage", ps_type=PSString),
        PSNoteProperty("isMandatory", ps_type=PSBool),
        PSNoteProperty("metadata", ps_type=PSList),
        PSNoteProperty("modifiedByRemotingProtocol", ps_type=PSBool),
        PSNoteProperty("isFromRemoteHost", ps_type=PSBool),
    ],
    skip_inheritance=True,
)
class PSRPFieldDescription(PSObject):
    """FieldDescription.

    Represents a description of a field for use by
    :class:`psrp.host.PSHostUI.prompt`. It isn't documented in MS-PSRP but the
    properties are based on what has been seen across the w    PSObject = PSObjectMeta(

    )ire. This is not the
    same as the actual `System.Management.Automation.Host.FieldDescription`_
    .NET type but rather a custom format used by PSRP.

    Args:
        name: The name of the field.
        label: A short human-presentable message to describe and identify the
            field.
        parameterTypeName: Short string name of the parameter's type.
        parameterTypeFullName: Full string name of the parameter's type.
        parameterAssemblyFullName: Full name of the assembly containing the
            type.
        helpMessage: The help message for this field.
        isMandatory: Whether a value must be supplied for this field.
        metadata: Extra metadata for the field.
        modifiedByRemotingProtocol: Whether the field was modified by the
            remoting protocol.
        isFromRemoteHost:  Whether the field is from a remote host.

    .. _System.Management.Automation.Host.FieldDescription:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.fielddescription
    """


@PSType(
    type_names=[
        "System.Exception",
    ],
    adapted_properties=[
        PSNoteProperty("Message", mandatory=True, ps_type=PSString),
        PSNoteProperty("Data", ps_type=PSDict),
        PSNoteProperty("HelpLink", ps_type=PSString),
        PSNoteProperty("HResult", ps_type=PSInt),
        PSNoteProperty("InnerException"),
        PSNoteProperty("Source", ps_type=PSString),
        PSNoteProperty("StackTrace", ps_type=PSString),
        PSNoteProperty("TargetSite", ps_type=PSString),
    ],
)
class NETException(PSObject):
    """.NET Exception.

    Represents a .NET `System.Exception`_ type. It isn't documented in
    MS-PSRP but is used when creating an ErrorRecord or just as a base of
    another exception type.

    Args:
        Message: Message that describes the current exception.
        Data: User defined information about the exception.
        HelpLink: A link to the help file associated with this exception.
        HResult: A coded numerical value that is assigned to a specific exception.
        InnerException: Exception instance that caused the current exception.
        Source: Name of the application or the object that causes the error.
        StackTrace: String representation of the immediate frames on the call stack.
        TargetSite: Method that throws the current exception.

    .. _System.Exception:
        https://docs.microsoft.com/en-us/dotnet/api/system.exception?view=net-5.0
    """
