# -*- coding: utf-8 -*-
# Copyright: (c) 2021, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import functools
import typing
import uuid

from psrpcore._client import (
    ClientGetCommandMetadata,
    ClientPowerShell,
    ClientRunspacePool,
)
from psrpcore._server import ServerPipeline, ServerRunspacePool
from psrpcore.types import (
    BufferCell,
    BufferCellType,
    ChoiceDescription,
    ConsoleColor,
    ControlKeyStates,
    Coordinates,
    FieldDescription,
    HostMethodIdentifier,
    KeyInfo,
    ProgressRecordMsg,
    ProgressRecordType,
    PSChar,
    PSCredential,
    PSCredentialTypes,
    PSCredentialUIOptions,
    PSListBase,
    PSObject,
    PSSecureString,
    PSType,
    PSVersion,
    ReadKeyOptions,
    Rectangle,
    Size,
    add_note_property,
)


@PSType(["System.Int32[]", "System.Array"])
class _ArrayCount(PSListBase):
    """Used to encapsuilate an int32 array for multidimensional arrays."""


def _create_multi_dimensional_array(
    values: typing.List[typing.List[typing.Any]],
    pack_func: typing.Callable[[typing.Any], PSObject],
) -> PSObject:
    """Create a host method multidimensional array object."""
    flattened: typing.List[typing.Any] = []
    for val in values:
        flattened.extend(val)

    # The code only handles 2 dimensional arrays for now.
    mal = _ArrayCount([len(values), len(values[0])])
    mae = [pack_func(v) for v in flattened]

    obj = PSObject()
    obj.PSObject.type_names = []
    add_note_property(obj, "mae", mae)
    add_note_property(obj, "mal", mal)

    return obj


