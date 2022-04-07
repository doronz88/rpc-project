import contextlib
import json
import os
import plistlib
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Union, List
from uuid import UUID

from pygments import highlight, formatters, lexers
from xonsh.built_ins import XSH
from xonsh.completers.tools import contextual_completer

import rpcclient
from rpcclient.client_factory import create_client
from rpcclient.protocol import DEFAULT_PORT


def _default_json_encoder(obj):
    if isinstance(obj, bytes):
        return obj.hex()
    if isinstance(obj, datetime):
        return str(obj)
    if isinstance(obj, UUID):
        return str(obj)
    raise TypeError()


def _print_json(buf, colored=True, default=_default_json_encoder):
    formatted_json = json.dumps(buf, sort_keys=True, indent=4, default=default)
    if colored:
        colorful_json = highlight(formatted_json, lexers.JsonLexer(),
                                  formatters.TerminalTrueColorFormatter(style='stata-dark'))
        print(colorful_json)
    else:
        print(formatted_json)


class XonshRc:
    def __init__(self):
        self._client = None  # type: Union[None, rpcclient.client.Client, rpcclient.darwin.client.DarwinClient]
        self._commands = {}
        self._orig_aliases = {}
        self._orig_prompt = XSH.env['PROMPT']
        self._register_rpc_command('rpc-connect', self._rpc_connect)
        self._register_rpc_command('rpc-list-commands', self._rpc_list_commands)

        if '_RPC_AUTO_CONNECT_HOSTNAME' in XSH.env:
            self._rpc_connect([XSH.env['_RPC_AUTO_CONNECT_HOSTNAME'], XSH.env['_RPC_AUTO_CONNECT_PORT']],
                              stdin=None, stdout=sys.stdout, stderr=None)

        print('''
        Welcome to xonsh-rpc shell! 👋
        Below is list of commands that have been remapped to work over the target device *instead* of the
        default machine behavior:
        ''')
        self._rpc_list_commands([], None, sys.stdout, None)

    def _register_rpc_command(self, name, handler):
        self._commands[name] = handler
        if XSH.aliases.get(name):
            self._orig_aliases[name] = XSH.aliases[name]
        XSH.aliases[name] = handler

    def _rpc_disconnect(self, args, stdin, stdout, stderr):
        self._client.close()
        for k, v in self._orig_aliases.items():
            XSH.aliases[k] = v

    def _rpc_connect(self, args, stdin, stdout, stderr):
        if '--help' in args:
            print('rpc-connect <hostname> [port]', file=stdout)
            return

        hostname = args[0]
        port = DEFAULT_PORT
        if len(args) > 1:
            port = int(args[1])
        self._client = create_client(hostname, port)

        # -- rpc
        self._register_rpc_command('rpc-disconnect', self._rpc_disconnect)

        # -- automation
        self._register_rpc_command('press-labels', self._rpc_press_labels)
        self._register_rpc_command('press-keys', self._rpc_press_keys)

        # -- processes
        self._register_rpc_command('run', self._rpc_run)
        self._register_rpc_command('run-async', self._rpc_run_async)
        self._register_rpc_command('ps', self._rpc_ps)
        self._register_rpc_command('kill', self._rpc_kill)

        # -- fs
        self._register_rpc_command('ls', self._rpc_ls)
        self._register_rpc_command('ln', self._rpc_ln)
        self._register_rpc_command('touch', self._rpc_touch)
        self._register_rpc_command('pwd', self._rpc_pwd)
        self._register_rpc_command('cd', self._rpc_cd)
        self._register_rpc_command('rm', self._rpc_rm)
        self._register_rpc_command('mv', self._rpc_mv)
        self._register_rpc_command('mkdir', self._rpc_mkdir)
        self._register_rpc_command('cat', self._rpc_cat)
        self._register_rpc_command('pull', self._rpc_pull)
        self._register_rpc_command('push', self._rpc_push)
        self._register_rpc_command('chmod', self._rpc_chmod)
        self._register_rpc_command('find', self._rpc_find)
        self._register_rpc_command('xattr-get-dict', self._rpc_xattr_get_dict)
        self._register_rpc_command('vim', self._rpc_vim)

        # -- plist
        self._register_rpc_command('plshow', self._rpc_plshow)

        # -- misc
        self._register_rpc_command('open', self._rpc_open)

        XSH.env['PROMPT'] = f'[{{BOLD_GREEN}}{self._client.uname.nodename}{{RESET}} ' \
                            f'{{BOLD_YELLOW}}{{cwd}}{{RESET}}]$ '
        XSH.env['PROMPT_FIELDS']['cwd'] = self._client.fs.pwd

    def _rpc_xattr_get_dict(self, args, stdin, stdout, stderr):
        if '--help' in args:
            print('USAGE: xattr-get-dict <label0> [label1] ...', file=stdout)
            return
        self._client.accessibility.press_labels(args)

    def _rpc_vim(self, args, stdin, stdout, stderr):
        if '--help' in args:
            print('USAGE: vim <filename>', file=stdout)
            return
        remote_filename = args[0]
        with self._edit_remotely(remote_filename) as local_filename:
            os.system(f'vim "{local_filename}"')

    def _rpc_press_labels(self, args, stdin, stdout, stderr):
        if '--help' in args:
            print('USAGE: press <label0> [label1] ...', file=stdout)
            return
        self._client.accessibility.press_labels(args)

    def _rpc_press_keys(self, args, stdin, stdout, stderr):
        keys = {
            'power': self._client.hid.send_power_button_press,
            'home': self._client.hid.send_home_button_press,
            'volup': self._client.hid.send_volume_up_button_press,
            'voldown': self._client.hid.send_volume_down_button_press,
            'mute': self._client.hid.send_mute_button_press,
        }
        if '--help' in args:
            print('USAGE: press <key0> [key1] ...', file=stdout)
            print(f'key list: {keys.keys()}', file=stdout)
            return

        for k in args:
            keys[k]()

    def _rpc_run(self, args, stdin, stdout, stderr):
        if '--help' in args:
            print('USAGE: run <arg0> [arg1] ...', file=stderr)
            return
        result = self._client.spawn(args, raw_tty=False, stdin=stdin, stdout=stdout)
        return result.error

    def _rpc_run_async(self, args, stdin, stdout, stderr):
        if '--help' in args:
            print('USAGE: run-async <arg0> [arg1] ...', file=stdout)
            return
        print(self._client.spawn(args, raw_tty=False, background=True), file=stdout)

    def _rpc_kill(self, args, stdin, stdout, stderr):
        if '--help' in args:
            print('USAGE: kill <pid> <signal_number>', file=stdout)
            return
        self._client.processes.kill(args[0], int(args[1]))

    def _rpc_ps(self, args, stdin, stdout, stderr):
        if '--help' in args:
            print('USAGE: ps', file=stdout)
            return

        for p in self._client.processes.list():
            print(f'{p.pid:5} {p.path}', file=stdout)

    def _rpc_ls(self, args, stdin, stdout, stderr):
        if '--help' in args:
            print('USAGE: ls <path>', file=stdout)
            return

        path = '.'
        if args:
            path = args[0]

        for f in self._client.fs.scandir(path):
            print(f.name, file=stdout)

    def _rpc_ln(self, args, stdin, stdout, stderr):
        if '--help' in args:
            print('USAGE: ln [-s] <src> <dst>', file=stdout)
            return

        if args[0] == '-s':
            src = args[1]
            dst = args[2]
            self._client.fs.symlink(src, dst)
        else:
            src = args[0]
            dst = args[1]
            self._client.fs.link(src, dst)

    def _rpc_touch(self, args, stdin, stdout, stderr):
        if '--help' in args:
            print('USAGE: touch <filename>', file=stdout)
            return

        with self._client.fs.open(args[0], 'w'):
            pass

    def _rpc_pwd(self, args, stdin, stdout, stderr):
        print(self._client.fs.pwd(), file=stdout)

    @contextual_completer
    def _rpc_cd(self, args, stdin, stdout, stderr):
        if '--help' in args:
            print('USAGE: cd <path>', file=stdout)
            return
        self._client.fs.chdir(args[0])

    def _rpc_rm(self, args, stdin, stdout, stderr):
        if '--help' in args:
            print('USAGE: rm [-r] <path0> [path1] ...', file=stdout)
            return

        if args[0] != '-r':
            for filename in args:
                self._client.fs.remove(filename)
            return

        # recursive
        for path in args[1:]:
            for filename in self._find(path):
                self._client.fs.remove(filename)
            self._client.fs.remove(path)

    def _rpc_mv(self, args, stdin, stdout, stderr):
        if '--help' in args:
            print('USAGE: rm <path>', file=stdout)
            return
        self._client.fs.rename(args[0], args[1])

    def _rpc_mkdir(self, args, stdin, stdout, stderr):
        if '--help' in args:
            print('USAGE: mkdir <path>', file=stdout)
            return
        self._client.fs.mkdir(args[0], mode=0o777)

    def _rpc_cat(self, args, stdin, stdout, stderr):
        if '--help' in args:
            print('USAGE: cat <file0> [file1] ...', file=stdout)
            return

        for filename in args:
            with self._client.fs.open(filename, 'r') as f:
                print(f.readall(), file=stdout, end='')

        print('', file=stdout)

    def _rpc_pull(self, args, stdin, stdout, stderr):
        if '--help' in args:
            print('USAGE: pull <remote> <local>', file=stdout)
            return
        return self._pull(args[0], args[1])

    def _rpc_push(self, args, stdin, stdout, stderr):
        if '--help' in args:
            print('USAGE: push <local> <remote>', file=stdout)
            return
        return self._push(args[0], args[1])

    def _rpc_chmod(self, args, stdin, stdout, stderr):
        if '--help' in args:
            print('USAGE: chmod <mode> <filename>', file=stdout)
            return
        self._client.fs.chmod(args[0], int(args[1], 8))

    def _rpc_find(self, args, stdin, stdout, stderr):
        if '--help' in args:
            print('USAGE: find <path>', file=stdout)
            return

        for filename in self._find(args[0]):
            print(filename, file=stdout)

    def _rpc_plshow(self, args, stdin, stdout, stderr):
        if '--help' in args:
            print('USAGE: plshow <filename>', file=stdout)
            return
        with self._client.fs.open(args[0], 'r') as f:
            _print_json(plistlib.loads(f.readall()))

    def _rpc_open(self, args, stdin, stdout, stderr):
        if '--help' in args:
            print('USAGE: open <filename>', file=stdout)
            return
        remote = args[0]
        with self._edit_remotely(remote) as local:
            os.system(f'open -W "{local}"')

    def _rpc_list_commands(self, args, stdin, stdout, stderr):
        for k, v in self._commands.items():
            print(f'👾 {k}', file=stdout)

    @contextlib.contextmanager
    def _edit_remotely(self, remote):
        with tempfile.TemporaryDirectory() as local_dir:
            local = Path(local_dir) / Path(remote).parts[-1]
            self._pull(remote, local.name)
            try:
                yield local.name
            finally:
                self._push(local.name, remote)

    def _find(self, path: str):
        for root, dirs, files in self._client.fs.walk(path):
            for name in files:
                yield os.path.join(root, name)
            for name in dirs:
                yield os.path.join(root, name)

    def _listdir(self, path: str) -> List[str]:
        return self._client.fs.listdir(path)

    def _pull(self, remote_filename, local_filename):
        with self._client.fs.open(remote_filename, 'r') as remote_fd:
            with open(local_filename, 'wb') as local_fd:
                local_fd.write(remote_fd.readall())

    def _push(self, local_filename, remote_filename):
        with open(local_filename, 'rb') as from_fd:
            with self._client.fs.open(remote_filename, 'w') as to_fd:
                to_fd.write(from_fd.read())


_rpc_client = XonshRc()
