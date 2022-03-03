# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

"""PSRP/.NET Host Types.

The PSRP/.NET host type and metadata definitions. Contains information used
for host methods used in PSRP.
"""

import typing

from psrpcore.types._base import PSNoteProperty, PSObject, PSType, add_note_property
from psrpcore.types._collection import PSList
from psrpcore.types._complex import ConsoleColor
from psrpcore.types._enum import PSEnumBase, PSFlagBase
from psrpcore.types._primitive import PSBool, PSChar, PSInt, PSString


@PSType(["System.Management.Automation.Remoting.RemoteHostMethodId"])
class HostMethodIdentifier(PSEnumBase):
    """Host Method Identifier enum.

    This is an enum class for the
    System.Management.Automation.Remoting.RemoteHostMethodId .NET class. It is
    documented in PSRP under `[MS-PSRP] 2.2.3.17 Host Method Identifier`_.

    The values are used in :class:`psrpcore.types.RunspacePoolHostCall` and
    :class:`psrpcore.types.PipelineHostCall` to identify what method should be
    invoked.

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

    def is_void(self) -> bool:
        """Whether the method is a void method and doesn't return data."""
        return self in [
            HostMethodIdentifier.SetShouldExit,
            HostMethodIdentifier.EnterNestedPrompt,
            HostMethodIdentifier.ExitNestedPrompt,
            HostMethodIdentifier.NotifyBeginApplication,
            HostMethodIdentifier.NotifyEndApplication,
            HostMethodIdentifier.PushRunspace,
            HostMethodIdentifier.PopRunspace,
            HostMethodIdentifier.Write1,
            HostMethodIdentifier.Write2,
            HostMethodIdentifier.WriteLine1,
            HostMethodIdentifier.WriteLine2,
            HostMethodIdentifier.WriteLine3,
            HostMethodIdentifier.WriteErrorLine,
            HostMethodIdentifier.WriteDebugLine,
            HostMethodIdentifier.WriteProgress,
            HostMethodIdentifier.WriteVerboseLine,
            HostMethodIdentifier.WriteWarningLine,
            HostMethodIdentifier.SetForegroundColor,
            HostMethodIdentifier.SetBackgroundColor,
            HostMethodIdentifier.SetCursorPosition,
            HostMethodIdentifier.SetWindowPosition,
            HostMethodIdentifier.SetCursorSize,
            HostMethodIdentifier.SetBufferSize,
            HostMethodIdentifier.SetWindowSize,
            HostMethodIdentifier.SetWindowTitle,
            HostMethodIdentifier.FlushInputBuffer,
            HostMethodIdentifier.SetBufferContents1,
            HostMethodIdentifier.SetBufferContents2,
            HostMethodIdentifier.ScrollBufferContents,
        ]


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

    none = 0  #: No control key state.
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


@PSType(["System.Management.Automation.Host.ReadKeyOptions"])
class ReadKeyOptions(PSFlagBase):
    """System.Management.Automation.Host.ReadKeyOptions enum flags.

    Governs the behavior of :class:`HostMethodIdentifier.ReadKey`.

    Note:
        This is an auto-generated Python class for the
        `System.Management.Automation.Host.ReadKeyOptions`_ .NET class.

    .. _System.Management.Automation.Host.ReadKeyOptions:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.readkeyoptions
    """

    AllowCtrlC = 1  #: Allow Ctrl-C to be processed as a keystroke, as opposed to causing a break event.
    NoEcho = 2  #: Do not display the character for the key in the window when pressed.
    IncludeKeyDown = 4  #: Include key down events. One of IncludeKeyDown and IncludeKeyUp or both must be specified.
    IncludeKeyUp = 8  #: Include key up events. One of IncludeKeyDown and IncludeKeyUp or both must be specified.


