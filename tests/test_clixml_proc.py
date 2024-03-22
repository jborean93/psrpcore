# Copyright: (c) 2024, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)

import base64
import subprocess

import psrpcore

from .conftest import PWSH_PATH, ClientTransport, FakeCryptoProvider, run_pipeline


def test_deserialize_process_clixml() -> None:
    cmd = r"""
"string" | Add-Member -NotePropertyName MyProp -NotePropertyValue foo -PassThru
1
[PSCustomObject]@{
    PSTypeName = 'MyType'
    Prop1 = $true
    Prop2 = [Int64]2
}
"""

    enc_cmd = base64.b64encode(cmd.encode("utf-16-le")).decode()
    res = subprocess.run(
        [PWSH_PATH or "pwsh", "-OutputFormat", "xml", "-EncodedCommand", enc_cmd],
        capture_output=True,
        text=True,
    )

    actual = psrpcore.types.deserialize_clixml(res.stdout, FakeCryptoProvider())
    assert isinstance(actual, list)
    assert len(actual) == 3
    assert actual[0] == "string"
    assert isinstance(actual[0], psrpcore.types.PSString)
    assert actual[0].MyProp == "foo"
    assert actual[1] == 1
    assert isinstance(actual[1], psrpcore.types.PSInt)
    assert isinstance(actual[2], psrpcore.types.PSObject)
    assert actual[2].PSTypeNames == [
        "Deserialized.MyType",
        "Deserialized.System.Management.Automation.PSCustomObject",
        "Deserialized.System.Object",
    ]
    assert actual[2].Prop1 is True
    assert actual[2].Prop2 == 2
    assert isinstance(actual[2].Prop2, psrpcore.types.PSInt64)


def test_serialize_process_clixml(client_pwsh: ClientTransport) -> None:
    obj1 = psrpcore.types.PSString("string")
    obj1.PSObject.extended_properties.append(psrpcore.types.PSNoteProperty("MyProp", "foo"))
    obj2 = psrpcore.types.PSCustomObject(
        PSTypeName="MyType",
        Prop1=True,
        Prop2=psrpcore.types.PSInt64(2),
    )
    clixml = psrpcore.types.serialize_clixml([obj1, 1, obj2], FakeCryptoProvider())

    client_pwsh.runspace.open()
    client_pwsh.data()
    while client_pwsh.runspace.state == psrpcore.types.RunspacePoolState.Opening:
        client_pwsh.next_event()

    cmd = rf"""
$data = @'
{clixml}
'@

[System.Management.Automation.PSSerializer]::Deserialize($data)
"""
    res = run_pipeline(client_pwsh, cmd)
    assert len(res) == 4
    assert isinstance(res[0], psrpcore.PipelineOutputEvent)
    assert isinstance(res[0].data, psrpcore.types.PSString)
    assert res[0].data == "string"
    assert res[0].data.MyProp == "foo"

    assert isinstance(res[1], psrpcore.PipelineOutputEvent)
    assert isinstance(res[1].data, psrpcore.types.PSInt)
    assert res[1].data == 1

    assert isinstance(res[2], psrpcore.PipelineOutputEvent)
    assert isinstance(res[2].data, psrpcore.types.PSObject)
    assert res[2].data.PSTypeNames == [
        "Deserialized.Deserialized.MyType",
        "Deserialized.Deserialized.System.Management.Automation.PSCustomObject",
        "Deserialized.Deserialized.System.Object",
    ]
    assert res[2].data.Prop1 is True
    assert res[2].data.Prop2 == 2
    assert isinstance(res[2].data.Prop2, psrpcore.types.PSInt64)

    assert isinstance(res[3], psrpcore.PipelineStateEvent)
    assert res[3].state == psrpcore.types.PSInvocationState.Completed
