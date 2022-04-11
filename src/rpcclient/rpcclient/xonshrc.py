import contextlib
import json
import os
import plistlib
import sys
import tempfile
import time
from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
from typing import Union, List
from uuid import UUID

import plumbum
from pygments import highlight, formatters, lexers
from xonsh.built_ins import XSH
from xonsh.completers.tools import contextual_completer

import rpcclient
from rpcclient.client_factory import create_client
from rpcclient.exceptions import RpcFileExistsError
from rpcclient.protocol import DEFAULT_PORT
from rpcclient.structs.consts import SIGTERM


def _default_json_encoder(obj):
    if isinstance(obj, bytes):
        return obj.hex()
    if isinstance(obj, datetime):
        return str(obj)
    if isinstance(obj, UUID):
        return str(obj)
    raise TypeError()


def _print_json(buf, colored=True, default=_default_json_encoder, file=None):
    formatted_json = json.dumps(buf, sort_keys=True, indent=4, default=default)
    if colored:
        colorful_json = highlight(formatted_json, lexers.JsonLexer(),
                                  formatters.TerminalTrueColorFormatter(style='stata-dark'))
        print(colorful_json, file=file, flush=True)
    else:
        print(formatted_json, file=file, flush=True)


class XonshRc:
    def __init__(self):
        self.client = None  # type: Union[None, rpcclient.client.Client, rpcclient.darwin.client.DarwinClient]
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
        Use `$rpc` to access current client.
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
        self.client.close()
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
        self.client = create_client(hostname, port)

        # -- rpc
        self._register_rpc_command('rpc-disconnect', self._rpc_disconnect)
        self._register_rpc_command('rpc-which', self._rpc_which)

        # -- automation
        self._register_rpc_command('list-labels', self._rpc_list_labels)
        self._register_rpc_command('press-labels', self._rpc_press_labels)
        self._register_rpc_command('press-keys', self._rpc_press_keys)

        # -- processes
        self._register_rpc_command('run', self._rpc_run)
        self._register_rpc_command('run-async', self._rpc_run_async)
        self._register_rpc_command('ps', self._rpc_ps)
        self._register_rpc_command('kill', self._rpc_kill)
        self._register_rpc_command('killall', self._rpc_killall)

        # -- fs
        self._register_rpc_command('ls', self._rpc_ls)
        self._register_rpc_command('ln', self._rpc_ln)
        self._register_rpc_command('touch', self._rpc_touch)
        self._register_rpc_command('pwd', self._rpc_pwd)
        self._register_rpc_command('cd', self._rpc_cd)
        self._register_rpc_command('rm', self._rpc_rm)
        self._register_rpc_command('mv', self._rpc_mv)
        self._register_rpc_command('cp', self._rpc_cp)
        self._register_rpc_command('mkdir', self._rpc_mkdir)
        self._register_rpc_command('cat', self._rpc_cat)
        self._register_rpc_command('bat', self._rpc_bat)
        self._register_rpc_command('pull', self._rpc_pull)
        self._register_rpc_command('push', self._rpc_push)
        self._register_rpc_command('chmod', self._rpc_chmod)
        self._register_rpc_command('find', self._rpc_find)
        self._register_rpc_command('xattr-get-dict', self._rpc_xattr_get_dict)
        self._register_rpc_command('vim', self._rpc_vim)
        self._register_rpc_command('entitlements', self._rpc_entitlements)

        # -- plist
        self._register_rpc_command('plshow', self._rpc_plshow)

        # -- media
        self._register_rpc_command('record', self._rpc_record)
        self._register_rpc_command('play', self._rpc_play)

        # -- misc
        self._register_rpc_command('open', self._rpc_open)
        self._register_rpc_command('date', self._rpc_date)
        self._register_rpc_command('env', self._rpc_env)
        self._register_rpc_command('file', self._rpc_file)

        XSH.env['PROMPT'] = f'[{{BOLD_GREEN}}{self.client.uname.nodename}{{RESET}} ' \
                            f'{{BOLD_YELLOW}}{{cwd}}{{RESET}}]$ '
        XSH.env['PROMPT_FIELDS']['cwd'] = self._rpc_cwd

    def _rpc_cwd(self, ) -> str:
        with self.client.reconnect_lock:
            return self.client.fs.pwd()

    def _rpc_xattr_get_dict(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='view file xattributes')
        parser.add_argument('filename')
        args = parser.parse_args(args)
        _print_json(self.client.fs.dictxattr(args.filename), file=stdout)

    def _rpc_vim(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='use "vim" to edit the given file')
        parser.add_argument('filename')
        args = parser.parse_args(args)
        with self._edit_remotely(args.filename) as f:
            os.system(f'vim "{f}"')

    def _rpc_entitlements(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='view file entitlements')
        parser.add_argument('filename')
        args = parser.parse_args(args)
        _print_json(self.client.lief.get_entitlements(args.filename), file=stdout)

    def _rpc_list_labels(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='list all labels in current main application')
        parser.parse_args(args)
        for element in self.client.accessibility.primary_app:
            print(element.label, file=stdout, flush=True)

    def _rpc_press_labels(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='press labels list by given order')
        parser.add_argument('label', nargs='+')
        args = parser.parse_args(args)
        self.client.accessibility.press_labels(args.label)

    def _rpc_press_keys(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='press key list by given order')
        parser.add_argument('key', nargs='+')
        args = parser.parse_args(args)
        keys = {
            'power': self.client.hid.send_power_button_press,
            'home': self.client.hid.send_home_button_press,
            'volup': self.client.hid.send_volume_up_button_press,
            'voldown': self.client.hid.send_volume_down_button_press,
            'mute': self.client.hid.send_mute_button_press,
        }
        for k in args.key:
            keys[k]()

    def _rpc_run(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='execute a program')
        parser.add_argument('arg', nargs='+')
        args = parser.parse_args(args)
        if not stdin:
            stdin = sys.stdin
        result = self.client.spawn(args.arg, raw_tty=True, stdin=stdin, stdout=stdout)
        return result.error

    def _rpc_run_async(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='execute a program in background')
        parser.add_argument('arg', nargs='+')
        args = parser.parse_args(args)
        print(self.client.spawn(args.arg, raw_tty=False, background=True), file=stdout, flush=True)

    def _rpc_kill(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='kill a process')
        parser.add_argument('pid', type=int)
        parser.add_argument('signal_number', nargs='?', type=int, default=SIGTERM)
        args = parser.parse_args(args)
        self.client.processes.kill(args.pid, args.signal_number)

    def _rpc_killall(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='killall processes with given basename given as a "contain" expression')
        parser.add_argument('expression')
        parser.add_argument('signal_number', nargs='?', type=int, default=SIGTERM)
        args = parser.parse_args(args)
        for p in self.client.processes.grep(args.expression):
            print(f'killing {p}', file=stdout, flush=True)
            p.kill(args.signal_number)

    def _rpc_ps(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='list processes')
        parser.parse_args(args)
        for p in self.client.processes.list():
            print(f'{p.pid:5} {p.path}', file=stdout, flush=True)

    def _rpc_ls(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='list files')
        parser.add_argument('path', nargs='?', default='.')
        args = parser.parse_args(args)
        for f in self.client.fs.scandir(args.path):
            print(f.name, file=stdout, flush=True)

    def _rpc_ln(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='create a link')
        parser.add_argument('-s', '--symlink', action='store_true')
        parser.add_argument('src')
        parser.add_argument('dst')
        args = parser.parse_args(args)
        if args.symlink:
            self.client.fs.symlink(args.src, args.dst)
        else:
            self.client.fs.link(args.src, args.dst)

    def _rpc_touch(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='create an empty file')
        parser.add_argument('filename')
        args = parser.parse_args(args)
        with self.client.fs.open(args.filename, 'w'):
            pass

    def _rpc_pwd(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='get current working directory')
        parser.parse_args(args)
        print(self.client.fs.pwd(), file=stdout, flush=True)

    @contextual_completer
    def _rpc_cd(self, args, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr):
        parser = ArgumentParser(description='change directory')
        parser.add_argument('path')
        args = parser.parse_args(args)
        self.client.fs.chdir(args.path)

    def _rpc_rm(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='remove list of files')
        parser.add_argument('path', nargs='+')
        parser.add_argument('-r', '--recursive', action='store_true')
        args = parser.parse_args(args)

        for path in args.path:
            if args.recursive:
                for entry in self._find(path):
                    self.client.fs.remove(entry)
            self.client.fs.remove(path)

    def _rpc_mv(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='move a file')
        parser.add_argument('src')
        parser.add_argument('dst')
        args = parser.parse_args(args)
        self.client.fs.rename(args.src, args.dst)

    def _rpc_cp(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='copy a file')
        parser.add_argument('src')
        parser.add_argument('dst')
        args = parser.parse_args(args)
        with self.client.fs.open(args.src, 'r') as src:
            with self.client.fs.open(args.dst, 'w') as dst:
                dst.writeall(src.readall())

    def _rpc_mkdir(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='create a directory')
        parser.add_argument('filename')
        parser.add_argument('-p', '--create-all', action='store_true')
        args = parser.parse_args(args)
        dir_path = Path(self._rpc_cwd())

        if args.create_all:
            for part in Path(args.filename).parts:
                dir_path = dir_path / part
                try:
                    self.client.fs.mkdir(dir_path, mode=0o777)
                except RpcFileExistsError:
                    pass
        else:
            self.client.fs.mkdir(args.filename, mode=0o777)

    def _rpc_cat(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='read a list of files')
        parser.add_argument('filename', nargs='+')
        args = parser.parse_args(args)
        for filename in args.filename:
            with self.client.fs.open(filename, 'r') as f:
                print(f.readall(), file=stdout, end='', flush=True)
        print('', file=stdout, flush=True)

    def _rpc_bat(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='"bat" (improved-cat) given file')
        parser.add_argument('filename')
        args = parser.parse_args(args)
        with self._remote_file(args.filename) as f:
            os.system(f'bat "{f}"')

    def _rpc_pull(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='pull a file from remote')
        parser.add_argument('remote')
        parser.add_argument('local')
        args = parser.parse_args(args)
        return self._pull(args.remote, args.local)

    def _rpc_push(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='push a file into remote')
        parser.add_argument('local')
        parser.add_argument('remote')
        args = parser.parse_args(args)
        return self._push(args.local, args.remote)

    def _rpc_chmod(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='chmod at remote')
        parser.add_argument('mode')
        parser.add_argument('filename')
        args = parser.parse_args(args)
        self.client.fs.chmod(args.filename, int(args.mode, 8))

    def _rpc_find(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='find file recursively')
        parser.add_argument('filename')
        args = parser.parse_args(args)
        for filename in self._find(args.filename):
            print(filename, file=stdout, flush=True)

    def _rpc_plshow(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='parse and show plist')
        parser.add_argument('filename')
        args = parser.parse_args(args)
        with self.client.fs.open(args.filename, 'r') as f:
            _print_json(plistlib.loads(f.readall()), file=stdout)

    def _rpc_record(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='start recording for specified duration')
        parser.add_argument('filename')
        parser.add_argument('duration', type=int)
        args = parser.parse_args(args)
        with self.client.media.get_recorder(args.filename) as r:
            r.record()
            time.sleep(args.duration)
            r.stop()

    def _rpc_play(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='play file')
        parser.add_argument('filename')
        parser.add_argument('duration', type=int, nargs='?')
        args = parser.parse_args(args)
        with self.client.media.get_player(args.filename) as r:
            r.play()
            if args.duration:
                time.sleep(args.duration)
            else:
                while r.playing:
                    time.sleep(.1)

    def _rpc_open(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='open a file from remote using default program')
        parser.add_argument('filename')
        args = parser.parse_args(args)

        open_ = plumbum.local['open']
        with self._edit_remotely(args.filename) as f:
            open_('-W', f)

    def _rpc_date(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='get/set date')
        parser.add_argument('new_date', nargs='?')
        args = parser.parse_args(args)
        if not args:
            print(self.client.time.now(), file=stdout, flush=True)
            return
        self.client.time.set_current(datetime.fromisoformat(args.new_date))

    def _rpc_which(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='traverse $PATH to find the first matching executable')
        parser.add_argument('filename')
        args = parser.parse_args(args)

        for p in self.client.getenv('PATH').split(':'):
            filename = (Path(p) / args.filename).absolute()
            if self.client.fs.accessible((Path(p) / args.filename).absolute()):
                print(filename, flush=True)
                return

    def _rpc_env(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='view all environment variables')
        parser.parse_args(args)

        for e in self.client.environ:
            print(e, file=stdout, flush=True)

    def _rpc_file(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='show file type')
        parser.add_argument('filename')
        args = parser.parse_args(args)

        file = plumbum.local['file']
        with self._remote_file(args.filename) as f:
            file(f, stdout=stdout)

    def _rpc_list_commands(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(description='list all rpc commands')
        parser.parse_args(args)

        for k, v in self._commands.items():
            print(f'👾 {k}', file=stdout, flush=True)

    @contextlib.contextmanager
    def _remote_file(self, remote):
        with tempfile.TemporaryDirectory() as local_dir:
            local = Path(local_dir) / Path(remote).parts[-1]
            if self.client.fs.accessible(remote):
                self._pull(remote, local.absolute())
            try:
                yield local.absolute()
            finally:
                pass

    @contextlib.contextmanager
    def _edit_remotely(self, remote):
        with self._remote_file(remote) as local:
            try:
                yield local
            finally:
                self._push(local, remote)

    def _find(self, path: str):
        for root, dirs, files in self.client.fs.walk(path):
            for name in files:
                yield os.path.join(root, name)
            for name in dirs:
                yield os.path.join(root, name)

    def _listdir(self, path: str) -> List[str]:
        return self.client.fs.listdir(path)

    def _pull(self, remote_filename, local_filename):
        with self.client.fs.open(remote_filename, 'r') as remote_fd:
            with open(local_filename, 'wb') as local_fd:
                local_fd.write(remote_fd.readall())

    def _push(self, local_filename, remote_filename):
        with open(local_filename, 'rb') as from_fd:
            with self.client.fs.open(remote_filename, 'w') as to_fd:
                to_fd.write(from_fd.read())


# actual RC contents
rc = XonshRc()
XSH.env['rpc'] = rc.client

XSH.aliases['xontrib']('load z argcomplete coreutils fzf-widgets jedi'.split())
XSH.env['fzf_history_binding'] = "c-r"  # Ctrl+R
XSH.env['fzf_ssh_binding'] = "c-s"  # Ctrl+S
XSH.env['fzf_file_binding'] = "c-t"  # Ctrl+T
XSH.env['fzf_dir_binding'] = "c-g"  # Ctrl+G