@PSType(
    type_names=[
        "System.Management.Automation.Host.BufferCell",
        "System.ValueType",
    ],
    adapted_properties=[
        PSNoteProperty("Character", ps_type=PSChar),
        PSNoteProperty("ForegroundColor", ps_type=ConsoleColor),
        PSNoteProperty("BackgroundColor", ps_type=ConsoleColor),
        PSNoteProperty("BufferCellType", ps_type=BufferCellType),
    ],
)
class BufferCell(PSObject):
    """BufferCell.

    Represents the contents of a cell of a host's screen buffer. It is
    documented in PSRP under `[MS-PSRP] 2.2.3.28 BufferCell`_. but the PSRP
    documentation represents how this value is serialized under
    host method invocations not the .NET type.

    Note:
        This is an auto-generated Python class for the
        `System.Management.Automation.Host.BufferCell`_ .NET class.

    Args:
        Character: Character visible in the cell.
        ForegroundColor: Foreground color.
        BackgroundColor: Background color.
        BufferCellType: Type of the buffer cell.

    .. _[MS-PSRP] 2.2.3.28 BufferCell:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/d6270c27-8855-46b6-834c-5a5d188bfe70

    .. _System.Management.Automation.Host.BufferCell:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.buffercell
    """

    @classmethod
    def FromPSObjectForRemoting(
        cls,
        obj: PSObject,
        **kwargs: typing.Any,
    ) -> "BufferCell":
        if isinstance(obj, BufferCell):
            return obj

        return BufferCell(
            Character=obj.character,
            ForegroundColor=ConsoleColor(obj.foregroundColor),
            BackgroundColor=ConsoleColor(obj.backgroundColor),
            BufferCellType=BufferCellType(obj.bufferCellType),
        )

    @classmethod
    def ToPSObjectForRemoting(
        cls,
        instance: "BufferCell",
        for_host: bool = False,
        **kwargs: typing.Any,
    ) -> PSObject:
        if not for_host:
            return instance

        obj = PSObject()
        obj.PSObject.type_names = []
        add_note_property(obj, "character", instance.Character, ps_type=PSChar)
        add_note_property(obj, "foregroundColor", instance.ForegroundColor.value, ps_type=PSInt)
        add_note_property(obj, "backgroundColor", instance.BackgroundColor.value, ps_type=PSInt)
        add_note_property(obj, "bufferCellType", instance.BufferCellType.value, ps_type=PSInt)

        return obj


