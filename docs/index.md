# PSRP Core: Python Implementation of the PowerShell Remoting Protocol

PowerShell Remoting Protocol is a protocol used by PowerShell to invoke commands
across the network just different processes. This library is designed around
the Sans-IO concept and focuses entirely on the protocol itself. It is up to
the user of this module to provide the IO using their desired mechanism.

This module is brand new and is still in development so the docs are very
brief and will be expanded upon in the future.

```{eval-rst}
.. toctree::
   :maxdepth: 2
   :caption: Contents:

   protocol
   minishell
   scenarios
   transport
   types

.. toctree::
   :maxdepth: 1
   :caption: API:

   psrpcore
   psrpcore.types
```