class ClientHostResponder:
    """Client Host Responser.

    Helper class that can be used to response to runspace and pipeline host
    calls. Each method is named after the corresponding host method identifer
    and document the required values that need to be set to respond to the hsot
    call for that request.

    Args:
        connection: The client Runspace Pool or Pipeline to response on.
    """

    def __init__(
        self,
        connection: typing.Union[ClientRunspacePool, ClientPowerShell, ClientGetCommandMetadata],
    ):
        self._connection = connection

    def get_name(
        self,
        ci: int,
        name: str,
    ) -> None:
        """GetName Response.

        Responds to :class:`psrpcore.types.HostMethodIdentifier.GetName` with a
        human friendly host name identifier.

        Note:
            For pwsh this value is typically static and set by the server on
            creation. It is rare for this to be requested by the server.

        Args:
            ci: The call id the response is for.
            name: The host name to respond.
        """
        self._connection.host_response(ci, name)

    def get_version(
        self,
        ci: int,
        version: typing.Union[str, PSVersion],
    ) -> None:
        """GetVersion Response.

        Responds to :class:`psrpcore.types.HostMethodIdentifier.GetVersion`
        with the version of the host.

        Note:
            For pwsh this value is typically static and set by the server on
            creation. It is rare for this to be requested by the server.

        Args:
            ci: The call id the response is for.
            version: The version of the host.
        """
        if not isinstance(version, PSVersion):
            version = PSVersion(version)

        self._connection.host_response(ci, version)

    def get_instance_id(
        self,
        ci: int,
        instance_id: uuid.UUID,
    ) -> None:
        """GetInstanceId Response.

        Responds to :class:`psrpcore.types.HostMethodIdentifier.GetInstanceId`
        with a unique identifier of the host.

        Note:
            For pwsh this value is typically static and set by the server on
            creation. It is rare for this to be requested by the server.

        Args:
            ci: The call id the response is for.
            instance_id: The host identifier.
        """
        self._connection.host_response(ci, instance_id)

    def get_current_culture(
        self,
        ci: int,
        culture: str,
    ) -> None:
        """GetCurrentCulture Response.

        Responds to
        :class:`psrpcore.types.HostMethodIdentifier.GetCurrentCulture` with the
        host's culture, like ``en-US``.

        Note:
            For pwsh this value is typically static and set by the server on
            creation. It is rare for this to be requested by the server.

        Args:
            ci: The call id the response is for.
            culture: The host culture.
        """
        self._connection.host_response(ci, culture)

    def get_current_ui_culture(
        self,
        ci: int,
        culture: str,
    ) -> None:
        """GetCurrentUICulture Response.

        Responds to
        :class:`psrpcore.types.HostMethodIdentifier.GetCurrentUICulture` with
        the host's UI culture, like ``en-US``. The UI culture is used for
        operations like loading resource files.

        Note:
            For pwsh this value is typically static and set by the server on
            creation. It is rare for this to be requested by the server.

        Args:
            ci: The call id the response is for.
            culture: The host UI culture.
        """
        self._connection.host_response(ci, culture)

    def get_is_runspace_pushed(
        self,
        ci: int,
        is_pushed: bool,
    ) -> None:
        """GetIsRunspacePushed Response.

        Responds to
        :class:`psrpcore.types.HostMethodIdentifier.GetIsRunspacePushed` with
        whether the runspace is pushed or not.

        Note:
            For pwsh this value is typically static and set by the server on
            creation. It is rare for this to be requested by the server.

        Args:
            ci: The call id the response is for.
            is_pushed: The runspace is pushed or not.
        """
        self._connection.host_response(ci, is_pushed)

    def read_line(
        self,
        ci: int,
        line: str,
    ) -> None:
        """ReadLine Response.

        Responds to
        :class:`psrpcore.types.HostMethodIdentifier.ReadLine` with the line
        that was read.

        Args:
            ci: The call id the response is for.
            line: The line that was read.
        """
        self._connection.host_response(ci, line)

    def read_line_as_secure_string(
        self,
        ci: int,
        line: PSSecureString,
    ) -> None:
        """ReadLineAsSecureString Response.

        Responds to
        :class:`psrpcore.types.HostMethodIdentifier.ReadLineAsSecureString`
        with the line as a secure string that was read.

        Args:
            ci: The call id the response is for.
            line: The line that was read as a secure string.
        """
        self._connection.host_response(ci, line)

    def prompt(
        self,
        ci: int,
        choices: typing.Dict[str, typing.Any],
    ) -> None:
        """Prompt Response.

        Responds to
        :class:`psrpcore.types.HostMethodIdentifier.Prompt` with the values for
        field that was entered.

        Args:
            ci: The call id the response is for.
            choices: The response with the key being the name of the field and
                the value is the value entered for that field.
        """
        self._connection.host_response(ci, choices)

    def prompt_for_credential(
        self,
        ci: int,
        credential: PSCredential,
    ) -> None:
        """PromptForCredential Response.

        Responds to
        :class:`psrpcore.types.HostMethodIdentifier.PromptForCredential1` or
        :class:`psrpcore.types.HostMethodIdentifier.PromptForCredential2` with
        the credential that was entered.

        Args:
            ci: The call id the response is for.
            credential: The credential that was entered.
        """
        self._connection.host_response(ci, credential)

    def prompt_for_choice(self, ci: int, choice: int) -> None:
        """PromptForChoice Response.

        Responds to
        :class:`psrpcore.types.HostMethodIdentifier.PromptForChoice` with the
        choice that was slected.

        Args:
            ci: The call id the response is for.
            choice: The choice that was selected. This is a 0 based index of
                selected choice from the host call.
        """
        self._connection.host_response(ci, choice)

    def prompt_for_multiple_choice(
        self,
        ci: int,
        choices: typing.Union[int, typing.List[int]],
    ) -> None:
        """PromptForChoiceMultipleSelection Response.

        Responds to
        :class:`psrpcore.types.HostMethodIdentifier.PromptForChoiceMultipleSelection`
        with the choices that were selected.

        Args:
            ci: The call id the response is for.
            choices: The choices that were selected. Each choice is a 0 based
                index of the selected choice from the host call.
        """
        self._connection.host_response(ci, choices if isinstance(choices, list) else [choices])

    def get_foreground_color(
        self,
        ci: int,
        color: ConsoleColor,
    ) -> None:
        """GetForegroundColor Response.

        Responds to
        :class:`psrpcore.types.HostMethodIdentifier.GetForegroundColor` with
        the foreground (text) color of the host.

        Note:
            For pwsh this value is set when the server creates the host based
            on the host default data. It is rare for this to be requested by
            the server.

        Args:
            ci: The call id the response is for.
            color: The foreground color of the host.
        """
        self._connection.host_response(ci, color.value)

    def get_background_color(
        self,
        ci: int,
        color: ConsoleColor,
    ) -> None:
        """GetBackgroundColor Response.

        Responds to
        :class:`psrpcore.types.HostMethodIdentifier.GetBackgroundColor` with
        the background color of the host.

        Note:
            For pwsh this value is set when the server creates the host based
            on the host default data. It is rare for this to be requested by
            the server.

        Args:
            ci: The call id the response is for.
            color: The background color of the host.
        """
        self._connection.host_response(ci, color.value)

    def get_cursor_position(
        self,
        ci: int,
        x: int,
        y: int,
    ) -> None:
        """GetCursorPosition Response.

        Responds to
        :class:`psrpcore.types.HostMethodIdentifier.GetCursorPosition` the
        coordinates of the cursor in the host.

        Note:
            For pwsh this value is set when the server creates the host based
            on the host default data. It is rare for this to be requested by
            the server.

        Args:
            ci: The call id the response is for.
            x: The X (horizontal) coordinate of the cursor.
            y: The Y (vertical) coordinate of the cursor.
        """
        self._connection.host_response(ci, Coordinates.ToPSObjectForRemoting(Coordinates(x, y), for_host=True))

    def get_window_position(
        self,
        ci: int,
        x: int,
        y: int,
    ) -> None:
        """GetWindowPosition Response.

        Responds to
        :class:`psrpcore.types.HostMethodIdentifier.GetWindowPosition` the
        coordinates (from the top left point) of the host window.

        Note:
            For pwsh this value is set when the server creates the host based
            on the host default data. It is rare for this to be requested by
            the server.

        Args:
            ci: The call id the response is for.
            x: The X (horizontal) coordinate of the host window.
            y: The Y (vertical) coordinate of the host window.
        """
        self._connection.host_response(ci, Coordinates.ToPSObjectForRemoting(Coordinates(x, y), for_host=True))

    def get_cursor_size(
        self,
        ci: int,
        size: int,
    ) -> None:
        """GetCursorSize Response.

        Responds to
        :class:`psrpcore.types.HostMethodIdentifier.GetCursorSize` with the
        size (as a percentage) of the cursor.

        Note:
            For pwsh this value is set when the server creates the host based
            on the host default data. It is rare for this to be requested by
            the server.

        Args:
            ci: The call id the response is for.
            size: The size, as a percentage, of the host cursor.
        """
        self._connection.host_response(ci, size)

    def get_buffer_size(
        self,
        ci: int,
        width: int,
        height: int,
    ) -> None:
        """GetBufferSize Response.

        Responds to
        :class:`psrpcore.types.HostMethodIdentifier.GetBufferSize` with the
        size of the buffer of the host. The size is measured in character cells
        which can contain a 16-bit Char.

        Note:
            For pwsh this value is set when the server creates the host based
            on the host default data. It is rare for this to be requested by
            the server.

        Args:
            ci: The call id the response is for.
            width: The number of cells the fit the width of the buffer.
            height: The number of cells that fit the height of the buffer.
        """
        self._connection.host_response(ci, Size.ToPSObjectForRemoting(Size(width, height), for_host=True))

    def get_window_size(
        self,
        ci: int,
        width: int,
        height: int,
    ) -> None:
        """GetWindowSize Response.

        Responds to
        :class:`psrpcore.types.HostMethodIdentifier.GetWindowSize` with the
        size of the window of the host. The size is measured in character cells
        which can contain a 16-bit Char.

        Note:
            For pwsh this value is set when the server creates the host based
            on the host default data. It is rare for this to be requested by
            the server.

        Args:
            ci: The call id the response is for.
            width: The number of cells the fit the width of the window.
            height: The number of cells that fit the height of the window.
        """
        self._connection.host_response(ci, Size.ToPSObjectForRemoting(Size(width, height), for_host=True))

    def get_window_title(
        self,
        ci: int,
        title: str,
    ) -> None:
        """GetWindowTitle Response.

        Responds to
        :class:`psrpcore.types.HostMethodIdentifier.GetWindowTitle` with the
        title of the host window.

        Note:
            For pwsh this value is set when the server creates the host based
            on the host default data. It is rare for this to be requested by
            the server.

        Args:
            ci: The call id the response is for.
            title: The title of the window.
        """
        self._connection.host_response(ci, title)

    def get_max_window_size(
        self,
        ci: int,
        width: int,
        height: int,
    ) -> None:
        """GetMaxWindowSize Response.

        Responds to
        :class:`psrpcore.types.HostMethodIdentifier.GetMaxWindowSize` with the
        maximum size of the window of the host. The size is measured in
        character cells which can contain a 16-bit Char.

        Note:
            For pwsh this value is set when the server creates the host based
            on the host default data. It is rare for this to be requested by
            the server.

        Args:
            ci: The call id the response is for.
            width: The number of cells the fit the max width of the window.
            height: The number of cells that fit the max height of the window.
        """
        self._connection.host_response(ci, Size.ToPSObjectForRemoting(Size(width, height), for_host=True))

    def get_max_physical_window_size(
        self,
        ci: int,
        width: int,
        height: int,
    ) -> None:
        """GetMaxPhysicalWindowSize Response.

        Responds to
        :class:`psrpcore.types.HostMethodIdentifier.GetMaxPhysicalWindowSize`
        with the maximum physical size of the window of the host. The size is
        measured in character cells which can contain a 16-bit Char.

        Note:
            For pwsh this value is set when the server creates the host based
            on the host default data. It is rare for this to be requested by
            the server.

        Args:
            ci: The call id the response is for.
            width: The number of cells the fit the max physical width of the
                window.
            height: The number of cells that fit the max physical height of
                the window.
        """
        self._connection.host_response(ci, Size.ToPSObjectForRemoting(Size(width, height), for_host=True))

    def get_key_available(
        self,
        ci: int,
        waiting: bool,
    ) -> None:
        """GetKeyAvailable Response.

        Responds to
        :class:`psrpcore.types.HostMethodIdentifier.GetKeyAvailable` with
        whether the host is waiting on input.

        Args:
            ci: The call id the response is for.
            waiting: Host is waiting on input.
        """
        self._connection.host_response(ci, waiting)

    def read_key(
        self,
        ci: int,
        character: typing.Union[int, str, PSChar],
        key_down: bool,
        control_key_state: ControlKeyStates = ControlKeyStates.none,
        key_code: int = 0,
    ) -> None:
        """ReadKey Response.

        Responds to
        :class:`psrpcore.types.HostMethodIdentifier.ReadKey` with key that was
        inputted onto the host.

        Args:
            ci: The call id the response is for.
            character: The character (UTF-16 16-bit char) that was inputted.
            key_down: Generated by a key press ``True`` or release ``False``.
            control_key_state: State of the control keys.
            key_code: Device-independent key code value.
        """
        char = character
        if not isinstance(char, PSChar):
            char = PSChar(character)

        self._connection.host_response(
            ci, KeyInfo.ToPSObjectForRemoting(KeyInfo(key_code, char, control_key_state, key_down), for_host=True)
        )

    def get_buffer_contents(
        self,
        ci: int,
        cells: typing.List[typing.List[BufferCell]],
    ) -> None:
        """GetBufferContents Response.

        Responds to
        :class:`psrpcore.types.HostMethodIdentifier.GetBufferContents` with
        contents of the buffer that was requested.

        The ``cells`` value is a list of a list of
        :class:`psrpcore.types.BufferCell` where the first list dimension
        represents each row and the 2nd dimension is each column of that row.

        Note:
            PowerShell does not implement this call for security reasons.
            Unless you trust the target host you should not return this
            information, or sanitise the data as needed.

        Args:
            ci: The call id the response is for.
            cells: A list of a list of cells.
        """
        wrap_cell = functools.partial(BufferCell.ToPSObjectForRemoting, for_host=True)
        return self._connection.host_response(ci, _create_multi_dimensional_array(cells, wrap_cell))


