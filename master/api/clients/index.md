# Platform clients

Each platform exposes a concrete `Client` built on top of `CoreClient`.

## Linux

## rpcclient.clients.linux.client

## macOS

## rpcclient.clients.macos.client

### MacosClient

Bases: `DarwinClient[DarwinSymbolT_co]`

Source code in `src/rpcclient/rpcclient/clients/macos/client.py`

```
class MacosClient(DarwinClient[DarwinSymbolT_co]):
    @subsystem
    def reports(self) -> Reports:
        return Reports(self, CRASH_REPORTS_DIR)

    @subsystem
    def apple_script(self) -> AppleScript[DarwinSymbolT_co]:
        return AppleScript(self)

    async def roots(self) -> list[str]:
        """get a list of all accessible darwin roots when used for lookup of files/preferences/..."""

        result = await super().roots()
        for username in await self.fs.scandir("/Users"):
            if not await username.is_dir() or not await self.fs.accessible(username.path):
                continue
            result.append(username.path)
        return result
```

#### roots

```
roots() -> list[str]
```

get a list of all accessible darwin roots when used for lookup of files/preferences/...

Source code in `src/rpcclient/rpcclient/clients/macos/client.py`

```
async def roots(self) -> list[str]:
    """get a list of all accessible darwin roots when used for lookup of files/preferences/..."""

    result = await super().roots()
    for username in await self.fs.scandir("/Users"):
        if not await username.is_dir() or not await self.fs.accessible(username.path):
            continue
        result.append(username.path)
    return result
```

## Darwin (shared macOS/iOS base)

## rpcclient.clients.darwin.client

### DarwinClient

Bases: `CoreClient[DarwinSymbolT_co]`

Source code in `src/rpcclient/rpcclient/clients/darwin/client.py`

