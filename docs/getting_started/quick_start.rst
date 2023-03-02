Quick start
===========

To execute the server:

::

   Usage: ./rpcserver [-p port] [-o (stdout|syslog|file:filename)]
   -h  show this help message
   -o  output. can be all of the following: stdout, syslog and file:filename. can be passed multiple times

   Example usage:
   ./rpcserver -p 5910 -o syslog -o stdout -o file:/tmp/log.txt

Connecting via:

.. code:: shell

   python3 -m rpcclient <HOST>

Full usage:

::

   Usage: python -m rpcclient [OPTIONS] HOSTNAME

   Options:
     -p, --port INTEGER
     -r, --rebind-symbols      reload all symbols upon connection
     -l, --load-all-libraries  load all libraries
     --help                    Show this message and exit.

..

   **NOTE:** If you are attempting to connect to a **jailbroken iOS
   device**, you will be required to also create a TCP tunnel to your
   device. For example, using:
   ```pymobiledevice3`` <https://github.com/doronz88/pymobiledevice3>`__:
   ``python3 -m pymobiledevice3 usbmux forward 5910 5910 -vvv``

You should now get a nice iPython shell looking like this:

::

   ➜  rpc-project git:(master) python3 -m rpcclient 127.0.0.1
   2022-03-29 23:42:31 Cyber root[24947] INFO connection uname.sysname: Darwin

   Welcome to the rpcclient interactive shell! You interactive shell for controlling the remote rpcserver.
   Feel free to use the following globals:

   🌍 p - the injected process
   🌍 symbols - process global symbols

   Have a nice flight ✈️!
   Starting an IPython shell... 🐍

   Python 3.9.10 (main, Jan 15 2022, 11:48:04)
   Type 'copyright', 'credits' or 'license' for more information
   IPython 7.25.0 -- An enhanced Interactive Python. Type '?' for help.

   In [1]:

And… Congrats! You are now ready to go! 😎

Try accessing the different features using the global ``p`` variable.
For example (Just a tiny sample of the many things you can now do. Feel
free to explore much more!):

::

   In [2]: p.spawn(['sleep', '1'])
   2022-03-29 23:45:51 Cyber root[24947] INFO shell process started as pid: 25047
   Out[2]: SpawnResult(error=0, pid=25047, stdout=<_io.TextIOWrapper name='<stdout>' mode='w' encoding='utf-8'>)

   In [3]: p.fs.listdir('.')
   Out[3]:
   ['common.c',
    '.pytest_cache',
    'Makefile',
    'rpcserver_iphoneos_arm64',
    'rpcserver.c',
    'common.h',
    'rpcserver_macosx_x86_64',
    'ents.plist',
    'build_darwin.sh']

   In [4]: p.processes.get_by_pid(p.pid).fds
   Out[4]:
   [FileFd(fd=0, path='/dev/ttys000'),
    FileFd(fd=1, path='/dev/ttys000'),
    FileFd(fd=2, path='/dev/ttys000'),
    Ipv6TcpFd(fd=3, local_address='0.0.0.0', local_port=5910, remote_address='0.0.0.0', remote_port=0),
    Ipv6TcpFd(fd=4, local_address='127.0.0.1', local_port=5910, remote_address='127.0.0.1', remote_port=53217),
    Ipv6TcpFd(fd=5, local_address='127.0.0.1', local_port=5910, remote_address='127.0.0.1', remote_port=53229),
    Ipv6TcpFd(fd=6, local_address='127.0.0.1', local_port=5910, remote_address='127.0.0.1', remote_port=53530)]

   In [5]: p.processes.get_by_pid(p.pid).regions[:3]
   Out[5]:
   [Region(region_type='__TEXT', start=4501995520, end=4502028288, vsize='32K', protection='r-x', protection_max='r-x', region_detail='/Users/USER/*/rpcserver_macosx_x86_64'),
    Region(region_type='__DATA_CONST', start=4502028288, end=4502044672, vsize='16K', protection='r--', protection_max='rw-', region_detail='/Users/USER/*/rpcserver_macosx_x86_64'),
    Region(region_type='__DATA', start=4502044672, end=4502061056, vsize='16K', protection='rw-', protection_max='rw-', region_detail='/Users/USER/*/rpcserver_macosx_x86_64')]