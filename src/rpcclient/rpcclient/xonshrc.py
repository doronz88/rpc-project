import contextlib
import json
import os
import plistlib
import posixpath
import shutil
import sys
import tempfile
import time
from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Union
from uuid import UUID

import plumbum
from click.exceptions import Exit
from humanfriendly.prompts import prompt_for_choice
from prompt_toolkit.keys import Keys
from pygments import formatters, highlight, lexers
from pygnuutils.cli.ls import ls as ls_cli
from pygnuutils.ls import Ls, LsStub
from xonsh.built_ins import XSH
from xonsh.cli_utils import Annotated, Arg, ArgParserAlias
from xonsh.events import events
from xonsh.tools import print_color

import rpcclient
from rpcclient.client_factory import create_client
from rpcclient.exceptions import RpcClientException
from rpcclient.structs.consts import SIGTERM


def _default_json_encoder(obj):
    if isinstance(obj, bytes):
        return obj.hex()
    if isinstance(obj, datetime):
        return str(obj)
    if isinstance(obj, UUID):
        return str(obj)
    raise TypeError()


def _pretty_json(buf, colored=True, default=_default_json_encoder):
    formatted_json = json.dumps(buf, sort_keys=True, indent=4, default=default)
    if colored:
        colorful_json = highlight(formatted_json, lexers.JsonLexer(),
                                  formatters.TerminalTrueColorFormatter(style='stata-dark'))
        return colorful_json
    else:
        return formatted_json


def element_completer(xsh, action, completer, alias, command):
    client = XSH.env['rpc']
    result = []
    if not client.accessibility.enabled:
        return result

    for f in client.accessibility.primary_app:
        result.append(f'"{f.label}"')

    return result


def path_completer(xsh, action, completer, alias, command):
    client = XSH.env['rpc']
    pwd = client.fs.pwd()
    is_absolute = command.prefix.startswith('/')
    dirpath = Path(pwd) / command.prefix
    if not client.fs.accessible(dirpath):
        dirpath = dirpath.parent
    result = []
    for f in client.fs.scandir(dirpath):
        if is_absolute:
            completion_option = str((dirpath / f.name))
        else:
            completion_option = str((dirpath / f.name).relative_to(pwd))
        try:
            if f.is_dir():
                result.append(f'{completion_option}/')
            else:
                result.append(completion_option)
        except RpcClientException:
            result.append(completion_option)

    return result


def dir_completer(xsh, action, completer, alias, command):
    client = XSH.env['rpc']
    pwd = client.fs.pwd()
    is_absolute = command.prefix.startswith('/')
    dirpath = Path(pwd) / command.prefix
    if not client.fs.accessible(dirpath):
        dirpath = dirpath.parent
    result = []
    for f in client.fs.scandir(dirpath):
        if is_absolute:
            completion_option = str((dirpath / f.name))
        else:
            completion_option = str((dirpath / f.name).relative_to(pwd))
        try:
            if f.is_dir():
                result.append(f'{completion_option}/')
        except RpcClientException:
            result.append(completion_option)

    return result