```
class DarwinClient(CoreClient[DarwinSymbolT_co]):
    loaded_objc_classes: list
    _NSPropertyListSerialization: DarwinSymbolT_co
    _CFNullTypeID: object

    def __init__(self, bridge: RpcBridge) -> None:
        super().__init__(bridge, RTLD_GLOBAL)
        self._objc_class_cache: dict[str, objective_c_class.Class[DarwinSymbolT_co]] = {}

    def symbol(self, symbol: int) -> DarwinSymbolT_co:
        return cast(DarwinSymbolT_co, DarwinSymbol(symbol, self))

    @classmethod
    async def create(cls, bridge: RpcBridge) -> Self:
        self = cls(bridge)
        if (
            await self.dlopen(
                "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation",
                RTLD_NOW,
            )
            == 0
        ):
            raise MissingLibraryError("failed to load CoreFoundation")

        self.loaded_objc_classes = []
        self._NSPropertyListSerialization = await self.symbols.objc_getClass("NSPropertyListSerialization")
        self._CFNullTypeID = await self.symbols.CFNullGetTypeID()

        return self

    @subsystem
    def biome(self) -> Biome[DarwinSymbolT_co]:
        return Biome(self)

    @subsystem
    def duet(self) -> Duet[DarwinSymbolT_co]:
        return Duet(self)

    @subsystem
    def fs(self) -> DarwinFs[DarwinSymbolT_co]:
        return DarwinFs(self)

    @subsystem
    def preferences(self) -> Preferences[DarwinSymbolT_co]:
        return Preferences(self)

    @subsystem
    def processes(self) -> DarwinProcesses[DarwinSymbolT_co]:
        return DarwinProcesses(self)

    @subsystem
    def media(self) -> DarwinMedia[DarwinSymbolT_co]:
        return DarwinMedia(self)

    @subsystem
    def ioregistry(self) -> IORegistry[DarwinSymbolT_co]:
        return IORegistry(self)

    @subsystem
    def xpc(self) -> Xpc[DarwinSymbolT_co]:
        return Xpc(self)

    @subsystem
    def syslog(self) -> Syslog[DarwinSymbolT_co]:
        return Syslog(self)

    @subsystem
    def time(self) -> Time[DarwinSymbolT_co]:
        return Time(self)

    @subsystem
    def hid(self) -> Hid[DarwinSymbolT_co]:
        return Hid(self)

    @subsystem
    def lief(self) -> DarwinLief[DarwinSymbolT_co]:
        return DarwinLief(self)

    @subsystem
    def bluetooth(self) -> Bluetooth[DarwinSymbolT_co]:
        return Bluetooth(self)

    @subsystem
    def core_graphics(self) -> CoreGraphics[DarwinSymbolT_co]:
        return CoreGraphics(self)

    @subsystem
    def keychain(self) -> Keychain[DarwinSymbolT_co]:
        return Keychain(self)

    @subsystem
    def network(self) -> DarwinNetwork[DarwinSymbolT_co]:
        return DarwinNetwork(self)

    @subsystem
    def dns(self) -> Dns[DarwinSymbolT_co]:
        return Dns(self)

    @subsystem
    def power(self) -> Power[DarwinSymbolT_co]:
        return Power(self)

    @subsystem
    def location(self) -> Location[DarwinSymbolT_co]:
        return Location(self)

    async def get_images(self) -> list[DyldImage]:
        m = []
        for i in range(await self.symbols._dyld_image_count()):
            module_name = await (await self.symbols._dyld_get_image_name(i)).peek_str()
            base_address = await self.symbols._dyld_get_image_header(i)
            m.append(DyldImage(module_name, base_address))
        return m

    async def images(self) -> list[DyldImage]:
        return await self.get_images()

    @cached_async_method
    async def get_uname(self) -> Container:
        async with self.safe_calloc(utsname.sizeof()) as uname:
            assert await self.symbols.uname(uname) == 0
            return await uname.parse(utsname)

    async def is_idevice(self) -> bool:
        return (await self.get_uname()).machine.startswith("i")

    async def roots(self) -> list[str]:
        """get a list of all accessible darwin roots when used for lookup of files/preferences/..."""
        return ["/", "/var/root"]

    async def showobject(self, object_address: int) -> dict:
        return json.loads((await self.rpc_call(MsgId.REQ_SHOW_OBJECT, address=object_address)).description)

    async def showclass(self, class_address: int) -> dict:
        return json.loads((await self.rpc_call(MsgId.REQ_SHOW_CLASS, address=class_address)).description)

    async def get_class_list(self) -> dict[str, objective_c_class.Class]:
        ret = await self.rpc_call(MsgId.REQ_GET_CLASS_LIST)
        result = {}
        for _class in ret.classes:
            result[_class.name] = objective_c_class.Class(self, self.symbol(_class.address), lazy=True)
        return result

    async def decode_cf(self, symbol: int) -> CfSerializable:
        if await self.symbols.CFGetTypeID(symbol) == self._CFNullTypeID:
            return None

        async with self.safe_malloc(8) as p_error:
            await p_error.setindex(0, 0)
            objc_data = await self._NSPropertyListSerialization.objc_call(
                "dataWithPropertyList:format:options:error:",
                symbol,
                CFPropertyListFormat.kCFPropertyListBinaryFormat_v1_0,
                0,
                p_error,
            )
            if await p_error.getindex(0) != 0:
                raise CfSerializationError()
        if objc_data == 0:
            return None
        count = await self.symbols.CFDataGetLength(objc_data)
        async with self.safe_malloc(count) as buf:
            await self.symbols.CFDataGetBytes(objc_data, 0, count, buf)
            result = plistlib.loads(await buf.peek(count))
        await objc_data.objc_call("release")
        return result

    async def cf(self, o: CfSerializable) -> DarwinSymbolT_co:
        """construct a CFObject from a given python object"""
        if o is None:
            return await self.symbols.kCFNull.getindex(0)

        plist_bytes = plistlib.dumps(o, fmt=plistlib.FMT_BINARY)
        plist_objc_bytes = await self.symbols.CFDataCreate(kCFAllocatorDefault, plist_bytes, len(plist_bytes))
        async with self.safe_malloc(8) as p_error:
            await p_error.setindex(0, 0)
            result = await self._NSPropertyListSerialization.objc_call(
                "propertyListWithData:options:format:error:",
                plist_objc_bytes,
                CFPropertyListMutabilityOptions.kCFPropertyListMutableContainersAndLeaves,
                0,
                p_error,
            )
            if await p_error.getindex(0) != 0:
                raise CfSerializationError()
            return result

    def objc_symbol(self, address) -> ObjectiveCSymbol[DarwinSymbolT_co]:
        """
        Get objc symbol wrapper for given address
        :param address:
        :return: ObjectiveC symbol object
        """
        return ObjectiveCSymbol(int(address), self)

    async def objc_get_class(self, name: str) -> objective_c_class.Class[DarwinSymbolT_co]:
        """
        Get ObjC class object
        :param name:
        :return:
        """
        if name not in self._objc_class_cache:
            self._objc_class_cache[name] = await objective_c_class.Class.from_class_name(self, name)

        return self._objc_class_cache[name]

    def objc_get_class_lazy(self, name: str) -> "LazyObjectiveCClassSymbol[DarwinSymbolT_co]":
        return LazyObjectiveCClassSymbol(self, name)

    async def is_objc_type(self, symbol: DarwinSymbol) -> bool:
        """
        Test if a given symbol represents an objc object
        :param symbol:
        :return:
        """
        class_info = await (await self.processes.get_self()).get_symbol_class_info(symbol)
        if class_info == 0:
            return False
        return await (await class_info.objc_call("typeName")).py() == "ObjC"

    async def rebind_symbols(self, populate_global_scope: bool = True) -> None:
        ip = get_ipython()
        if ip is None:
            raise RuntimeError("ipython is not running")
        logger.debug("rebinding symbols")
        self.loaded_objc_classes.clear()

        # enumerate all loaded objc classes
        for name, class_ in (await self.get_class_list()).items():
            self.loaded_objc_classes.append(name)
            if populate_global_scope:
                ip.user_ns[name] = class_

    async def load_framework(self, name: str) -> None:
        lib = await self.dlopen(f"{FRAMEWORKS_PATH}/{name}.framework/{name}", RTLD_NOW)
        if lib == 0:
            lib = await self.dlopen(f"{PRIVATE_FRAMEWORKS_PATH}/{name}.framework/{name}", RTLD_NOW)
        if lib == 0:
            raise MissingLibraryError(f"failed to load {name}")

    def load_framework_lazy(self, name: str) -> None:
        """Register a framework to be loaded at the beginning of the next RPC call operation."""
        self.pre_rpc_call_hooks.append(partial(self.load_framework, name=name))

    async def load_all_libraries(self, rebind_symbols: bool = True) -> None:
        logger.debug(f"loading frameworks: {FRAMEWORKS_PATH}")
        await self._load_frameworks(FRAMEWORKS_PATH)
        logger.debug(f"loading frameworks: {PRIVATE_FRAMEWORKS_PATH}")
        await self._load_frameworks(PRIVATE_FRAMEWORKS_PATH)

        logger.debug(f"loading libraries: {LIB_PATH}")
        for filename in tqdm(await self.fs.listdir(LIB_PATH)):
            if not filename.endswith(".dylib"):
                continue
            await self.dlopen(f"{LIB_PATH}/{filename}", RTLD_NOW)

        if rebind_symbols:
            await self.rebind_symbols()

    async def _load_frameworks(self, frameworks_path: str) -> None:
        for filename in tqdm(await self.fs.listdir(frameworks_path)):
            if filename in FRAMEWORKS_BLACKLIST:
                continue
            if "SpringBoard" in filename or "UI" in filename:
                continue
            await self.dlopen(f"{frameworks_path}/{filename}/{filename.split('.', 1)[0]}", RTLD_NOW)

    async def create_autorelease_pool_ctx(self) -> autorelease_pool.AutorelesePoolCtx:
        """
        Create `AutoreleasePoolCtx` representing an Objective-C `NSAutoreleasePool`.
        Automatically initialize the new pool, can be used with `with` to
        manage a section which would be drained after exiting.

        :return: `AutorelesePoolCtx`
        """
        return autorelease_pool.AutorelesePoolCtx(self)

    async def get_autorelease_pools(self) -> list[autorelease_pool.AutoreleasePool]:
        """
        Get all autorelease pools currently in the thread.

        :return: List of `AutoreleasePool` instances found in the dump
        """
        return await autorelease_pool.get_autorelease_pools(self)

    async def get_current_autorelease_pool(self) -> autorelease_pool.AutoreleasePool:
        """
        Get the most recently created autorelease pool.

        :return: The last `AutoreleasePool` in the list (most recent)
        :raises IndexError: if no pools are found
        """
        return await autorelease_pool.get_current_autorelease_pool(self)
```

