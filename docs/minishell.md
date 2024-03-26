# PowerShell MiniShell

It is possible to use a cutdown PowerShell integration to exchange data between a Python process and a PowerShell one.
In PowerShell this concept is called a minishell and uses CLIXML strings through stdin and stdout.
Using the builtin [type serialization](./types.md) it is possible to also exchange more rich types in Python.

## Output to PowerShell

The first scenario where the CLIXML minishell is useful is to output data to the calling PowerShell process.
Using the [ClixmlShell](psrpcore.ClixmlShell) class it is possible to emit Python objects to the calling PowerShell process as well as emitting other stream records.
This following Python script can be called in PowerShell

```python
import sys

import psrpcore


class CustomObject:
    def __init__(self) -> None:
        self.attribute = 'value'
        self.other = 123


def main() -> None:
    shell = psrpcore.ClixmlShell()

    # write_output can write any object
    shell.write_output("string value")
    shell.write_output(CustomObject())

    # write_verbose can write verbose records
    shell.write_verbose("verbose record")

    # When finish, write the CLIXML to stdout
    sys.stdout.write(shell.data_to_send())


if __name__ == '__main__':
    main()
```

In PowerShell this can be captured in PowerShell executing the Python process

```powershell
$out = python script.py

$out[0]  # string value
$out[1].attribute  # value
$out[1].other  # other
```

It is important that PowerShell is set to either capture or redirect/pipe the Python process output so it processes the CLIXML.
Specific types or direct `PSObject` manipulation can all be exposed through `psrpcore.types` see [Python to .NET Type Information](./types.md) for more information.

## Output to Python

The second scenario is where Python executes a PowerShell process and captures the objects it emits.
The captured CLIXML output can be processed through the [ClixmlOutput](psrpcore.ClixmlOutput) allowing Python to access the objects in a more structured manner.
An example, here is a PowerShell script that can output some more structured objects:

```powershell
[PSCustomObject]@{
    attribute = 'value'
    other = 123
}

Write-Error 'Error Message'
```

This can be captured in Python with:

```python
import subprocess

import psrpcore


def main() -> None:
    proc = subprocess.run(
        ["pwsh", "-OutputFormat", "xml", "-File", "ps.ps1"],
        capture_output=True,
        check=True,
        text=True,
    )
    out = psrpcore.ClixmlOutput.from_clixml([proc.stdout, proc.stderr])

    for obj in out.output:
        print(obj.attribute)

    for obj in out.error:
        print(f"Error: {obj}")


if __name__ == "__main__":
    main()
```

It is important that PowerShell is called with `-OutputFormat xml` to ensure the output is in the CLIXML format.
The `ClixmlOutput` object contains an attribute for every string, in this case the output stream contains 1 entry being the `PSCustomObject` from the PowerShell script and single error record from the `Write-Error` call.

```{note}
There is a bug in PowerShell where `ProgressRecords` are not emitted when `stdout` is redirected.
```