@PSType(
    type_names=["System.Management.Automation.Host.ChoiceDescription"],
    adapted_properties=[
        PSNoteProperty("Label", mandatory=True, ps_type=PSString),
        PSNoteProperty("HelpMessage", ps_type=PSString),
    ],
)
class ChoiceDescription(PSObject):
    """ChoiceDescription.

    Provides a description of a choice for use by
    :class:`HostMethodIdentifier.PromptForChoice`.

    Note:
        This is an auto-generated Python class for the
        `System.Management.Automation.Host.ChoiceDescription`_ .NET class.

    Args:
        Label: Human friendly message to describe the choice.
        HelpMessage: Help details of the choice.

    .. _System.Management.Automation.Host.ChoiceDescription:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.choicedescription
    """

    @classmethod
    def FromPSObjectForRemoting(
        cls,
        obj: PSObject,
        **kwargs: typing.Any,
    ) -> "ChoiceDescription":
        if isinstance(obj, ChoiceDescription):
            return obj

        return ChoiceDescription(Label=obj.label, HelpMessage=obj.helpMessage)

    @classmethod
    def ToPSObjectForRemoting(
        cls,
        instance: "ChoiceDescription",
        for_host: bool = False,
        **kwargs: typing.Any,
    ) -> PSObject:
        if not for_host:
            return instance

        obj = PSObject()
        obj.PSObject.type_names = []
        add_note_property(obj, "label", instance.Label, ps_type=PSString)
        add_note_property(obj, "helpMessage", instance.HelpMessage, ps_type=PSString)

        return obj


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

    Represents an x,y coordinate pair. It is documented under
    `[MS-PSRP] 2.2.3.1 Coordinates`_ but the PSRP documentation represents how
    this value is serialized under :class:`HostDefaultData` not the .NET type.

    Note:
        This is an auto-generated Python class for the
        `System.Management.Automation.Host.Coordinates`_ .NET class.

    Args:
        X: X coordinate (0 is the leftmost column).
        Y: Y coordinate (0 is the topmost row).

    .. _[MS-PSRP] 2.2.3.1 Coordinates:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/05db8994-ec5c-485c-9e91-3a398e461d38

    .. _System.Management.Automation.Host.Coordinates:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.coordinates
    """

    @classmethod
    def FromPSObjectForRemoting(
        cls,
        obj: PSObject,
        **kwargs: typing.Any,
    ) -> "Coordinates":
        if isinstance(obj, Coordinates):
            return obj

        return Coordinates(X=obj.x, Y=obj.y)

    @classmethod
    def ToPSObjectForRemoting(
        cls,
        instance: "Coordinates",
        for_host: bool = False,
        **kwargs: typing.Any,
    ) -> PSObject:
        if not for_host:
            return instance

        obj = PSObject()
        obj.PSObject.type_names = []
        add_note_property(obj, "x", instance.X, ps_type=PSInt)
        add_note_property(obj, "y", instance.Y, ps_type=PSInt)

        return obj


@PSType(
    type_names=["System.Management.Automation.Host.FieldDescription"],
    adapted_properties=[
        PSNoteProperty("Name", mandatory=True, ps_type=PSString),
        PSNoteProperty("ParameterTypeName", ps_type=PSString),
        PSNoteProperty("ParameterTypeFullName", ps_type=PSString),
        PSNoteProperty("ParameterAssemblyFullName", ps_type=PSString),
        PSNoteProperty("Label", value="", ps_type=PSString),
        PSNoteProperty("HelpMessage", value="", ps_type=PSString),
        PSNoteProperty("IsMandatory", value=True, ps_type=PSBool),
        PSNoteProperty("DefaultValue", value=None),
        PSNoteProperty("Attributes", ps_type=PSList),
    ],
)
class FieldDescription(PSObject):
    """FieldDescription.

    Provides a description of a field for use by
    :class:`HostMethodIdentifier.Prompt`.

    Note:
        This is an auto-generated Python class for the
        `System.Management.Automation.Host.FieldDescription`_ .NET class.

    Args:
        Name: The name of the field.
        ParameterTypeName: Short name of the field value type.
        ParameterTypeFullName: Full name of the field value type.
        ParameterAssemblyFullName: .NET assembly name of the field value type.
        Label: Human friendly message to describe the field.
        HelpMessage: Help details of the field.
        IsMandatory: The value must be supplied for this field.
        DefaultValue: The default value, if any, for the field.
        Attributes: List of attributes that apply to the field.

    .. _System.Management.Automation.Host.FieldDescription:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.fielddescription
    """

    @classmethod
    def FromPSObjectForRemoting(
        cls,
        obj: PSObject,
        **kwargs: typing.Any,
    ) -> "FieldDescription":
        if isinstance(obj, FieldDescription):
            return obj

        return FieldDescription(
            Name=obj.name,
            ParameterTypeName=obj.parameterTypeName,
            ParameterTypeFullName=obj.parameterTypeFullName,
            ParameterAssemblyFullName=obj.parameterAssemblyFullName,
            Label=obj.label,
            HelpMessage=obj.helpMessage,
            IsMandatory=obj.isMandatory,
            Attributes=obj.metadata,
        )

    @classmethod
    def ToPSObjectForRemoting(
        cls,
        instance: "FieldDescription",
        for_host: bool = False,
        **kwargs: typing.Any,
    ) -> PSObject:
        if not for_host:
            return instance

        obj = PSObject()
        obj.PSObject.type_names = []
        add_note_property(obj, "name", instance.Name, ps_type=PSString)
        add_note_property(obj, "label", instance.Label, ps_type=PSString)
        add_note_property(obj, "parameterTypeName", instance.ParameterTypeName, ps_type=PSString)
        add_note_property(obj, "parameterTypeFullName", instance.ParameterTypeFullName, ps_type=PSString)
        add_note_property(obj, "parameterAssemblyFullName", instance.ParameterAssemblyFullName, ps_type=PSString)
        add_note_property(obj, "helpMessage", instance.HelpMessage, ps_type=PSString)
        add_note_property(obj, "isMandatory", instance.IsMandatory, ps_type=PSBool)
        add_note_property(obj, "metadata", [])
        add_note_property(obj, "modifiedByRemotingProtocol", False, ps_type=PSBool)
        add_note_property(obj, "isFromRemoteHost", False, ps_type=PSBool)

        return obj


@PSType(
    type_names=["System.Management.Automation.Host.KeyInfo"],
    adapted_properties=[
        PSNoteProperty("VirtualKeyCode", ps_type=PSInt),
        PSNoteProperty("Character", ps_type=PSChar),
        PSNoteProperty("ControlKeyState", ps_type=ControlKeyStates),
        PSNoteProperty("KeyDown", ps_type=PSBool),
    ],
)
class KeyInfo(PSObject):
    """KeyInfo.

    Represents information of a keystroke. It is documented in PSRP under
    `[MS-PSRP] 2.2.3.26 KeyInfo`_.

    Note:
        This is an auto-generated Python class for the
        `System.Management.Automation.Host.KeyInfo`_ .NET class.

    Args:
        VirtualKeyCode: A virtual key code that identifies the given key in a
            device-independent manner.
        Character: Character corresponding to the pressed keys.
        ControlKeyState: State of the control keys.
        KeyDown: True if the event was generated when a key was pressed.

    .. _[MS-PSRP] 2.2.3.26 KeyInfo:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/481442e2-5304-4679-b16d-6e53c351339d

    .. _System.Management.Automation.Host.KeyInfo:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.keyinfo
    """

    @classmethod
    def FromPSObjectForRemoting(
        cls,
        obj: PSObject,
        **kwargs: typing.Any,
    ) -> "KeyInfo":
        if isinstance(obj, KeyInfo):
            return obj

        return KeyInfo(
            VirtualKeyCode=obj.virtualKeyCode,
            Character=obj.character,
            ControlKeyState=ControlKeyStates(obj.controlKeyState),
            KeyDown=obj.keyDown,
        )

    @classmethod
    def ToPSObjectForRemoting(
        cls,
        instance: "KeyInfo",
        for_host: bool = False,
        **kwargs: typing.Any,
    ) -> PSObject:
        if not for_host:
            return instance

        obj = PSObject()
        obj.PSObject.type_names = []
        add_note_property(obj, "virtualKeyCode", instance.VirtualKeyCode, ps_type=PSInt)
        add_note_property(obj, "character", instance.Character, ps_type=PSChar)
        add_note_property(obj, "controlKeyState", instance.ControlKeyState.value, ps_type=PSInt)
        add_note_property(obj, "keyDown", instance.KeyDown, ps_type=PSBool)

        return obj


@PSType(
    type_names=[
        "System.Management.Automation.Host.Rectangle",
        "System.ValueType",
    ],
    adapted_properties=[
        PSNoteProperty("Left", mandatory=True, ps_type=PSInt),
        PSNoteProperty("Top", mandatory=True, ps_type=PSInt),
        PSNoteProperty("Right", mandatory=True, ps_type=PSInt),
        PSNoteProperty("Bottom", mandatory=True, ps_type=PSInt),
    ],
)
class Rectangle(PSObject):
    """Rectangle.

    Represents a rectangular region of the screen.

    Note:
        This is an auto-generated Python class for the
        `System.Management.Automation.Host.Rectangle`_ .NET class.

    Args:
        Left: Gets and sets the left side of the rectangle.
        Top: Gets and sets the top of the rectangle.
        Right: Gets and sets the right side of the rectangle.
        Bottom: Gets and sets the bottom of the rectanngle.

    .. _System.Management.Automation.Host.Rectangle:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.rectangle
    """

    @classmethod
    def FromPSObjectForRemoting(
        cls,
        obj: PSObject,
        **kwargs: typing.Any,
    ) -> "Rectangle":
        if isinstance(obj, Rectangle):
            return obj

        return Rectangle(Left=obj.left, Top=obj.top, Right=obj.right, Bottom=obj.bottom)

    @classmethod
    def ToPSObjectForRemoting(
        cls,
        instance: "Rectangle",
        for_host: bool = False,
        **kwargs: typing.Any,
    ) -> PSObject:
        if not for_host:
            return instance

        obj = PSObject()
        obj.PSObject.type_names = []
        add_note_property(obj, "left", instance.Left, ps_type=PSInt)
        add_note_property(obj, "top", instance.Top, ps_type=PSInt)
        add_note_property(obj, "right", instance.Right, ps_type=PSInt)
        add_note_property(obj, "bottom", instance.Bottom, ps_type=PSInt)

        return obj


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

    Represents a width and height pair. It is documented under
    `[MS-PSRP] 2.2.3.2 Size`_ but the PSRP documentation represents how this
    value is serialized under :class:`HostDefaultData` not the .NET type.


    Note:
        This is an auto-generated Python class for the
        `System.Management.Automation.Host.Size`_ .NET class.

    Args:
        Width: The width of an area.
        Height: The height of an area.

    .. _[MS-PSRP] 2.2.3.2 Size:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/98cd950f-cc12-4ab4-955d-c389e3089856

    .. _System.Management.Automation.Host.Size:
        https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.size
    """

    @classmethod
    def FromPSObjectForRemoting(
        cls,
        obj: PSObject,
        **kwargs: typing.Any,
    ) -> "Size":
        if isinstance(obj, Size):
            return obj

        return Size(Width=obj.width, Height=obj.height)

    @classmethod
    def ToPSObjectForRemoting(
        cls,
        instance: "Size",
        for_host: bool = False,
        **kwargs: typing.Any,
    ) -> PSObject:
        if not for_host:
            return instance

        obj = PSObject()
        obj.PSObject.type_names = []
        add_note_property(obj, "width", instance.Width, ps_type=PSInt)
        add_note_property(obj, "height", instance.Height, ps_type=PSInt)

        return obj


