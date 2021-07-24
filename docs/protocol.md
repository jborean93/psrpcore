# PowerShell Remoting Protocol Information

The PowerShell Remoting Protocol (PSRP) is documented by Microsoft under [MS-PSRP](https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-psrp/602ee78e-9a19-45ad-90fa-bb132b7cecec).
The protocol defines the communication that occurs between PowerShell instances.
While it also includes details on one of the underlying transport, WSMan, this layer is not part of PSRP itself and thus isn't implemented in this library.


## Glossary

Here are some of the key terms used in PSRP and this library:

### Runspace Pool

A runspace pool is a collection of [runspaces](./protocol.html/#runspace).
This is the primary interface that a client and server used to communicate with each other.
A runspace pool is represented by the following classes:

+ [ClientRunspacePool](./source/psrpcore.html#psrpcore.ClientRunspacePool)
+ [ServerRunspacePool](./source/psrpcore.html#psrpcore.ServerRunspacePool)

### Runspace

A runspace is an entity that is able to run a [pipeline](./protocol.html/#pipeline) (only 1 concurrently) and also contains session state information, like variables.
There is no specific runspace class in this library as the same functionality is offered by using a runspace pool with a min and max count of 1.

### Pipeline

A pipeline contains an ordered list of [commands](./protocol.html/#command) to be run.
The output of the first command becomes the input to the next command in the list until all commands have been run.
A pipeline is represented by the following classes:

+ [ClientPowerShell](./source/psrpcore.html#psrpcore.ClientPowerShell)
  + Main pipeline used by a client to run a collection of PowerShell commands
+ [ClientGetCommandMetadata](./source/psrpcore.html#psrpcore.ClientGetCommandMetadata)
  + Pipeline used by a client to extract command metadata of the connected runspace
+ [ServerPipeline](./source/psrpcore.html#psrpcore.ServerPipeline)
  + Pipeline used by a server to represent the client pipeline requested

### Command

A command is process that can be executed by the server.
It contains the necessary instructions to tell the server what to run.
A command is represent by the following class:

+ [Command](./source/psrpcore.html#psrpcore.Command)

### PSHost

A PSHost is the interface that is used by the runspace/pipeline to communicate with the user.
This communication is typically, but not limited to, in the form of a console/terminal window.
A PSHost is represented by the following classes:

+ [ClientHostResponder](./source/psrpcore.html#psrpcore.ClientHostResponder)
+ [ServerHostRequestor](./source/psrpcore.html#psrpcore.ServerHostRequestor)

### Fragment

A fragment contains a message, or part of, that is the fundamental message streamed between the client and the server.
The size of the fragment is defined by the underlying transport used.

### CLIXML

CLIXML is the serialized form of PowerShell objects in XML format.
It used to exchange messages between the client and server.
