# Filesystem

The `fs` subsystem (`p.fs`) works with the target's filesystem: listing and walking directories,
reading and writing files, copying files between your machine and the target, and changing
permissions, ownership and links. On Darwin targets it also covers extended attributes, file flags
and `statfs`.

!!! note "Console vs. scripts"
    The examples below are written for the interactive console, where `smart_await` awaits each
    call for you. A console cell that already uses `await`, `async with` or `async for` is left
    as-is, so every call inside such a cell needs an explicit `await`. In scripts, `await` each
    call yourself - see [Scripting with rpcclient](scripting.md).

## Listing and walking directories

```python
p.fs.listdir('/var/mobile/Library/Preferences')     # list of names, without '.' and '..'
p.fs.pwd()
p.fs.chdir('/var/mobile')
```

`scandir()` returns `DirEntry` objects. `name` and `path` are plain properties; `is_dir()`,
`is_file()`, `is_symlink()` and `stat()` are calls:

```python
entries = p.fs.scandir('/var/mobile/Library')
entry = entries[0]
entry.name, entry.path
entry.is_dir()
```

`walk()` mirrors `os.walk()` and `find()` yields every path under a directory. Both are async
generators, so iterate them with `async for` (pass `topdown=False` for a bottom-up traversal):

```python
async for root, dirs, files in p.fs.walk('/var/mobile/Library/Preferences'):
    print(root, len(files))

paths = [path async for path in p.fs.find('/tmp/logs')]
```

## Reading and writing files

For whole files, use `p.fs.write_file('/tmp/hello.txt', b'hello')` and `p.fs.read_file('/tmp/hello.txt')`.

`open(path, mode, access=0o777)` returns a remote `File` wrapping the target's file descriptor.
`mode` is one of `'r'`, `'r+'` (read/write, must exist), `'rw'` (read/write, create and truncate),
`'w'` (write-only, create and truncate) or `'w+'` (read/write, create, no truncate). Use it as an
async context manager so the descriptor is closed:

```python
async with await p.fs.open('/tmp/hello.txt', 'r') as f:
    header = await f.read(4)
    rest = await f.read()
```

Outside a context manager, close it with `deallocate()`:

```python
f = p.fs.open('/tmp/data.bin', 'w+')
f.write(b'\x00' * 16)
f.pwrite(b'ABCD', 8)                                 # write at offset 8
f.pread(4, 8)                                        # b'ABCD'
f.seek(0, 2)                                         # SEEK_END; returns the new offset
f.fsync()
f.deallocate()
```

`File` also provides `tell()`, `fdatasync()`, `flock(operation)` (with `LOCK_*` from
`rpcclient.core.structs.consts`), `dup()` and `parse(struct)` to read and parse a `construct` struct.

## Copying between your machine and the target

`push()` copies local files to the target and `pull()` copies remote files to your machine. Both
accept a single path or a list, and `~` is expanded on each side:

```python
p.fs.push('~/Desktop/config.plist', '/var/mobile/Documents/config.plist')
p.fs.pull('/var/mobile/Library/Preferences/com.apple.springboard.plist', '/tmp/')
p.fs.pull('/var/mobile/Media/DCIM', '/tmp/dcim', recursive=True)
```

Directories are skipped unless `recursive=True`; a copied directory lands inside the destination
as `<dest>/<name>`. Existing destination files are **not** overwritten unless you pass `force=True`.

To edit a remote file with local tools, `remote_file()` pulls it into a local temporary directory,
yields the local `Path`, and pushes it back (with `force=True`) when the block exits:

```python
async with p.fs.remote_file('/var/mobile/Library/Preferences/com.example.app.plist') as local:
    data = local.read_bytes()
    local.write_bytes(data.replace(b'old', b'new'))
```

## Stat, permissions and ownership

```python
st = p.fs.stat('/var/mobile/Documents/notes.txt')    # follows symlinks
st.st_size, oct(st.st_mode), st.st_uid, st.st_mtime
p.fs.lstat('/var/mobile/Documents/link')             # does not follow symlinks
p.fs.is_file('/var/mobile/Documents/notes.txt')
p.fs.accessible('/var/root')                         # access(path, R_OK) == 0
p.fs.realpath('/tmp/../var/mobile')
```

`chmod()` and `chown()` take an optional `recursive=True`, which applies the change to every path
under a directory. Pass `-1` to `chown()` to leave the uid or gid unchanged:

```python
p.fs.chmod('/tmp/tool', 0o755)
p.fs.chown('/var/mobile/Documents/export', 501, 501, recursive=True)
p.fs.chown('/tmp/tool', 0, -1)
```

## Creating, removing and renaming

```python
p.fs.mkdir('/tmp/work/a/b', parents=True)
p.fs.mkdir('/tmp/work', exist_ok=True)
p.fs.touch('/tmp/work/empty.txt')                    # mode=0o666, exist_ok=True
p.fs.rename('/tmp/work/empty.txt', '/tmp/work/a/empty.txt')
p.fs.remove('/tmp/work/a/empty.txt')
p.fs.remove('/tmp/work', recursive=True)             # force=True ignores errors
```

For scratch space, `remote_temp_dir()` creates a uniquely named directory (under `/tmp` by
default) and removes it with its contents when the block exits:

```python
async with await p.fs.remote_temp_dir() as tmp:
    await (tmp / 'out.bin').write_bytes(b'data')
```

## Links

```python
p.fs.symlink('/var/mobile/Documents/notes.txt', '/tmp/notes')   # symlink(target, link)
p.fs.link('/tmp/hello.txt', '/tmp/hello-hardlink.txt')         # hard link
p.fs.is_symlink('/tmp/notes')
p.fs.readlink('/tmp/notes')                    # resolved against the link's directory
p.fs.readlink('/tmp/notes', absolute=False)    # the raw link contents
```

## Remote paths

`remote_path()` returns a `RemotePath`, a `PurePosixPath` bound to the client. Path arithmetic is
local; filesystem methods such as `exists()`, `is_dir()`, `stat()`, `read_bytes()`,
`write_bytes()`, `mkdir()`, `touch()`, `remove()` and `chmod()` run on the target. Any `fs` method
accepts a `RemotePath` wherever it takes a path.

```python
docs = p.fs.remote_path('/var/mobile/Documents')
notes = docs / 'notes.txt'
notes.exists()
notes.read_bytes()
names = [child.name async for child in docs.iterdir()]
```

## Darwin: extended attributes, flags and statfs

```python
path = '/var/mobile/Downloads/app.zip'
p.fs.listxattr(path)                                 # ['com.apple.quarantine', ...]
p.fs.getxattr(path, 'com.apple.quarantine')          # bytes
p.fs.dictxattr(path)                                 # {name: bytes}
p.fs.setxattr(path, 'com.example.tag', b'value')
p.fs.removexattr(path, 'com.apple.quarantine')
```

`chflags()` sets BSD file flags, with constants from `rpcclient.clients.darwin.consts`:

```python
from rpcclient.clients.darwin.consts import UF_IMMUTABLE

p.fs.chflags('/tmp/locked.txt', UF_IMMUTABLE)        # remove() now fails with RpcPermissionError
p.fs.chflags('/tmp/locked.txt', 0)
```

`statfs()` describes the volume a path lives on:

```python
vfs = p.fs.statfs('/var/mobile')
vfs.f_mntonname, vfs.f_fstypename, vfs.f_bavail * vfs.f_bsize
```

See also: [Core API reference](../api/core.md), [Darwin API reference](../api/darwin.md#filesystem),
[Mounting in Finder (WebDAV)](mounting-webdav.md).