#### roots

```
roots() -> list[str]
```

get a list of all accessible darwin roots when used for lookup of files/preferences/...

Source code in `src/rpcclient/rpcclient/clients/darwin/client.py`

```
async def roots(self) -> list[str]:
    """get a list of all accessible darwin roots when used for lookup of files/preferences/..."""
    return ["/", "/var/root"]
```

#### cf

```
cf(o: CfSerializable) -> DarwinSymbolT_co
```

construct a CFObject from a given python object

Source code in `src/rpcclient/rpcclient/clients/darwin/client.py`

```
async def cf(self, o: CfSerializable) -> DarwinSymbolT_co:
    """construct a CFObject from a given python object"""
    if o is None:
        return await self.symbols.kCFNull.getindex(0)

    plist_bytes = plistlib.dumps(o, fmt=plistlib.FMT_BINARY)
    plist_objc_bytes = await self.symbols.CFDataCreate(kCFAllocatorDefault, plist_bytes, len(plist_bytes))
    async with self.safe_malloc(8) as p_error:
        await p_error.setindex(0, 0)
        result = await self._NSPropertyListSerialization.objc_call(
            "propertyListWithData:options:format:error:",
            plist_objc_bytes,
            CFPropertyListMutabilityOptions.kCFPropertyListMutableContainersAndLeaves,
            0,
            p_error,
        )
        if await p_error.getindex(0) != 0:
            raise CfSerializationError()
        return result
```

