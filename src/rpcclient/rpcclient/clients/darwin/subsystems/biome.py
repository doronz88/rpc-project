import json
from datetime import datetime
from functools import cached_property
from typing import TYPE_CHECKING, Any, Generic

import zyncio

from rpcclient.clients.darwin._types import DarwinSymbolT, DarwinSymbolT_co
from rpcclient.core._types import ClientBound
from rpcclient.core.allocated import Allocated
from rpcclient.core.subsystems.fs import Fs, RemotePath, RemoteTemporaryDir
from rpcclient.exceptions import SymbolAbsentError


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import BaseDarwinClient, LazyObjectiveCClassSymbol


BIOME_PATHS = [
    "/private/var/mobile/Library/Biome/streams/restricted",
    "/private/var/db/biome/streams/restricted",
    "/private/var/mobile/Library/Biome/streams/public",
    "/private/var/db/biome/streams/public",
]


class Biome(ClientBound["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """
    Biome interface for interacting with BiomeStreams.

    Loads the required framework and exposes helpers for enumerating streams and
    creating a `BiomeLibrary` for reading events.

    :param rpcclient.darwin.client.DarwinClient client: Connected Darwin client.
    :param Optional[list[str]] biome_paths: Paths to Biome storage directories on the remote host.
    :param Optional[Fs] fs: Filesystem helper. Defaults to `client.fs`.
    """

    def __init__(
        self,
        client: "BaseDarwinClient[DarwinSymbolT_co]",
        biome_paths: list[str] | None = None,
        fs: "Fs[BaseDarwinClient[DarwinSymbolT_co]] | None" = None,
    ) -> None:
        self._client = client
        self.fs = fs if fs is not None else client.fs
        self.biome_paths = biome_paths if biome_paths is not None else BIOME_PATHS

        client.load_framework_lazy("BiomeStreams")
        self.BPSBiomeStorePublisher_cls: LazyObjectiveCClassSymbol[DarwinSymbolT_co] = client.objc_get_class_lazy(
            "BPSBiomeStorePublisher"
        )
        self.BMStoreConfig_cls: LazyObjectiveCClassSymbol[DarwinSymbolT_co] = client.objc_get_class_lazy(
            "BMStoreConfig"
        )

    @zyncio.zmethod
    async def get_streams(self) -> set[str]:
        """
        Scan all configured Biome paths for accessible streams.

        Any entries prefixed with `_DKEvent` are ignored.

        :return: Stream identifiers discovered under the configured paths.
        """
        return {
            stream
            for biome_path in self.biome_paths
            if await self.fs.accessible.z(biome_path)
            for stream in await self.fs.listdir.z(biome_path)
            if not stream.startswith("_DKEvent")
        }

    @zyncio.zproperty
    async def streams(self) -> set[str]:
        """
        Scan all configured Biome paths for accessible streams.

        Any entries prefixed with `_DKEvent` are ignored.

        :return: Stream identifiers discovered under the configured paths.
        """
        return await self.get_streams.z()

    @zyncio.zmethod
    async def resolve_stream_path(self, stream: str) -> RemotePath | None:
        """
        Resolve a stream name to its first accessible `RemotePath`.

        :param str stream: Stream identifier.
        :return: Remote path of the stream, or `None` if not found.
        :rtype: Optional[RemotePath]
        """
        for biome_path in self.biome_paths:
            remote_path = self.fs.remote_path(f"{biome_path}/{stream}")
            if await self.fs.accessible.z(remote_path):
                return remote_path
        return None

    def create_library(self) -> "BiomeLibrary":
        """
        Create a `BiomeLibrary` bound to this client.

        This library should either be deallocated (using `*.deallocate()`),
        or used as a context manager with a `with` statement.

        :return: Initialized Biome library.
        :rtype: BiomeLibrary
        """
        return BiomeLibrary(self._client, self)


class BiomeEvent(Generic[DarwinSymbolT_co]):
    """
    Wrapper for a single Biome event extracted from a stream.

    :param raw_event: Raw Objective-C event object.
    :param data: Event data as a Python dict.
    :param stream: Stream identifier.
    """

    def __init__(self, raw_event: DarwinSymbolT_co, data: dict[str, Any], stream: str) -> None:
        self.native: DarwinSymbolT_co = raw_event
        self.data = data
        self.stream: str = stream

    @staticmethod
    async def create(raw_event: DarwinSymbolT, stream: str) -> "BiomeEvent[DarwinSymbolT]":
        """
        Create a BiomeEvent.

        :param raw_event: Raw Objective-C event object.
        :param stream: Stream identifier.
        """
        data = json.loads(await (await raw_event.objc_call.z("json")).py.z(str))
        return BiomeEvent(raw_event, data, stream)

    @cached_property
    def timestamp(self) -> datetime:
        """
        Event timestamp.

        :return: Event timestamp.
        :rtype: datetime
        """
        return datetime.fromtimestamp(self.data["eventTimestamp"])

    def __str__(self) -> str:
        """Human-readable string representation of the event data."""
        return str(self.data)

    def __repr__(self) -> str:
        """Debug representation of the event."""
        return f"<BiomeEvent from stream '{self.stream}'>"


class BiomeLibrary(Allocated["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """
    Access to Biome streams and events.

    Resolve requested streams via the parent `Biome`, copies stream
    data to a temporary directory, and reads events using Biome store publishers.

    This object should either be deallocated (using `*.deallocate()`),
    or used as a context manager with a `with` statement.

    :param rpcclient.darwin.client.DarwinClient client: Connected Darwin client.
    :param Biome biome: Parent `Biome` instance.
    """

    def __init__(self, client: "BaseDarwinClient[DarwinSymbolT_co]", biome: Biome[DarwinSymbolT_co]) -> None:
        Allocated.__init__(self)
        self._client = client
        self.biome: Biome[DarwinSymbolT_co] = biome
        self._event_classes = {}

    async def _allocate(self) -> None:
        self._tmp_dir = await self.biome.fs.remote_temp_dir.z()

        self._store_config = await (await self.biome.BMStoreConfig_cls.objc_call.z("alloc")).objc_call.z(
            "initWithStoreBasePath:segmentSize:", await self._client.cf.z(str(self.tmp_dir)), 0x80000
        )

        try:
            self._cached_BMEventClassForStreamIdentifier = (
                await self._client.symbols.BMEventClassForStreamIdentifier.resolve()
            )
        except SymbolAbsentError:
            self._cached_BMEventClassForStreamIdentifier = None

    async def _deallocate(self) -> None:
        """
        Release allocated Objective-C objects and temporary resources.

        Called by `Allocated` during cleanup.
        """
        if self._store_config is not None:
            await self.store_config.objc_call.z("release")
        if self._tmp_dir is not None:
            await self.tmp_dir.deallocate.z()

    _tmp_dir: "RemoteTemporaryDir[BaseDarwinClient[DarwinSymbolT_co]] | None" = None

    @property
    def tmp_dir(self) -> "RemoteTemporaryDir[BaseDarwinClient[DarwinSymbolT_co]]":
        if self._tmp_dir is None:
            raise RuntimeError(f"{type(self).__name__} object not yet allocated")
        return self._tmp_dir

    _store_config: DarwinSymbolT_co | None = None

    @property
    def store_config(self) -> DarwinSymbolT_co:
        if self._store_config is None:
            raise RuntimeError(f"{type(self).__name__} object not yet allocated")
        return self._store_config

    _cached_BMEventClassForStreamIdentifier: DarwinSymbolT_co | None | tuple[()] = ()

    @property
    def _BMEventClassForStreamIdentifier(self) -> DarwinSymbolT_co | None:
        if isinstance(self._cached_BMEventClassForStreamIdentifier, tuple):
            raise RuntimeError(f"{type(self).__name__} object not yet allocated")  # noqa: TRY004
        return self._cached_BMEventClassForStreamIdentifier

    @zyncio.zproperty
    async def streams(self) -> set[str]:
        """
        Scan all configured Biome paths for accessible streams.

        Any entries prefixed with `_DKEvent` are ignored.

        :return: Stream identifiers discovered under the configured paths.
        :rtype: set[str]
        """
        return await self.biome.get_streams.z()

    @zyncio.zmethod
    async def read_stream(self, stream: str, refresh: bool = True) -> list[BiomeEvent]:
        """
        Read events from a specified Biome stream.

        If *refresh* is `True`, copy the stream directory into `tmp_dir`
        before reading regurdless to the existance of a previously cached stream.
        Returns an empty list if the stream does not exist.

        :param str stream: Stream identifier.
        :param bool refresh: Whether to re-copy the stream before reading.
        :return: Parsed events.
        :rtype: list[BiomeEvent]
        """
        if refresh or not await self.biome.fs.accessible.z(self.tmp_dir / stream):
            remote_path = await self.biome.resolve_stream_path.z(stream)
            if remote_path is None:
                return []
            await self.biome.fs.cp.z([remote_path], self.tmp_dir, recursive=True, force=True)
        return await self._get_events_for_local_stream(stream)

    async def _get_event_class(self, stream: str) -> DarwinSymbolT_co:
        if stream in self._event_classes:
            return self._event_classes[stream]
        cf_stream_name = await self._client.cf.z(stream)
        if self._BMEventClassForStreamIdentifier is not None:
            event_class = await self._BMEventClassForStreamIdentifier.z(cf_stream_name)
        else:
            if stream.endswith(":tombstones"):
                return await self._client.symbols.objc_getClass.z("BMTombstoneEvent")
            internal_library = await self._client.symbols.BiomeLibraryAndInternalLibraryNode.z()
            stream_obj = await internal_library.objc_call.z("streamWithIdentifier:error:", cf_stream_name, 0)
            event_class = (
                self._client.null
                if stream_obj == 0
                else await (await stream_obj.objc_call.z("configuration")).objc_call.z("eventClass")
            )
        self._event_classes[stream] = event_class
        return event_class

    async def _create_publisher(self, stream: str) -> DarwinSymbolT_co:
        """
        Create and initialize a Biome store publisher for a given stream.

        :param str stream: Stream identifier.
        :return: Objective-C publisher object.
        :rtype: DarwinSymbol
        """
        cf_stream_name = await self._client.cf.z(stream)
        event_class = await self._get_event_class(stream)

        return await (await self.biome.BPSBiomeStorePublisher_cls.objc_call.z("alloc")).objc_call.z(
            "initWithStreamId:storeConfig:streamsAccessClient:eventDataClass:",
            cf_stream_name,
            self.store_config,
            0,
            event_class,
        )

    async def _get_events_for_local_stream(self, stream: str) -> list[BiomeEvent]:
        """
        Read all available events for a local copy of the given stream.

        Assumes the stream data already exists under `tmp_dir`.

        :param str stream: Stream identifier.
        :return: Parsed events.
        :rtype: list[BiomeEvent]
        """
        publisher = await self._create_publisher(stream)
        await publisher.objc_call.z("startWithSubscriber:", 0)
        events: list[BiomeEvent] = []
        while await publisher.objc_call.z("finished") != 1:
            event = await publisher.objc_call.z("nextEvent")
            if event != 0:
                events.append(await BiomeEvent.create(event, stream))
        return events