@PSType(
    extended_properties=[
        PSNoteProperty("ForegroundColor", mandatory=True, ps_type=ConsoleColor),
        PSNoteProperty("BackgroundColor", mandatory=True, ps_type=ConsoleColor),
        PSNoteProperty("CursorPosition", mandatory=True, ps_type=Coordinates),
        PSNoteProperty("WindowPosition", mandatory=True, ps_type=Coordinates),
        PSNoteProperty("CursorSize", mandatory=True, ps_type=PSInt),
        PSNoteProperty("BufferSize", mandatory=True, ps_type=Size),
        PSNoteProperty("WindowSize", mandatory=True, ps_type=Size),
        PSNoteProperty("MaxWindowSize", mandatory=True, ps_type=Size),
        PSNoteProperty("MaxPhysicalWindowSize", mandatory=True, ps_type=Size),
        PSNoteProperty("WindowTitle", mandatory=True, ps_type=PSString),
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
        ForegroundColor: Color of the character on the screen buffer.
        BackgroundColor: Color behind characters on the screen buffer.
        CursorPosition: Cursor position in the screen buffer.
        WindowPosition: Position of the view window relative to the screen
            buffer.
        CursorSize: Cursor size as a percentage 0..100.
        BufferSize: Current size of the screen buffer, measured in character
            cells.
        WindowSize: Current view window size, measured in character cells.
        MaxWindowSize:  Size of the largest window position for the current
            buffer.
        MaxPhysicalWindowSize: Largest window possible ignoring the current
            buffer dimensions.
        WindowTitle: The titlebar text of the current view window.

    .. _[MS-PSRP] 2.2.3.14 HostInfo:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/510fd8f3-e3ac-45b4-b622-0ad5508a5ac6
    """

    @classmethod
    def FromPSObjectForRemoting(
        cls,
        obj: PSObject,
        **kwargs: typing.Any,
    ) -> "HostDefaultData":
        return HostDefaultData(
            ForegroundColor=ConsoleColor(obj.data[0].V),
            BackgroundColor=ConsoleColor(obj.data[1].V),
            CursorPosition=Coordinates.FromPSObjectForRemoting(obj.data[2].V),
            WindowPosition=Coordinates.FromPSObjectForRemoting(obj.data[3].V),
            CursorSize=obj.data[4].V,
            BufferSize=Size.FromPSObjectForRemoting(obj.data[5].V),
            WindowSize=Size.FromPSObjectForRemoting(obj.data[6].V),
            MaxWindowSize=Size.FromPSObjectForRemoting(obj.data[7].V),
            MaxPhysicalWindowSize=Size.FromPSObjectForRemoting(obj.data[8].V),
            WindowTitle=obj.data[9].V,
        )

    @classmethod
    def ToPSObjectForRemoting(
        cls,
        instance: "HostDefaultData",
        **kwargs: typing.Any,
    ) -> PSObject:
        obj = PSObject()

        def dict_value(value: typing.Union[int, str, PSObject], value_type: str) -> PSObject:
            dict_obj = PSObject()
            add_note_property(dict_obj, "T", value_type, ps_type=PSString)
            add_note_property(dict_obj, "V", value)
            return dict_obj

        data = {}
        for idx, prop in enumerate(instance.PSObject.extended_properties):
            value = prop.get_value(instance)
            if isinstance(value, ConsoleColor):
                value = dict_value(PSInt(value), value.PSObject.type_names[0])

            elif isinstance(value, Coordinates):
                raw = Coordinates.ToPSObjectForRemoting(value, for_host=True)
                value = dict_value(raw, value.PSObject.type_names[0])

            elif isinstance(value, Size):
                raw = Size.ToPSObjectForRemoting(value, for_host=True)
                value = dict_value(raw, value.PSObject.type_names[0])

            else:
                value = dict_value(value, value.PSObject.type_names[0])

            data[idx] = value

        add_note_property(obj, "data", data)

        return obj


@PSType(
    extended_properties=[
        PSNoteProperty("IsHostNull", value=True, ps_type=PSBool),
        PSNoteProperty("IsHostUINull", value=True, ps_type=PSBool),
        PSNoteProperty("IsHostRawUINull", value=True, ps_type=PSBool),
        PSNoteProperty("UseRunspaceHost", value=True, ps_type=PSBool),
        PSNoteProperty("HostDefaultData", ps_type=HostDefaultData),
    ],
    skip_inheritance=True,
)
class HostInfo(PSObject):
    """HostInfo.

    Defines the PSHost information. Message is defined in
    `[MS-PSRP] 2.2.3.14 HostInfo`_.

    Args:
        IsHostNull: Whether there is a PSHost ``False`` or not ``True``.
        IsHostUINull: Whether the PSHost implements the `UI` implementation
            methods ``False`` or not ``True``.
        IsHostRawUINull: Whether the PSHost UI implements the ``RawUI``
            implementation methods ``False`` or not ``True``.
        UseRunspaceHost: When creating a pipeline, set this to ``True`` to get
            it to use the associated RunspacePool host.
        HostDefaultData: Host default data associated with the PSHost
            implementation. Can be ``None`` if not implemented.

    .. _[MS-PSRP] 2.2.3.14 HostInfo:
        https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/510fd8f3-e3ac-45b4-b622-0ad5508a5ac6
    """

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
            IsHostNull=obj._isHostNull,
            IsHostUINull=obj._isHostUINull,
            IsHostRawUINull=obj._isHostRawUINull,
            UseRunspaceHost=obj._useRunspaceHost,
            HostDefaultData=host_data,
        )

    @classmethod
    def ToPSObjectForRemoting(
        cls,
        instance: "HostInfo",
        **kwargs: typing.Any,
    ) -> PSObject:
        obj = PSObject()
        add_note_property(obj, "_isHostNull", instance.IsHostNull)
        add_note_property(obj, "_isHostUINull", instance.IsHostUINull)
        add_note_property(obj, "_isHostRawUINull", instance.IsHostRawUINull)
        add_note_property(obj, "_useRunspaceHost", instance.UseRunspaceHost)

        if instance.HostDefaultData:
            add_note_property(obj, "_hostDefaultData", instance.HostDefaultData)

        return obj
