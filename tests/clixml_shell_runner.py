import sys

import psrpcore


class MyObj:

    def __init__(self) -> None:
        self.value = 123
        self.other = "foo"


def main() -> None:
    shell = psrpcore.ClixmlShell()

    shell.write_output("string")
    shell.write_output(MyObj())
    shell.write_output(psrpcore.types.WarningRecord(Message="warning as output"))

    shell.write_error("error as string")
    shell.write_error(
        psrpcore.types.ErrorRecord(
            Exception=psrpcore.types.NETException(Message="error as record"),
            CategoryInfo=psrpcore.types.ErrorCategoryInfo(
                Category=psrpcore.types.ErrorCategory.DeviceError,
            ),
        )
    )
    shell.write_debug("debug")
    shell.write_verbose("verbose")
    shell.write_warning("warning")
    shell.write_information("information as string")
    shell.write_information(
        psrpcore.types.InformationRecord.create(
            message_data="information as record",
            source="my source",
            time_generated=psrpcore.types.PSDateTime(1970, 1, 1),
        ),
    )
    shell.write_progress(
        1,
        psrpcore.types.ProgressRecord(
            ActivityId=1,
            Activity="progress",
            StatusDescription="status",
        ),
    )

    sys.stdout.write(shell.data_to_send())

    shell.write_output("final")
    sys.stdout.write(shell.data_to_send())


if __name__ == "__main__":
    main()