class RpcLsStub(LsStub):
    def __init__(self, client, stdout):
        self._client = client
        self._stdout = stdout
        self._paths_entries = {}

    @property
    def sep(self):
        return posixpath.sep

    def join(self, path, *paths):
        return posixpath.join(path, *paths)

    def abspath(self, path):
        return posixpath.normpath(path)

    def stat(self, path, dir_fd=None, follow_symlinks=True):
        path = Path(path)

        for parent, entries in self._paths_entries.items():
            try:
                Path(path).relative_to(parent)
            except ValueError:
                # if not relative then use stat()
                if follow_symlinks:
                    return self._client.fs.stat(path)
                return self._client.fs.lstat(path)

            # otherwise, search for a cached entry
            for e in entries:
                if e.name == path.parts[-1]:
                    return e.stat(follow_symlinks=follow_symlinks)

        return self._client.fs.lstat(path)

    def readlink(self, path, dir_fd=None):
        return self._client.fs.readlink(path)

    def isabs(self, path):
        return posixpath.isabs(path)

    def dirname(self, path):
        return posixpath.dirname(path)

    def basename(self, path):
        return posixpath.basename(path)

    def getgroup(self, st_gid):
        return str(st_gid)

    def getuser(self, st_uid):
        return str(st_uid)

    def now(self):
        return self._client.time.now()

    def listdir(self, path='.'):
        self._paths_entries[path] = self._client.fs.scandir(path)
        return [e.name for e in self._paths_entries[path]]

    def system(self):
        return 'Darwin'

    def getenv(self, key, default=None):
        return self._client.getenv(key)

    def get_tty_width(self):
        return os.get_terminal_size().columns

    def print(self, *objects, sep=' ', end='\n', file=sys.stdout, flush=False):
        print(objects[0], end=end, file=self._stdout, flush=flush)