#### objc_symbol

```
objc_symbol(address) -> ObjectiveCSymbol[DarwinSymbolT_co]
```

Get objc symbol wrapper for given address

Parameters:

| Name      | Type | Description | Default    |
| --------- | ---- | ----------- | ---------- |
| `address` |      |             | *required* |

Returns:

| Type                                 | Description              |
| ------------------------------------ | ------------------------ |
| `ObjectiveCSymbol[DarwinSymbolT_co]` | ObjectiveC symbol object |

Source code in `src/rpcclient/rpcclient/clients/darwin/client.py`

```
def objc_symbol(self, address) -> ObjectiveCSymbol[DarwinSymbolT_co]:
    """
    Get objc symbol wrapper for given address
    :param address:
    :return: ObjectiveC symbol object
    """
    return ObjectiveCSymbol(int(address), self)
```

#### objc_get_class

```
objc_get_class(name: str) -> objective_c_class.Class[DarwinSymbolT_co]
```

Get ObjC class object

Parameters:

| Name   | Type  | Description | Default    |
| ------ | ----- | ----------- | ---------- |
| `name` | `str` |             | *required* |

Returns:

| Type                      | Description |
| ------------------------- | ----------- |
| `Class[DarwinSymbolT_co]` |             |

Source code in `src/rpcclient/rpcclient/clients/darwin/client.py`

```
async def objc_get_class(self, name: str) -> objective_c_class.Class[DarwinSymbolT_co]:
    """
    Get ObjC class object
    :param name:
    :return:
    """
    if name not in self._objc_class_cache:
        self._objc_class_cache[name] = await objective_c_class.Class.from_class_name(self, name)

    return self._objc_class_cache[name]
```

#### is_objc_type

```
is_objc_type(symbol: DarwinSymbol) -> bool
```

Test if a given symbol represents an objc object

Parameters:

| Name     | Type           | Description | Default    |
| -------- | -------------- | ----------- | ---------- |
| `symbol` | `DarwinSymbol` |             | *required* |

Returns:

| Type   | Description |
| ------ | ----------- |
| `bool` |             |

Source code in `src/rpcclient/rpcclient/clients/darwin/client.py`