class ServerHostRequestor:
    """Server Host Requestor.

    Helper class that can be used to create Runspace Pool or Pipeline host
    call requests. Each method exposes the required/optional arguments for each
    call and extra handling that may be required for that request. The
    :class:`ClientHostResponder` is used on the client side to respond to the
    host calls that require a response.

    Args:
        connection: The server Runspace Pool or Pipeline to send requests to.
    """

    def __init__(
        self,
        connection: typing.Union[ServerRunspacePool, ServerPipeline],
    ):
        self._connection = connection

    def get_name(
        self,
    ) -> int:
        """GetName Request.

        Sends the :class:`psrpcore.types.HostMethodIdentifier.GetName` host
        call that requests the human friendly host name identifier.
        human friendly host name identifier.

        This corresponds to the `PSHost.Name Property`_.

        Note:
            The server should wait for the host response before continuing the
            pipeline that created this request.

        Returns:
            int: The call id for the request.

        .. _PSHost.Name Property:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshost.name
        """
        return self._connection.host_call(HostMethodIdentifier.GetName)

    def get_version(
        self,
    ) -> int:
        """GetVersion Request.

        Sends the :class:`psrpcore.types.HostMethodIdentifier.GetVersion` host
        call that requests the version of the hosting application.

        This corresponds to the `PSHost.Version Property`_.

        Note:
            The server should wait for the host response before continuing the
            pipeline that created this request.

        Returns:
            int: The call id for the request.

        .. _PSHost.Version Property:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshost.version
        """
        return self._connection.host_call(HostMethodIdentifier.GetVersion)

    def get_instance_id(
        self,
    ) -> int:
        """GetInstanceId Request.

        Sends the :class:`psrpcore.types.HostMethodIdentifier.GetInstanceId`
        host call that requests the identifier of the hosting application.

        This corresponds to the `PSHost.InstanceId Property`_.

        Note:
            The server should wait for the host response before continuing the
            pipeline that created this request.

        Returns:
            int: The call id for the request.

        .. _PSHost.InstanceId Property:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshost.instanceid
        """
        return self._connection.host_call(HostMethodIdentifier.GetInstanceId)

    def get_current_culture(
        self,
    ) -> int:
        """GetCurrentCulture Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.GetCurrentCulture` host
        call that requests the current culture of the host.

        This corresponds to the `PSHost.CurrentCulture Property`_.

        Note:
            The server should wait for the host response before continuing the
            pipeline that created this request.

        Returns:
            int: The call id for the request.

        .. _PSHost.CurrentCulture Property:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshost.currentculture
        """
        return self._connection.host_call(HostMethodIdentifier.GetCurrentCulture)

    def get_current_ui_culture(
        self,
    ) -> int:
        """GetCurrentUICulture Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.GetCurrentUICulture` host
        call that requests the current UI culture of the host.

        This corresponds to the `PSHost.CurrentUICulture Property`_.

        Note:
            The server should wait for the host response before continuing the
            pipeline that created this request.

        Returns:
            int: The call id for the request.

        .. _PSHost.CurrentUICulture Property:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshost.currentuiculture
        """
        return self._connection.host_call(HostMethodIdentifier.GetCurrentUICulture)

    def set_should_exit(
        self,
        exit_code: int,
    ) -> None:
        """SetShouldExit Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.SetShouldExit` host
        call that requests the current engine runspace to shut down and
        terminate the host's root runspace.

        This corresponds to the `PSHost.SetShouldExit Method`_.

        Note:
            This is a void method and the server should continue pipeline
            execution and expect no response from the client.

        Args:
            exit_code: The exit code accompanying the exit keyword.

        .. _PSHost.SetShouldExit Method:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshost.setshouldexit
        """
        self._connection.host_call(HostMethodIdentifier.SetShouldExit, [exit_code])

    def enter_nested_prompt(
        self,
    ) -> None:
        """EnterNestedPrompt Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.EnterNestedPrompt` host
        call that instructs the host to interrupt the currently running
        pipeline and start a new, "nested" input loop, where an input loop is
        the cycle of prompt, input, execute.

        This corresponds to the `PSHost.EnterNestedPrompt Method`_.

        Note:
            This is a void method and the server should continue pipeline
            execution and expect no response from the client.

        .. _PSHost.EnterNestedPrompt Method:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshost.enternestedprompt
        """
        self._connection.host_call(HostMethodIdentifier.EnterNestedPrompt)

    def exit_nested_prompt(
        self,
    ) -> None:
        """ExitNestedPrompt Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.ExitNestedPrompt` host
        call that causes the host to end the currently running input loop. If
        the input loop was created by a prior call to EnterNestedPrompt, the
        enclosing pipeline will be resumed. If the current input loop is the
        top-most loop, then the host will act as though
        :meth:`set_should_exit()` was called.

        This corresponds to the `PSHost.ExitNestedPrompt Method`_.

        Note:
            This is a void method and the server should continue pipeline
            execution and expect no response from the client.

        .. _PSHost.ExitNestedPrompt Method:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshost.exitnestedprompt
        """
        self._connection.host_call(HostMethodIdentifier.ExitNestedPrompt)

    def notify_begin_application(
        self,
    ) -> None:
        """NotifyBeginApplication Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.NotifyBeginApplication`
        host call that is called by the engine to notify the host that it is
        about to execute a "legacy" command line application. A legacy
        application is defined as a console-mode executable that may do one or
        more of the following:

            * reads from stdin
            * writes to stdout
            * writes to stderr

        The engine will always call this method and
        :meth:`notify_end_application()` in pairs.

        This corresponds to the `PSHost.NotifyBeginApplication Method`_.

        Note:
            This is a void method and the server should continue pipeline
            execution and expect no response from the client.

        .. _PSHost.NotifyBeginApplication Method:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshost.notifybeginapplication
        """
        self._connection.host_call(HostMethodIdentifier.NotifyBeginApplication)

    def notify_end_application(
        self,
    ) -> None:
        """NotifyEndApplication Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.NotifyEndApplication`
        host call that is called by the engine to notify the host that the
        execution of a legacy command has completed.

        The engine will always call this method and
        :meth:`notify_begin_application()` in pairs.

        This corresponds to the `PSHost.NotifyEndApplication Method`_.

        Note:
            This is a void method and the server should continue pipeline
            execution and expect no response from the client.

        .. _PSHost.NotifyEndApplication Method:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshost.notifyendapplication
        """
        self._connection.host_call(HostMethodIdentifier.NotifyEndApplication)

    # I don't think this is actually possible to do.
    # def push_runspace(self, runspace) -> None:
    #     self._connection.host_call(HostMethodIdentifier.PushRunspace, [runspace])

    def pop_runspace(
        self,
    ) -> None:
        """PopRunspace Request.

        Sends the :class:`psrpcore.types.HostMethodIdentifier.PopRunspace` host
        call that is called by the engine to notify the host that a Runspace
        pop has been requested.

        This corresponds to the `IHostSupportsInteractiveSession.PopRunspace Method`_.

        Note:
            This is a void method and the server should continue pipeline
            execution and expect no response from the client.

        .. _IHostSupportsInteractiveSession.PopRunspace Method:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.ihostsupportsinteractivesession.poprunspace
        """
        self._connection.host_call(HostMethodIdentifier.PopRunspace)

    def get_is_runspace_pushed(
        self,
    ) -> int:
        """GetIsRunspacePushed Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.GetIsRunspacePushed` host
        call to check if the runspace is pushed or not.

        This corresponds to the `IHostSupportsInteractiveSession.IsRunspacePushed Property`_.

        Note:
            The server should wait for the host response before continuing the
            pipeline that created this request.

        Returns:
            int: The call id for the request.

        .. _IHostSupportsInteractiveSession.IsRunspacePushed Property:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.ihostsupportsinteractivesession.isrunspacepushed
        """
        return self._connection.host_call(HostMethodIdentifier.GetIsRunspacePushed)

    # Also don't think this is possible remotely.
    # def get_runspace(self) -> int:
    #     return self._connection.host_call(HostMethodIdentifier.GetRunspace, [])

    def read_line(
        self,
    ) -> int:
        """ReadLine Request.

        Sends the :class:`psrpcore.types.HostMethodIdentifier.ReadLine` host
        call to read characters from the console until a newline is
        encountered.

        This corresponds to the `PSHostUserInterface.ReadLine Method`_.

        Note:
            The server should wait for the host response before continuing the
            pipeline that created this request.

        Returns:
            int: The call id for the request.

        .. _PSHostUserInterface.ReadLine Method:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostuserinterface.readline
        """
        return self._connection.host_call(HostMethodIdentifier.ReadLine)

    def read_line_as_secure_string(
        self,
    ) -> int:
        """ReadLineAsSecureString Request.

        Sends the :class:`psrpcore.types.HostMethodIdentifier.ReadLineAsSecureString` host
        call to read characters from the console until a newline is
        encountered without echoing the input back to the user.

        This corresponds to the `PSHostUserInterface.ReadLineAsSecureString Method`_.

        Note:
            The server should wait for the host response before continuing the
            pipeline that created this request.

        Returns:
            int: The call id for the request.

        .. _PSHostUserInterface.ReadLineAsSecureString Method:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostuserinterface.readlineassecurestring
        """
        return self._connection.host_call(HostMethodIdentifier.ReadLineAsSecureString)

    def write(
        self,
        value: str,
        foreground_color: typing.Optional[ConsoleColor] = None,
        background_color: typing.Optional[ConsoleColor] = None,
    ) -> None:
        """Write Request.

        Sends the :class:`psrpcore.types.HostMethodIdentifier.Write1` or
        :class:`psrpcore.types.HostMethodIdentifier.Write2` host call that
        writes the characters to the screen buffer.

        This corresponds to the `PSHostUserInterface.Write Method`_.

        Note:
            This is a void method and the server should continue pipeline
            execution and expect no response from the client.

        Args:
            value: The characters to write.
            foreground_color: The color to display the text with.
            background_color: The color to display the background with.

        .. _PSHostUserInterface.Write Method:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostuserinterface.write
        """
        mi = HostMethodIdentifier.Write1
        mp: typing.List[typing.Union[str, int]] = [value]

        if not (foreground_color is None and background_color is None):
            mi = HostMethodIdentifier.Write2
            mp.insert(0, foreground_color.value if foreground_color is not None else 0)
            mp.insert(1, background_color.value if background_color is not None else 0)

        self._connection.host_call(mi, mp)

    def write_line(
        self,
        line: typing.Optional[str] = None,
        foreground_color: typing.Optional[ConsoleColor] = None,
        background_color: typing.Optional[ConsoleColor] = None,
    ) -> None:
        """WriteLine Request.

        Sends the :class:`psrpcore.types.HostMethodIdentifier.WriteLine1`,
        :class:`psrpcore.types.HostMethodIdentifier.WriteLine2`, or
        :class:`psrpcore.types.HostMethodIdentifier.WriteLine2` host call that
        writes the characters with a newline to the screen buffer.

        This corresponds to the `PSHostUserInterface.WriteLine Method`_.

        Note:
            This is a void method and the server should continue pipeline
            execution and expect no response from the client.

        Args:
            line: The line to write, if not set then just a newline is written.
            foreground_color: The color to display the line with.
            background_color: The color to display the background with.

        .. _PSHostUserInterface.WriteLine Method:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostuserinterface.writeline
        """
        mi = HostMethodIdentifier.WriteLine1
        mp: typing.List[typing.Union[str, int]] = []

        if line is not None:
            mi = HostMethodIdentifier.WriteLine2
            mp.append(line)

        if not (foreground_color is None and background_color is None):
            if not mp:
                mp.append("")

            mi = HostMethodIdentifier.WriteLine3
            mp.insert(0, foreground_color.value if foreground_color is not None else 0)
            mp.insert(1, background_color.value if background_color is not None else 0)

        self._connection.host_call(mi, mp)

    def write_error_line(
        self,
        line: str,
    ) -> None:
        """WriteErrorLine Request.

        Sends the :class:`psrpcore.types.HostMethodIdentifier.WriteErrorLine`
        host call that writes the line to the error display of the host.

        This corresponds to the `PSHostUserInterface.WriteErrorLine Method`_.

        Note:
            This is a void method and the server should continue pipeline
            execution and expect no response from the client.

        Args:
            line: The line to write to the error display.

        .. _PSHostUserInterface.WriteErrorLine Method:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostuserinterface.writeerrorline
        """
        self._connection.host_call(HostMethodIdentifier.WriteErrorLine, [line])

    def write_debug_line(
        self,
        line: str,
    ) -> None:
        """WriteDebugLine Request.

        Sends the :class:`psrpcore.types.HostMethodIdentifier.WriteDebugLine`
        host call that writes a debugging message to the host.

        This corresponds to the `PSHostUserInterface.WriteDebugLine Method`_.

        Note:
            This is a void method and the server should continue pipeline
            execution and expect no response from the client.

        Args:
            line: The debug line to write to the display.

        .. _PSHostUserInterface.WriteDebugLine Method:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostuserinterface.writedebugline
        """
        self._connection.host_call(HostMethodIdentifier.WriteDebugLine, [line])

    def write_progress(
        self,
        source_id: int,
        activity_id: int,
        activity: str,
        status_description: str,
        current_operation: typing.Optional[str] = None,
        parent_activity_id: int = -1,
        percent_complete: int = -1,
        record_type: ProgressRecordType = ProgressRecordType.Processing,
        seconds_remaining: int = -1,
    ) -> None:
        """WriteProgress Request.

        Sends the :class:`psrpcore.types.HostMethodIdentifier.WriteProgress`
        host call that writes a progress record to be displayed on the host.

        This corresponds to the `PSHostUserInterface.WriteProgress Method`_.

        Note:
            This is a void method and the server should continue pipeline
            execution and expect no response from the client.

        Args:
            source_id: Unique identifier of the source of the record.
            activity: The description of the activity for which progress is
                being reported.
            activity_id: The Id of the activity to which this record
                corresponds. Used as a key for linking of subordinate
                activities.
            status_description: Current status of the operation, e.g.
                "35 of 50 items copied.".
            current_operation: Current operation of the many required to
                accomplish the activity, e.g. "copying foo.txt".
            parent_activity_id: The Id of the activity for which this record is
                a subordinate.
            percent_complete: The estimate of the percentage of total work for
                the activity that is completed. Set to a negative value to
                indicate that the percentage completed should not be displayed.
            record_type: The type of record represented.
            seconds_remaining: The estimate of time remaining until this
                activity is completed. Set to a negative value to indicate that
                the seconds remaining should not be displayed.

        .. _PSHostUserInterface.WriteProgress Method:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostuserinterface.writeprogress
        """
        # ProgressRecord serialized here is like a PSRP ProgressRecordMsg object.
        self._connection.host_call(
            HostMethodIdentifier.WriteProgress,
            [
                source_id,
                ProgressRecordMsg(
                    ActivityId=activity_id,
                    Activity=activity,
                    StatusDescription=status_description,
                    CurrentOperation=current_operation,
                    ParentActivityId=parent_activity_id,
                    PercentComplete=percent_complete,
                    Type=record_type,
                    SecondsRemaining=seconds_remaining,
                ),
            ],
        )

    def write_verbose_line(
        self,
        line: str,
    ) -> None:
        """WriteVerboseLine Request.

        Sends the :class:`psrpcore.types.HostMethodIdentifier.WriteVerboseLine`
        host call that writes a verbose message to the host.

        This corresponds to the `PSHostUserInterface.WriteVerboseLine Method`_.

        Note:
            This is a void method and the server should continue pipeline
            execution and expect no response from the client.

        Args:
            line: The verbose line to write to the display.

        .. _PSHostUserInterface.WriteVerboseLine Method:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostuserinterface.writeverboseline
        """
        self._connection.host_call(HostMethodIdentifier.WriteVerboseLine, [line])

    def write_warning_line(
        self,
        line: str,
    ) -> None:
        """WriteWarningLine Request.

        Sends the :class:`psrpcore.types.HostMethodIdentifier.WriteWarningLine`
        host call that writes a warning message to the host.

        This corresponds to the `PSHostUserInterface.WriteWarningLine Method`_.

        Note:
            This is a void method and the server should continue pipeline
            execution and expect no response from the client.

        Args:
            line: The warning line to write to the display.

        .. _PSHostUserInterface.WriteWarningLine Method:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostuserinterface.writewarningline
        """
        self._connection.host_call(HostMethodIdentifier.WriteWarningLine, [line])

    def prompt(
        self,
        caption: str,
        message: str,
        descriptions: typing.List[FieldDescription],
    ) -> int:
        """Prompt Request.

        Sends the :class:`psrpcore.types.HostMethodIdentifier.Prompt`
        host call prompts the user with a number of fields for which to supply
        values.

        This corresponds to the `PSHostUserInterface.Prompt Method`_.

        Note:
            The server should wait for the host response before continuing the
            pipeline that created this request.

        Args:
            caption: The caption or title for the prompt.
            message: The message describing the set of fields.
            descriptions: A list of fields to display.

        Returns:
            int: The call id for the request.

        .. _PSHostUserInterface.Prompt Method:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostuserinterface.prompt
        """
        fields = [FieldDescription.ToPSObjectForRemoting(f, for_host=True) for f in descriptions]

        return self._connection.host_call(HostMethodIdentifier.Prompt, [caption, message, fields])

    def prompt_for_credential(
        self,
        caption: str = "PSRPCore credential request",
        message: str = "Enter your credentials.",
        username: typing.Optional[str] = None,
        target_name: typing.Optional[str] = None,
        allowed_credential_types: typing.Optional[PSCredentialTypes] = None,
        options: typing.Optional[PSCredentialUIOptions] = None,
    ) -> int:
        """PromptForCredential Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.PromptForCredential1`, or
        :class:`psrpcore.types.HostMethodIdentifier.PromptForCredential2` host
        call prompts the user for a credential.

        This corresponds to the `PSHostUserInterface.PromptForCredential Method`_.

        Note:
            The server should wait for the host response before continuing the
            pipeline that created this request.

        Args:
            caption: The caption or title for the prompt.
            message: The message describing the credential required.
            username: The username the credential is for, if omitted or
                None/empty the username is requested in the prompt.
            target_name: The domain part of the username if set.
            allowed_credential_types: The types of credential that is being
                requested.
            options: Options to control the UI behaviour.

        Returns:
            int: The call id for the request.

        .. _PSHostUserInterface.PromptForCredential Method:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostuserinterface.promptforcredential
        """
        mi = HostMethodIdentifier.PromptForCredential1
        mp: typing.List[typing.Any] = [caption, message, username, target_name or ""]
        if not (allowed_credential_types is None and options is None):
            mi = HostMethodIdentifier.PromptForCredential2
            mp.append(
                PSCredentialTypes.Default.value if allowed_credential_types is None else allowed_credential_types.value
            )
            mp.append(PSCredentialUIOptions.Default.value if options is None else options.value)

        return self._connection.host_call(mi, mp)

    def prompt_for_choice(
        self,
        caption: str,
        message: str,
        choices: typing.List[ChoiceDescription],
        default_choice: int = -1,
    ) -> int:
        """PromptForChoice Request.

        Sends the :class:`psrpcore.types.HostMethodIdentifier.PromptForChoice`
        host call prompts the user to choose an option from a set list.

        This corresponds to the `PSHostUserInterface.PromptForChoice Method`_.
        See :meth:`prompt_for_multiple_choice()` for a way to allow the user to
        select multiple choices.

        Note:
            The server should wait for the host response before continuing the
            pipeline that created this request.

        Args:
            caption: The caption or title for the prompt.
            message: The message describing the set of choices.
            choices: A list of choices.
            default_choice: The default choice that correspond to the index of
                choices, ``-1`` means no default.

        Returns:
            int: The call id for the request.

        .. _PSHostUserInterface.PromptForChoice Method:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostuserinterface.promptforchoice
        """
        converted_choices = [ChoiceDescription.ToPSObjectForRemoting(c, for_host=True) for c in choices]

        return self._connection.host_call(
            HostMethodIdentifier.PromptForChoice, [caption, message, converted_choices, default_choice]
        )

    def prompt_for_multiple_choice(
        self,
        caption: str,
        message: str,
        choices: typing.List[ChoiceDescription],
        default_choices: typing.Optional[typing.List[int]] = None,
    ) -> int:
        """PromptForChoiceMultipleSelection Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.PromptForChoiceMultipleSelection`
        host call prompts the user to choose multiple options from a set list.

        This corresponds to the
        `IHostUISupportsMultipleChoiceSelection.PromptForChoice Method`_.

        Note:
            The server should wait for the host response before continuing the
            pipeline that created this request.

        Args:
            caption: The caption or title for the prompt.
            message: The message describing the set of choices.
            choices: A list of choices.
            default_choices: A list of default choice that correspond to the index of
                choices.

        Returns:
            int: The call id for the request.

        .. _IHostUISupportsMultipleChoiceSelection.PromptForChoice Method:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.ihostuisupportsmultiplechoiceselection.promptforchoice
        """
        converted_choices = [ChoiceDescription.ToPSObjectForRemoting(c, for_host=True) for c in choices]

        return self._connection.host_call(
            HostMethodIdentifier.PromptForChoiceMultipleSelection,
            [caption, message, converted_choices, default_choices or []],
        )

    def get_foreground_color(
        self,
    ) -> int:
        """GetForegroundColor Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.GetForegroundColor` host
        call to request the foreground color of the host.

        This corresponds to the
        `PSHostRawUserInterface.ForegroundColor Property`_.

        Note:
            The server should wait for the host response before continuing the
            pipeline that created this request.

        Returns:
            int: The call id for the request.

        .. _PSHostRawUserInterface.ForegroundColor Property:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostrawuserinterface.foregroundcolor
        """
        return self._connection.host_call(HostMethodIdentifier.GetForegroundColor)

    def set_foreground_color(
        self,
        color: ConsoleColor,
    ) -> None:
        """SetForegroundColor Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.SetForegroundColor` host
        call to change the foreground color of the host.

        This corresponds to the
        `PSHostRawUserInterface.ForegroundColor Property`_.

        Note:
            This is a void method and the server should continue pipeline
            execution and expect no response from the client.

        Args:
            color: The color to set the foreground color to.

        .. _PSHostRawUserInterface.ForegroundColor Property:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostrawuserinterface.foregroundcolor
        """
        self._connection.host_call(HostMethodIdentifier.SetForegroundColor, [color.value])

    def get_background_color(
        self,
    ) -> int:
        """GetBackgroundColor Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.GetBackgroundColor` host
        call to request the background color of the host.

        This corresponds to the
        `PSHostRawUserInterface.BackgroundColor Property`_.

        Note:
            The server should wait for the host response before continuing the
            pipeline that created this request.

        Returns:
            int: The call id for the request.

        .. _PSHostRawUserInterface.BackgroundColor Property:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostrawuserinterface.backgroundcolor
        """
        return self._connection.host_call(HostMethodIdentifier.GetBackgroundColor)

    def set_background_color(
        self,
        color: ConsoleColor,
    ) -> None:
        """SetBackgroundColor Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.SetBackgroundColor` host
        call to change the background color of the host.

        This corresponds to the
        `PSHostRawUserInterface.BackgroundColor Property`_.

        Note:
            This is a void method and the server should continue pipeline
            execution and expect no response from the client.

        Args:
            color: The color to set the background color to.

        .. _PSHostRawUserInterface.BackgroundColor Property:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostrawuserinterface.backgroundcolor
        """
        self._connection.host_call(HostMethodIdentifier.SetBackgroundColor, [color.value])

    def get_cursor_position(
        self,
    ) -> int:
        """GetCursorPosition Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.GetCursorPosition` host
        call to get the position of the cursor on the screen buffer.

        This corresponds to the
        `PSHostRawUserInterface.CursorPosition Property`_.

        Note:
            The server should wait for the host response before continuing the
            pipeline that created this request.

        Returns:
            int: The call id for the request.

        .. _PSHostRawUserInterface.CursorPosition Property:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostrawuserinterface.cursorposition
        """
        return self._connection.host_call(HostMethodIdentifier.GetCursorPosition)

    def set_cursor_position(
        self,
        x: int,
        y: int,
    ) -> None:
        """SetCursorPosition Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.SetCursorPosition` host
        call to change the position of the cursor on the screen buffer.

        This corresponds to the
        `PSHostRawUserInterface.CursorPosition Property`_.

        Note:
            This is a void method and the server should continue pipeline
            execution and expect no response from the client.

        Args:
            x: The horizontal location to set the cursor to.
            y: The vertical location to set the cursor to.

        .. _PSHostRawUserInterface.CursorPosition Property:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostrawuserinterface.cursorposition
        """
        self._connection.host_call(
            HostMethodIdentifier.SetCursorPosition,
            [Coordinates.ToPSObjectForRemoting(Coordinates(x, y), for_host=True)],
        )

    def get_window_position(
        self,
    ) -> int:
        """GetWindowPosition Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.GetWindowPosition` host
        call to get the position of the view window relative to the screen
        buffer.

        This corresponds to the
        `PSHostRawUserInterface.WindowPosition Property`_.

        Note:
            The server should wait for the host response before continuing the
            pipeline that created this request.

        Returns:
            int: The call id for the request.

        .. _PSHostRawUserInterface.WindowPosition Property:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostrawuserinterface.windowposition
        """
        return self._connection.host_call(HostMethodIdentifier.GetWindowPosition)

    def set_window_position(
        self,
        x: int,
        y: int,
    ) -> None:
        """SetWindowPosition Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.SetWindowPosition` host
        call to change the position of the view window relative to the screen
        buffer.

        This corresponds to the
        `PSHostRawUserInterface.WindowPosition Property`_.

        Note:
            This is a void method and the server should continue pipeline
            execution and expect no response from the client.

        Args:
            x: The horizontal location to set the window to.
            y: The vertical location to set the window to.

        .. _PSHostRawUserInterface.WindowPosition Property:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostrawuserinterface.windowposition
        """
        self._connection.host_call(
            HostMethodIdentifier.SetWindowPosition,
            [Coordinates.ToPSObjectForRemoting(Coordinates(x, y), for_host=True)],
        )

    def get_cursor_size(
        self,
    ) -> int:
        """GetCursorSize Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.GetCursorSize` host
        call to get the size of the cursor as a percentage.

        This corresponds to the
        `PSHostRawUserInterface.CursorSize Property`_.

        Note:
            The server should wait for the host response before continuing the
            pipeline that created this request.

        Returns:
            int: The call id for the request.

        .. _PSHostRawUserInterface.CursorSize Property:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostrawuserinterface.cursorsize
        """
        return self._connection.host_call(HostMethodIdentifier.GetCursorSize)

    def set_cursor_size(
        self,
        size: int,
    ) -> None:
        """SetCursorSize Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.SetCursorSize` host
        call to set the size of the cursor as a percentage.

        This corresponds to the
        `PSHostRawUserInterface.CursorSize Property`_.

        Note:
            This is a void method and the server should continue pipeline
            execution and expect no response from the client.

        Args:
            size: The cursor size as a percentage.

        .. _PSHostRawUserInterface.CursorSize Property:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostrawuserinterface.cursorsize
        """
        self._connection.host_call(HostMethodIdentifier.SetCursorSize, [size])

    def get_buffer_size(
        self,
    ) -> int:
        """GetBufferSize Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.GetBufferSize` host
        call to get the size of the screen buffer as measured by cells.

        This corresponds to the
        `PSHostRawUserInterface.BufferSize Property`_.

        Note:
            The server should wait for the host response before continuing the
            pipeline that created this request.

        Returns:
            int: The call id for the request.

        .. _PSHostRawUserInterface.BufferSize Property:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostrawuserinterface.buffersize
        """
        return self._connection.host_call(HostMethodIdentifier.GetBufferSize)

    def set_buffer_size(
        self,
        width: int,
        height: int,
    ) -> None:
        """SetBufferSize Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.SetBufferSize` host
        call to change the size of the screen buffer as measured by cells.

        This corresponds to the
        `PSHostRawUserInterface.BufferSize Property`_.

        Note:
            This is a void method and the server should continue pipeline
            execution and expect no response from the client.

        Args:
            width: The number of cells in the buffer width.
            height: The number of cells in the buffer height.

        .. _PSHostRawUserInterface.BufferSize Property:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostrawuserinterface.buffersize
        """
        self._connection.host_call(
            HostMethodIdentifier.SetBufferSize, [Size.ToPSObjectForRemoting(Size(width, height), for_host=True)]
        )

    def get_window_size(
        self,
    ) -> int:
        """GetWindowSize Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.GetWindowSize` host
        call to get the size of the view window as measured by cells.

        This corresponds to the
        `PSHostRawUserInterface.WindowSize Property`_.

        Note:
            The server should wait for the host response before continuing the
            pipeline that created this request.

        Returns:
            int: The call id for the request.

        .. _PSHostRawUserInterface.WindowSize Property:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostrawuserinterface.windowsize
        """
        return self._connection.host_call(HostMethodIdentifier.GetWindowSize)

    def set_window_size(
        self,
        width: int,
        height: int,
    ) -> None:
        """SetWindowSize Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.SetWindowSize` host
        call to change the size of the view window size as measured by cells.

        This corresponds to the
        `PSHostRawUserInterface.WindowSize Property`_.

        Note:
            This is a void method and the server should continue pipeline
            execution and expect no response from the client.

        Args:
            width: The number of cells in the view window width.
            height: The number of cells in the view window height.

        .. _PSHostRawUserInterface.WindowSize Property:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostrawuserinterface.windowsize
        """
        self._connection.host_call(
            HostMethodIdentifier.SetWindowSize, [Size.ToPSObjectForRemoting(Size(width, height), for_host=True)]
        )

    def get_window_title(
        self,
    ) -> int:
        """GetWindowTitle Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.GetWindowTitle` host
        call to get the window title.

        This corresponds to the
        `PSHostRawUserInterface.WindowTitle Property`_.

        Note:
            The server should wait for the host response before continuing the
            pipeline that created this request.

        Returns:
            int: The call id for the request.

        .. _PSHostRawUserInterface.WindowTitle Property:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostrawuserinterface.windowtitle
        """
        return self._connection.host_call(HostMethodIdentifier.GetWindowTitle)

    def set_window_title(
        self,
        title: str,
    ) -> None:
        """SetWindowTitle Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.SetWindowTitle` host
        call to change the title of the host window

        This corresponds to the
        `PSHostRawUserInterface.WindowTitle Property`_.

        Note:
            This is a void method and the server should continue pipeline
            execution and expect no response from the client.

        Args:
            title: The title to set the host window to.

        .. _PSHostRawUserInterface.WindowTitle Property:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostrawuserinterface.windowtitle
        """
        self._connection.host_call(HostMethodIdentifier.SetWindowTitle, [title])

    def get_max_window_size(
        self,
    ) -> int:
        """GetMaxWindowSize Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.GetMaxWindowSize` host
        call to get largest possible window size that can fit in the current
        buffer.

        This corresponds to the
        `PSHostRawUserInterface.MaxWindowSize Property`_.

        Note:
            The server should wait for the host response before continuing the
            pipeline that created this request.

        Returns:
            int: The call id for the request.

        .. _PSHostRawUserInterface.MaxWindowSize Property:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostrawuserinterface.maxwindowsize
        """
        return self._connection.host_call(HostMethodIdentifier.GetMaxWindowSize)

    def get_max_physical_window_size(
        self,
    ) -> int:
        """GetMaxPhysicalWindowSize Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.GetMaxPhysicalWindowSize`
        host call to get largest possible window size that can be set.

        This corresponds to the
        `PSHostRawUserInterface.MaxPhysicalWindowSize Property`_.

        Note:
            The server should wait for the host response before continuing the
            pipeline that created this request.

        Returns:
            int: The call id for the request.

        .. _PSHostRawUserInterface.MaxPhysicalWindowSize Property:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostrawuserinterface.maxphysicalwindowsize
        """
        return self._connection.host_call(HostMethodIdentifier.GetMaxPhysicalWindowSize)

    def get_key_available(
        self,
    ) -> int:
        """GetKeyAvailable Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.GetKeyAvailable` host
        call to examine if a keystroke is waiting in the input buffer.

        This corresponds to the
        `PSHostRawUserInterface.KeyAvailable Property`_.

        Note:
            The server should wait for the host response before continuing the
            pipeline that created this request.

        Returns:
            int: The call id for the request.

        .. _PSHostRawUserInterface.KeyAvailable Property:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostrawuserinterface.keyavailable
        """
        return self._connection.host_call(HostMethodIdentifier.GetKeyAvailable)

    def read_key(
        self,
        options: ReadKeyOptions = ReadKeyOptions.IncludeKeyDown,
    ) -> int:
        """ReadKey Request.

        Sends the :class:`psrpcore.types.HostMethodIdentifier.ReadKey` host
        call to request read a key stroke.

        This corresponds to the
        `PSHostRawUserInterface.ReadKey Method`_.

        Note:
            The server should wait for the host response before continuing the
            pipeline that created this request.

        Args:
            options: Further options to control the read key operation.

        Returns:
            int: The call id for the request.

        .. _PSHostRawUserInterface.ReadKey Method:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostrawuserinterface.readkey
        """
        return self._connection.host_call(HostMethodIdentifier.ReadKey, [options.value])

    def flush_input_buffer(
        self,
    ) -> None:
        """FlushInputBuffer Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.FlushInputBuffer` host
        call to reset the keyboard input buffer.

        This corresponds to the
        `PSHostRawUserInterface.FlushInputBuffer Method`_.

        Note:
            This is a void method and the server should continue pipeline
            execution and expect no response from the client.

        .. _PSHostRawUserInterface.FlushInputBuffer Method:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostrawuserinterface.flushinputbuffer
        """
        self._connection.host_call(HostMethodIdentifier.FlushInputBuffer)

    def set_buffer_cells(
        self,
        left: int,
        top: int,
        right: int,
        bottom: int,
        character: typing.Union[int, str, PSChar],
        foreground: ConsoleColor = ConsoleColor.White,
        background: ConsoleColor = ConsoleColor.Black,
    ) -> None:
        """SetBufferContents Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.SetBufferContents1` host
        call to set the contents of the host buffer.

        This corresponds to the
        `PSHostRawUserInterface.SetBufferContents Method`_. See
        :meth:`set_buffer_contents()` to set the buffer contents by individual
        cells.

        Note:
            This is a void method and the server should continue pipeline
            execution and expect no response from the client.

        Args:
            left: The left margin of the region to set the cell to.
            top: The top margin of the region to set the cell to.
            right: The right margin of the region to set the cell to.
            bottom: The bottom margin of the region to set the cell to.
            character: The character used to fill the cells in the region
                specified.
            foreground: The foreground (text) color to fill the cells in the
                region specified.
            background: The background color to fill the cells in the region
                specified.

        .. _PSHostRawUserInterface.SetBufferContents Method:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostrawuserinterface.setbuffercontents
        """
        rectangle = Rectangle.ToPSObjectForRemoting(Rectangle(left, top, right, bottom), for_host=True)
        cell = BufferCell.ToPSObjectForRemoting(
            BufferCell(character, foreground, background, BufferCellType.Complete), for_host=True
        )
        self._connection.host_call(HostMethodIdentifier.SetBufferContents1, [rectangle, cell])

    def set_buffer_contents(
        self,
        x: int,
        y: int,
        contents: typing.List[typing.List[BufferCell]],
    ) -> None:
        """SetBufferContents Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.SetBufferContents2` host
        call to set the contents of the host buffer.

        The ``contents`` value is a list of a list of
        :class:`psrpcore.types.BufferCell` where the first list dimension
        represents each row and the 2nd dimension is each column of that row.

        This corresponds to the
        `PSHostRawUserInterface.SetBufferContents Method`_. See
        :meth:`set_buffer_cells()` to set an individual cell across a region.

        Note:
            This is a void method and the server should continue pipeline
            execution and expect no response from the client.

        Args:
            x: The horizontal location of the upper left corner of the region
                to write the cells from.
            y: The vertical location of the upper left corner of the region to
                write the cells from.
            contents: A list of a list of cells that should be written.

        .. _PSHostRawUserInterface.SetBufferContents Method:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostrawuserinterface.setbuffercontents
        """
        coordinates = Coordinates.ToPSObjectForRemoting(Coordinates(x, y), for_host=True)
        wrap_cell = functools.partial(BufferCell.ToPSObjectForRemoting, for_host=True)
        host_contents = _create_multi_dimensional_array(contents, wrap_cell)
        self._connection.host_call(HostMethodIdentifier.SetBufferContents2, [coordinates, host_contents])

    def get_buffer_contents(
        self,
        left: int,
        top: int,
        right: int,
        bottom: int,
    ) -> int:
        """GetBufferContents Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.GetBufferContents` host
        call to request the contents of the screen region specified.

        This corresponds to the
        `PSHostRawUserInterface.GetBufferContents Method`_.

        Note:
            The server should wait for the host response before continuing the
            pipeline that created this request.

        Note:
            PowerShell does not implement this call for security reasons.
            Unless you trust the client host you should write an error record
            instead.

        Args:
            left: The left margin of the buffer region.
            top: The top margin of the buffer region.
            right: The right margin of the buffer region.
            bottom: The bottom margin of the buffer region.

        Returns:
            int: The call id for the request.

        .. _PSHostRawUserInterface.GetBufferContents Method:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostrawuserinterface.getbuffercontents
        """
        return self._connection.host_call(
            HostMethodIdentifier.GetBufferContents,
            [
                Rectangle.ToPSObjectForRemoting(Rectangle(left, top, right, bottom), for_host=True),
            ],
        )

    def scroll_buffer_contents(
        self,
        source_left: int,
        source_top: int,
        source_right: int,
        source_bottom: int,
        x: int,
        y: int,
        clip_left: int,
        clip_top: int,
        clip_right: int,
        clip_bottom: int,
        character: typing.Union[int, str, PSChar],
        foreground: ConsoleColor = ConsoleColor.White,
        background: ConsoleColor = ConsoleColor.Black,
    ) -> None:
        """ScrollBufferContents Request.

        Sends the
        :class:`psrpcore.types.HostMethodIdentifier.ScrollBufferContents` host
        call to scoll a region of the screen buffer.

        This corresponds to the
        `PSHostRawUserInterface.ScrollBufferContents Method`_.

        Note:
            This is a void method and the server should continue pipeline
            execution and expect no response from the client.

        Args:
            source_left: The left margin of the screen to be scrolled.
            source_top: The top margin of the screen to be scrolled.
            source_right: The right margin of the screen to be scrolled.
            source_bottom: The bottom margin of the screen to be scrolled.
            x: The horizontal location of the upper left coordinate to receive
                the source region contents.
            y: The vertical location of the upper left coordinate to receive
                the source region contents.
            clip_left: The left margin of the clipped region.
            clip_top: The top margin of the clipped region.
            clip_right: The right margin of the clipped region.
            clip_bottom: The bottom margin of the clipped region.
            character: The character used to fill the cells intersecting the
                source and clip region.
            foreground: The foreground (text) color to fill the cells
                intersecting the source and clip region.
            background: The background color to fill the cells intersecting
                the source and clip region.

        .. _PSHostRawUserInterface.ScrollBufferContents Method:
            https://docs.microsoft.com/en-us/dotnet/api/system.management.automation.host.pshostrawuserinterface.scrollbuffercontents
        """
        source = Rectangle.ToPSObjectForRemoting(
            Rectangle(source_left, source_top, source_right, source_bottom), for_host=True
        )
        dest = Coordinates.ToPSObjectForRemoting(Coordinates(x, y), for_host=True)
        clip = Rectangle.ToPSObjectForRemoting(Rectangle(clip_left, clip_top, clip_right, clip_bottom), for_host=True)
        fill = BufferCell.ToPSObjectForRemoting(
            BufferCell(character, foreground, background, BufferCellType.Complete), for_host=True
        )

        self._connection.host_call(HostMethodIdentifier.ScrollBufferContents, [source, dest, clip, fill])
