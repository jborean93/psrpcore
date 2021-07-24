# PSRP Transport

While this library is a sans-IO implementation of PSRP there are still a few actions that isn't covered by the PSRP protocol itself.
This page briefly talks about the 2 main connection protocols and the specific messages they contain.

## Connection Specific Actions

These are some common actions that are defined on the connection/transport layer above PSRP:

+ Create
  + Signals the server to create the Runspace Pool or Pipeline object
+ Close
  + Signals the server to close the Runspace Pool or Pipeline object
+ Stop
  + Signals the server to stop a running Pipeline
+ Send
  + Sends a PSRP message targeted towards either a Runspace Pool or Pipeline
+ Receive
  + Receives a PSRP message targeted towards either a Runspace Pool or PIpeline

While only defined for WSMan at this time these actions are also related to PSRP:

+ Connect
  + Connects to a Runspace Pool or Pipeline that was disconnected by a different client
+ Disconnect
  + Disconnects from an opened Runspace Pool
+ Reconnect
  + Reconnects to a Runspace Pool or Pipeline that was disconnected by the same client
+ Enumerate
  + List all the Runspace Pools and Pipelines on the server


## WSMan

Web Services Management Protocol (WSMan), also known as Windows Remote Management (WinRM) is another protocol that is defined by Microsoft in [MS-WSMV](https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-wsmv/055dc36b-db2a-41ae-a47b-82cbfa0b4a92).
Historically it's the only transport that was supported by PSRP and is still a protocol used today in the Windows world.
WSMan is quite a complex protocol already so this doc won't cover it too much.
One major difference between WSMan and OutOfProc transports is that it can manage multiple Runspace Pools over the same transport.
It also offers the ability for pool disconnect/reconnections.

A brief overview of how it implements each message:

|Action|Protocol Equivalent|Details|
|-|-|-|
|Create (Shell)|Create Shell|Includes as many PSRP messages in the message|
|Create (Pipeline)|Create Command|Includes as many PSRP messages in the message|
|Close (Pool)|Signal Terminate|Sends the terminate signal to the specified pipeline|
|Close (Pipeline)|Delete|Sends the delete message to the specified Runspace Pool|
|Stop|Signal powershell/signal/ctrl_c|Sends a PowerShell specific ctrl+c signal to the specified pipeline|
|Send|Send|Sends data to the `stdin` or `pr` (PromptResponse) pipe of the shell|
|Receive|Receive|Requests output from the Runspace Pool or Pipeline - loops until closed|


## OutOfProc

The OutOfProc transport is a simplified transport that was introduced with PowerShell v5.1.
It uses simple XML packets that is exchanged on either a bi-directional or 2 uni-directional pipe.
The OutOfProc transports are currently used for the following connections in PowerShell:

+ SSH
  + Connects to a specific SSH subsystem and uses the `stdout` and `stdin` pipe to read and write data respectively
+ Named Pipes
  + Connects to a Named Pipe (Windows) or Unix Domain Socket (Unix) to read and write data to
+ Process stdio
  + Like SSH but just starts the process locally and uses the `stdout` and `stdin` pipe
+ Hyper-V/Docker
  + Uses a Hyper-V/Docker specific pipe to read and write data to

While the underlying transport may differ with these connections the same actions apply:

|Action|Protocol Equivalent|Details|
|-|-|-|
|Create (Pool)|PSData|Base64 encodes the fragment in a PSData XML payload|
|Create (Pipe)|PSGuid Command|Contains no data, signifies a new command is created and to expect more data|
|Close|PSGuid Close|The pipeline id is set to the PSGuid element otherwise it's all 0's|
|Stop|PSGuid Signal|The pipeline id is set to the PSGuid element|
|Send|PSData|Base64 encodes the fragment in a PSData XML payload|
|Receive|N/A|There is no special message to request output, it is just read from the relevant pipe|

The format of the PSData and PSGuid element is as follows:

```xml
<!--PSData (for creating a pool and sending data-->
<Data Stream='Default|PromptResponse' PSGuid='id uuid'>base64 fragment(s)</Data>

<!--PSGuid - Action is either Command/Close/Signal-->
<Action PSGuid='id uuid' />

<!--PS Ack - In response to PSData or PSGuid-->
<ActionAck PSGuid='id uuid' />
```

The server is expected to send an acknowledgement of each PSGuid and PSData element received.
Some PSData packets may not have an acknowledgement until all expected messages for that scenario have been received.