```
async def is_objc_type(self, symbol: DarwinSymbol) -> bool:
    """
    Test if a given symbol represents an objc object
    :param symbol:
    :return:
    """
    class_info = await (await self.processes.get_self()).get_symbol_class_info(symbol)
    if class_info == 0:
        return False
    return await (await class_info.objc_call("typeName")).py() == "ObjC"
```

#### load_framework_lazy

```
load_framework_lazy(name: str) -> None
```

Register a framework to be loaded at the beginning of the next RPC call operation.

Source code in `src/rpcclient/rpcclient/clients/darwin/client.py`

```
def load_framework_lazy(self, name: str) -> None:
    """Register a framework to be loaded at the beginning of the next RPC call operation."""
    self.pre_rpc_call_hooks.append(partial(self.load_framework, name=name))
```

#### create_autorelease_pool_ctx

```
create_autorelease_pool_ctx() -> autorelease_pool.AutorelesePoolCtx
```

Create `AutoreleasePoolCtx` representing an Objective-C `NSAutoreleasePool`. Automatically initialize the new pool, can be used with `with` to manage a section which would be drained after exiting.

Returns:

| Type                | Description       |
| ------------------- | ----------------- |
| `AutorelesePoolCtx` | AutorelesePoolCtx |

Source code in `src/rpcclient/rpcclient/clients/darwin/client.py`

```
async def create_autorelease_pool_ctx(self) -> autorelease_pool.AutorelesePoolCtx:
    """
    Create `AutoreleasePoolCtx` representing an Objective-C `NSAutoreleasePool`.
    Automatically initialize the new pool, can be used with `with` to
    manage a section which would be drained after exiting.

    :return: `AutorelesePoolCtx`
    """
    return autorelease_pool.AutorelesePoolCtx(self)
```

#### get_autorelease_pools

```
get_autorelease_pools() -> list[autorelease_pool.AutoreleasePool]
```

Get all autorelease pools currently in the thread.

Returns:

| Type                    | Description                                         |
| ----------------------- | --------------------------------------------------- |
| `list[AutoreleasePool]` | List of AutoreleasePool instances found in the dump |

Source code in `src/rpcclient/rpcclient/clients/darwin/client.py`

```
async def get_autorelease_pools(self) -> list[autorelease_pool.AutoreleasePool]:
    """
    Get all autorelease pools currently in the thread.

    :return: List of `AutoreleasePool` instances found in the dump
    """
    return await autorelease_pool.get_autorelease_pools(self)
```

#### get_current_autorelease_pool

```
get_current_autorelease_pool() -> autorelease_pool.AutoreleasePool
```

Get the most recently created autorelease pool.

Returns:

| Type              | Description                                        |
| ----------------- | -------------------------------------------------- |
| `AutoreleasePool` | The last AutoreleasePool in the list (most recent) |

Raises:

| Type         | Description           |
| ------------ | --------------------- |
| `IndexError` | if no pools are found |

Source code in `src/rpcclient/rpcclient/clients/darwin/client.py`

```
async def get_current_autorelease_pool(self) -> autorelease_pool.AutoreleasePool:
    """
    Get the most recently created autorelease pool.

    :return: The last `AutoreleasePool` in the list (most recent)
    :raises IndexError: if no pools are found
    """
    return await autorelease_pool.get_current_autorelease_pool(self)
```

### LazyObjectiveCClassSymbol

Bases: `LazySymbol[DarwinSymbolT_co]`

Source code in `src/rpcclient/rpcclient/clients/darwin/client.py`

```
class LazyObjectiveCClassSymbol(LazySymbol[DarwinSymbolT_co]):
    @cached_async_method
    async def resolve(self) -> DarwinSymbolT_co:
        return await self._client.symbols.objc_getClass(self.name)

    async def objc_call(
        self, selector: str, *params: RemoteCallArg, va_list_index: int | None = None
    ) -> DarwinSymbolT_co:
        """call an objc method on a given object and return a symbol"""
        return await (await self.resolve())._objc_call(selector, *params, va_list_index=va_list_index)
```

#### objc_call