class XonshRc:
    def __init__(self):
        self.client: Union[None, rpcclient.client.Client, rpcclient.darwin.client.DarwinClient] = None
        self._commands = {}
        self._orig_aliases = {}
        self._orig_prompt = XSH.env['PROMPT']
        self._register_rpc_command('rpc-connect', self._rpc_connect)
        self._register_rpc_command('rpc-list-commands', self._rpc_list_commands)
        self._rpc_connect()

        print_color('''
        {BOLD_WHITE}Welcome to xonsh-rpc shell! 👋{RESET}
        Use {CYAN}$rpc{RESET} to access current client.
        Use {CYAN}rpc-list-commands{RESET} to view a list of all available special commands.
            These special commands will replace all already existing commands.

        {BOLD_WHITE}Use the following keyboard shortcuts:{RESET}
        * Home: ControlHome
        * Power: ControlEnd
        * VolUp: ControlShiftUp
        * VolDown: ControlShiftDown
        ''')

    def _register_arg_parse_alias(self, name: str, handler: Union[Callable, str]):
        handler = ArgParserAlias(func=handler, has_args=True, prog=name)
        self._commands[name] = handler
        if XSH.aliases.get(name):
            self._orig_aliases[name] = XSH.aliases[name]
        XSH.aliases[name] = handler

    def _register_rpc_command(self, name, handler):
        self._commands[name] = handler
        if XSH.aliases.get(name):
            self._orig_aliases[name] = XSH.aliases[name]
        XSH.aliases[name] = handler

    def _rpc_disconnect(self, args, stdin, stdout, stderr):
        self.client.close()
        for k, v in self._orig_aliases.items():
            XSH.aliases[k] = v

    def _rpc_connect(self):
        """
        connect to remote rpcserver
        """
        self.client = create_client(XSH.ctx['_create_socket_cb'])

        # clear all host commands except for some useful ones
        XSH.env['PATH'].clear()
        for cmd in ['wc', 'grep', 'egrep', 'sed', 'awk', 'print', 'yes', 'cat', 'file']:
            executable = shutil.which(cmd)
            if executable is not None:
                self._register_rpc_command(cmd.strip(), executable)

        # -- rpc
        self._register_arg_parse_alias('rpc-disconnect', self._rpc_disconnect)
        self._register_arg_parse_alias('rpc-which', self._rpc_which)

        # -- automation
        self._register_arg_parse_alias('list-elements', self._rpc_list_elements)
        self._register_arg_parse_alias('press-elements', self._rpc_press_elements)
        self._register_arg_parse_alias('enable-accessibility', self._rpc_enable_accessibility)
        self._register_arg_parse_alias('disable-accessibility', self._rpc_disable_accessibility)
        self._register_arg_parse_alias('press-keys', self._rpc_press_keys)
        self._register_arg_parse_alias('swipe-up', self._rpc_swipe_up)
        self._register_arg_parse_alias('swipe-down', self._rpc_swipe_down)
        self._register_arg_parse_alias('swipe-left', self._rpc_swipe_left)
        self._register_arg_parse_alias('swipe-right', self._rpc_swipe_right)

        # -- processes
        self._register_rpc_command('run', self._rpc_run)
        self._register_rpc_command('run-async', self._rpc_run_async)
        if self.client.fs.accessible('/bin/ps'):
            XSH.aliases['ps'] = 'run ps'
        else:
            self._register_arg_parse_alias('ps', self._rpc_ps)
        self._register_arg_parse_alias('kill', self._rpc_kill)
        self._register_arg_parse_alias('killall', self._rpc_killall)

        # -- fs
        self._register_rpc_command('ls', self._rpc_ls)
        self._register_arg_parse_alias('ln', self._rpc_ln)
        self._register_arg_parse_alias('touch', self._rpc_touch)
        self._register_arg_parse_alias('pwd', self._rpc_pwd)
        self._register_arg_parse_alias('cd', self._rpc_cd)
        self._register_arg_parse_alias('rm', self._rpc_rm)
        self._register_arg_parse_alias('mv', self._rpc_mv)
        self._register_arg_parse_alias('cp', self._rpc_cp)
        self._register_arg_parse_alias('mkdir', self._rpc_mkdir)
        self._register_arg_parse_alias('cat', self._rpc_cat)
        self._register_arg_parse_alias('bat', self._rpc_bat)
        self._register_arg_parse_alias('pull', self._rpc_pull)
        self._register_arg_parse_alias('push', self._rpc_push)
        self._register_arg_parse_alias('chmod', self._rpc_chmod)
        self._register_arg_parse_alias('chown', self._rpc_chown)
        self._register_arg_parse_alias('find', self._rpc_find)
        self._register_arg_parse_alias('xattr-get-dict', self._rpc_xattr_get_dict)
        self._register_arg_parse_alias('vim', self._rpc_vim)
        self._register_arg_parse_alias('entitlements', self._rpc_entitlements)

        # -- plist
        self._register_arg_parse_alias('plshow', self._rpc_plshow)

        # -- media
        self._register_arg_parse_alias('record', self._rpc_record)
        self._register_arg_parse_alias('play', self._rpc_play)

        # -- misc
        self._register_arg_parse_alias('open', self._rpc_open)
        self._register_arg_parse_alias('date', self._rpc_date)
        self._register_arg_parse_alias('env', self._rpc_env)
        self._register_arg_parse_alias('rpc-file', self._rpc_file)

        XSH.env['PROMPT'] = f'[{{BOLD_GREEN}}{self.client.uname.nodename}{{RESET}} ' \
                            f'{{BOLD_YELLOW}}{{rpc_cwd}}{{RESET}}]{{prompt_end}} '
        XSH.env['PROMPT_FIELDS']['rpc_cwd'] = self._rpc_cwd
        XSH.env['PROMPT_FIELDS']['prompt_end'] = self._prompt

    def _prompt(self) -> str:
        if len(XSH.history) == 0 or XSH.history[-1].rtn == 0:
            return '{BOLD_GREEN}${RESET}'
        return '{BOLD_RED}${RESET}'

    def _rpc_cwd(self) -> str:
        with self.client.reconnect_lock:
            return self.client.fs.pwd()

    def _rpc_xattr_get_dict(self, filename: Annotated[str, Arg(completer=path_completer)]):
        """
        view file xattributes
        """
        return _pretty_json(self.client.fs.dictxattr(filename))

    def _rpc_vim(self, filename: Annotated[str, Arg(completer=path_completer)]):
        """
        use "vim" to edit the given file
        """
        with self._edit_remotely(filename) as f:
            os.system(f'vim "{f}"')
            self._push(f, filename)

    def _rpc_entitlements(self, filename: Annotated[str, Arg(completer=path_completer)]):
        """
        view file entitlements
        """
        return _pretty_json(self.client.lief.get_entitlements(filename))

    def _rpc_list_elements(self):
        """
        list all labels in current main application')
        """
        for element in self.client.accessibility.primary_app:
            print_color(f'🏷  '
                        f'{{BOLD_WHITE}}Label:{{RESET}} {element.label} '
                        f'{{BOLD_WHITE}}Value:{{RESET}} {element.value} '
                        f'{{RESET}}',
                        file=sys.stdout)

    def _rpc_press_elements(self, label: Annotated[List[str], Arg(nargs='+', completer=element_completer)]):
        """
        press labels list by given order
        """
        self.client.accessibility.press_elements_by_labels(label)

    def _rpc_enable_accessibility(self):
        """
        enable accessibility features
        """
        self.client.accessibility.enabled = True

    def _rpc_disable_accessibility(self):
        """
        disable accessibility features
        """
        self.client.accessibility.enabled = False

    def _rpc_press_keys(self, key: Annotated[
        List[str], Arg(nargs='+',
                       completer=lambda xsh, action, completer, alias, command: ['power', 'home', 'volup', 'voldown',
                                                                                 'mute'])]):
        """
        press key list by given order
        """
        keys_map = {
            'power': self.client.hid.send_power_button_press,
            'home': self.client.hid.send_home_button_press,
            'volup': self.client.hid.send_volume_up_button_press,
            'voldown': self.client.hid.send_volume_down_button_press,
            'mute': self.client.hid.send_mute_button_press,
        }
        for k in key:
            keys_map[k]()

    def _rpc_swipe_up(self):
        """
        swipe up
        """
        self.client.hid.send_swipe_up()

    def _rpc_swipe_down(self):
        """
        swipe down
        """
        self.client.hid.send_swipe_down()

    def _rpc_swipe_left(self):
        """
        swipe left
        """
        self.client.hid.send_swipe_left()

    def _rpc_swipe_right(self):
        """
        swipe right
        """
        self.client.hid.send_swipe_right()

    def _rpc_run(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(prog='run', description='execute a program')
        parser.add_argument('arg', nargs='+')
        args = parser.parse_args(args)
        if not stdin:
            stdin = sys.stdin
        result = self.client.spawn(args.arg, raw_tty=True, stdin=stdin, stdout=stdout)
        return result.error

    def _rpc_run_async(self, args, stdin, stdout, stderr):
        parser = ArgumentParser(prog='run-async', description='execute a program in background')
        parser.add_argument('arg', nargs='+')
        args = parser.parse_args(args)
        print(self.client.spawn(args.arg, raw_tty=False, background=True), file=stdout, flush=True)

    def _rpc_kill(self, pid: int, signal_number: Annotated[int, Arg(nargs='?', default=SIGTERM)]):
        """
        kill a process
        """
        signal_number = int(signal_number)
        pid = int(pid)
        self.client.processes.kill(pid, signal_number)

    def _rpc_killall(self, expression: str, signal_number: Annotated[int, Arg(nargs='?', default=SIGTERM)]):
        """
        killall processes with given basename given as a "contain" expression
        """
        signal_number = int(signal_number)
        for p in self.client.processes.grep(expression):
            p.kill(signal_number)

    def _rpc_ps(self):
        """ list processes """
        for p in self.client.processes.list():
            print_color(f'{p.pid:5} {p.path}', file=sys.stdout, flush=True)

    def _rpc_ls(self, args, stdin, stdout, stderr):
        """ list files """
        try:
            with ls_cli.make_context('ls', args) as ctx:
                files = list(map(self._relative_path, ctx.params.pop('files')))
                files = files if files else [self._rpc_pwd()]
                Ls(RpcLsStub(self.client, stdout))(*files, **ctx.params)
        except Exit:
            pass

    def _rpc_ln(self, src: Annotated[str, Arg(completer=path_completer)],
                dst: Annotated[str, Arg(completer=path_completer)], symlink=False):
        """
        create a link

        Parameters
        ----------
        symlink : -s, --symlink
            create a symlink instead of a hard link
        """
        if symlink:
            self.client.fs.symlink(src, dst)
        else:
            self.client.fs.link(src, dst)

    def _rpc_touch(self, filename: Annotated[str, Arg(completer=path_completer)]):
        """
        create an empty file
        """
        self.client.fs.write_file(filename, b'')

    def _rpc_pwd(self):
        """
        get current working directory
        """
        return self.client.fs.pwd()

    def _rpc_cd(self, path: Annotated[str, Arg(completer=dir_completer)]):
        """
        change directory
        """
        self.client.fs.chdir(path)

    def _rpc_rm(self, path: Annotated[List[str], Arg(nargs='+', completer=path_completer)], recursive=False,
                force=False):
        """
        remove files

        Parameters
        ----------
        recursive : -r, --recursive
            remove recursively
        force : -f, --force
            ignore errors
        """
        for p in path:
            self.client.fs.remove(p, recursive=recursive, force=force)

    def _rpc_mv(self, src: Annotated[str, Arg(completer=path_completer)],
                dst: Annotated[str, Arg(completer=path_completer)]):
        """
        move a file
        """
        self.client.fs.rename(src, dst)

    def _rpc_cp(self, src: Annotated[str, Arg(completer=path_completer)],
                dst: Annotated[str, Arg(completer=path_completer)]):
        """
        copy a file
        """
        self.client.fs.write_file(dst, self.client.fs.read_file(src))

    def _rpc_mkdir(self, filename: Annotated[str, Arg(completer=path_completer)], parents: bool = False,
                   mode: Annotated[str, Arg(nargs='?')] = '777'):
        """
        create a directory

        Parameters
        ----------
        parents : -p, --parents
            Create intermediate directories as required.
        """
        self.client.fs.mkdir(filename, mode=int(mode, 8), parents=parents)

    def _rpc_cat(self, filename: Annotated[List[str], Arg(nargs='+', completer=path_completer)]):
        """
        read a list of files
        """
        buf = b''
        for current in filename:
            with self.client.fs.open(current, 'r') as f:
                buf += f.read()
        buf += b'\n'
        try:
            return buf.decode()
        except UnicodeDecodeError:
            return str(buf)

    def _rpc_bat(self, filename: Annotated[List[str], Arg(completer=path_completer)]):
        """
        "bat" (improved-cat) given file
        """
        with self._remote_file(filename) as f:
            os.system(f'bat "{f}"')

    def _rpc_pull(self, remote: Annotated[str, Arg(completer=path_completer)], local: str):
        """
        pull a file from remote
        """
        return self._pull(remote, local)

    def _rpc_push(self, local: str, remote: Annotated[str, Arg(completer=path_completer)]):
        """
        push a file into remote
        """
        return self._push(local, remote)

    def _rpc_chmod(self, mode: str, filename: Annotated[str, Arg(completer=path_completer)], recursive=False):
        """
        chmod at remote

        Parameters
        ----------
        recursive : -R, --recursive
            remove recursively
        """
        self.client.fs.chmod(filename, int(mode, 8), recursive=recursive)

    def _rpc_chown(self, uid: int, gid: int, filename: Annotated[str, Arg(completer=path_completer)], recursive=False):
        """
        chown at remote

        Parameters
        ----------
        recursive : -r, --recursive
            remove recursively
        """
        uid = int(uid)
        gid = int(gid)
        self.client.fs.chown(filename, uid, gid, recursive=recursive)

    def _rpc_find(self, filename: Annotated[str, Arg(completer=path_completer)], depth=True):
        """ find file recursively """
        for f in self.client.fs.find(filename, topdown=not depth):
            print_color(f, file=sys.stdout, flush=True)

    def _rpc_plshow(self, filename: Annotated[str, Arg(completer=path_completer)]):
        """
        parse and show plist
        """
        with self.client.fs.open(filename, 'r') as f:
            return _pretty_json(plistlib.loads(f.read()))

    def _rpc_record(self, filename: Annotated[str, Arg(completer=path_completer)], duration: int):
        """
        start recording for specified duration
        """
        duration = int(duration)
        with self.client.media.get_recorder(filename) as r:
            r.record()
            time.sleep(duration)
            r.stop()

    def _rpc_play(self, filename: Annotated[str, Arg(completer=path_completer)],
                  duration: Annotated[int, Arg(nargs='?')] = None):
        """
        play file
        """
        with self.client.media.get_player(filename) as r:
            r.play()
            if duration:
                duration = int(duration)
                time.sleep(duration)
            else:
                while r.playing:
                    time.sleep(.1)

    def _rpc_open(self, filename: Annotated[str, Arg(completer=path_completer)]):
        """
        open a file from remote using default program')
        """
        open_ = plumbum.local['open']
        upload_changes = 'Upload changes'
        discard_changes = 'Discard changes'
        with self._edit_remotely(filename) as f:
            open_(f)
            if prompt_for_choice([upload_changes, discard_changes]) == upload_changes:
                self._push(f, filename)

    def _rpc_date(self, new_date: Annotated[str, Arg(nargs='?')] = None):
        """
        get/set date
        """
        if not new_date:
            return self.client.time.now()
        self.client.time.set_current(datetime.fromisoformat(new_date))

    def _rpc_which(self, filename: str):
        """ traverse $PATH to find the first matching executable """
        for p in self.client.getenv('PATH').split(':'):
            abs_filename = (Path(p) / filename).absolute()
            if self.client.fs.accessible((Path(p) / filename).absolute()):
                return abs_filename

    def _rpc_env(self):
        """
        view all environment variables
        """
        return '\n'.join(self.client.environ)

    def _rpc_file(self, filename: str):
        """
        show file type
        """
        file = plumbum.local['file']
        with self._remote_file(filename) as f:
            return file(f)

    def _rpc_list_commands(self):
        """
        list all rpc commands
        """
        buf = ''
        for k, v in self._commands.items():
            buf += f'👾 {k}\n'
        print(buf)

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
            yield local

    def _relative_path(self, filename):
        return posixpath.join(self._rpc_pwd(), filename)

    def _listdir(self, path: str) -> List[str]:
        return self.client.fs.listdir(path)

    def _pull(self, remote_filename, local_filename):
        self.client.fs.pull(remote_filename, local_filename, onerror=lambda x: None)

    def _push(self, local_filename, remote_filename):
        self.client.fs.push(local_filename, remote_filename, onerror=lambda x: None)


# actual RC contents
XSH.aliases['xontrib']('load z argcomplete coreutils fzf-widgets jedi'.split())
XSH.env['fzf_history_binding'] = ""  # Ctrl+R
XSH.env['fzf_ssh_binding'] = ""  # Ctrl+S
XSH.env['fzf_file_binding'] = ""  # Ctrl+T
XSH.env['fzf_dir_binding'] = ""  # Ctrl+G

rc = XonshRc()
XSH.env['rpc'] = rc.client


@events.on_ptk_create
def custom_keybindings(bindings, **kw):
    @bindings.add(Keys.ControlHome)
    def press_home(event):
        XSH.env['rpc'].hid.send_home_button_press()

    @bindings.add(Keys.ControlEnd)
    def press_power(event):
        XSH.env['rpc'].hid.send_power_button_press()

    @bindings.add(Keys.ControlShiftUp)
    def press_volume_up(event):
        XSH.env['rpc'].hid.send_volume_down_button_press()

    @bindings.add(Keys.ControlShiftDown)
    def press_volume_down(event):
        XSH.env['rpc'].hid.send_volume_up_button_press()