```
objc_call(selector: str, *params: RemoteCallArg, va_list_index: int | None = None) -> DarwinSymbolT_co
```

call an objc method on a given object and return a symbol

Source code in `src/rpcclient/rpcclient/clients/darwin/client.py`

```
async def objc_call(
    self, selector: str, *params: RemoteCallArg, va_list_index: int | None = None
) -> DarwinSymbolT_co:
    """call an objc method on a given object and return a symbol"""
    return await (await self.resolve())._objc_call(selector, *params, va_list_index=va_list_index)
```

## iOS

## rpcclient.clients.ios.client

### IosClient

Bases: `DarwinClient[DarwinSymbolT_co]`

Source code in `src/rpcclient/rpcclient/clients/ios/client.py`

```
class IosClient(DarwinClient[DarwinSymbolT_co]):
    @subsystem
    def backlight(self) -> Backlight[DarwinSymbolT_co]:
        return Backlight(self)

    @subsystem
    def reports(self) -> Reports[DarwinSymbolT_co]:
        return Reports(self, CRASH_REPORTS_DIR)

    @subsystem
    def mobile_gestalt(self) -> MobileGestalt[DarwinSymbolT_co]:
        return MobileGestalt(self)

    @subsystem
    def processes(self) -> IosProcesses[DarwinSymbolT_co]:
        return IosProcesses(self)

    @subsystem
    def preferences(self) -> IosPreferences[DarwinSymbolT_co]:
        return IosPreferences(self)

    @subsystem
    def lockdown(self) -> Lockdown[DarwinSymbolT_co]:
        return Lockdown(self)

    @subsystem
    def telephony(self) -> Telephony[DarwinSymbolT_co]:
        return Telephony(self)

    @subsystem
    def screen_capture(self) -> ScreenCapture[DarwinSymbolT_co]:
        return ScreenCapture(self)

    @subsystem
    def accessibility(self) -> Accessibility[DarwinSymbolT_co]:
        return Accessibility(self)

    @subsystem
    def wifi(self) -> IosWifi[DarwinSymbolT_co]:
        return IosWifi(self)

    @subsystem
    def springboard(self) -> SpringBoard[DarwinSymbolT_co]:
        return SpringBoard(self)

    @subsystem
    def amfi(self) -> Amfi[DarwinSymbolT_co]:
        return Amfi(self)

    @subsystem
    def installations(self) -> Installations[DarwinSymbolT_co]:
        return Installations(self)

    async def roots(self) -> list[str]:
        """get a list of all accessible darwin roots when used for lookup of files/preferences/..."""
        return [*(await super().roots()), "/var/mobile"]

    async def get_airplane_mode(self) -> bool:
        # use MobileGestalt for a more accurate result
        return await type(self.mobile_gestalt).AirplaneMode(self.mobile_gestalt)

    async def set_airplane_mode(self, value: bool) -> None:
        """set whether the device should enter airplane mode (turns off baseband, bt, etc...)"""
        radio_preferences = await (await self.symbols.objc_getClass("RadiosPreferences")).objc_call("new")
        await radio_preferences.objc_call("setAirplaneMode:", value)
        await radio_preferences.objc_call("synchronize")
```

#### roots

```
roots() -> list[str]
```

get a list of all accessible darwin roots when used for lookup of files/preferences/...

Source code in `src/rpcclient/rpcclient/clients/ios/client.py`

```
async def roots(self) -> list[str]:
    """get a list of all accessible darwin roots when used for lookup of files/preferences/..."""
    return [*(await super().roots()), "/var/mobile"]
```

#### set_airplane_mode

```
set_airplane_mode(value: bool) -> None
```

set whether the device should enter airplane mode (turns off baseband, bt, etc...)

Source code in `src/rpcclient/rpcclient/clients/ios/client.py`

```
async def set_airplane_mode(self, value: bool) -> None:
    """set whether the device should enter airplane mode (turns off baseband, bt, etc...)"""
    radio_preferences = await (await self.symbols.objc_getClass("RadiosPreferences")).objc_call("new")
    await radio_preferences.objc_call("setAirplaneMode:", value)
    await radio_preferences.objc_call("synchronize")
```
