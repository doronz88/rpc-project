import json
from datetime import datetime
from functools import cached_property
from typing import Any, Optional

from rpcclient.clients.darwin.symbol import DarwinSymbol
from rpcclient.core.allocated import Allocated
from rpcclient.core.subsystems.fs import Fs, RemotePath
from rpcclient.exceptions import SymbolAbsentError

BIOME_PATHS = [
    "/private/var/mobile/Library/Biome/streams/restricted",
    "/private/var/db/biome/streams/restricted",
    "/private/var/mobile/Library/Biome/streams/public",
    "/private/var/db/biome/streams/public",
]


class Biome:
    """
    Biome interface for interacting with BiomeStreams.

    Loads the required framework and exposes helpers for enumerating streams and
    creating a `BiomeLibrary` for reading events.

    :param rpcclient.darwin.client.DarwinClient client: Connected Darwin client.
    :param Optional[list[str]] biome_paths: Paths to Biome storage directories on the remote host.
    :param Optional[Fs] fs: Filesystem helper. Defaults to `client.fs`.
    """

    def __init__(self, client, biome_paths: Optional[list[str]] = None, fs: Optional[Fs] = None) -> None:
        self._client = client
        self._client.load_framework("BiomeStreams")
        self.fs = fs if fs is not None else client.fs
        self.biome_paths = biome_paths if biome_paths is not None else BIOME_PATHS
        self.BPSBiomeStorePublisher_cls = client.symbols.objc_getClass("BPSBiomeStorePublisher")
        self.BMStoreConfig_cls = client.symbols.objc_getClass("BMStoreConfig")

    @property
    def streams(self) -> set[str]:
        """
        Scan all configured Biome paths for accessible streams.

        Any entries prefixed with `_DKEvent` are ignored.

        :return: Stream identifiers discovered under the configured paths.
        :rtype: set[str]
        """
        streams = set()
        for biome_path in self.biome_paths:
            if self.fs.accessible(biome_path):
                for stream in self.fs.listdir(biome_path):
                    if not stream.startswith("_DKEvent"):
                        streams.add(stream)
        return streams

    def resolve_stream_path(self, stream: str) -> Optional[RemotePath]:
        """
        Resolve a stream name to its first accessible `RemotePath`.

        :param str stream: Stream identifier.
        :return: Remote path of the stream, or `None` if not found.
        :rtype: Optional[RemotePath]
        """
        for biome_path in self.biome_paths:
            remote_path = self.fs.remote_path(f"{biome_path}/{stream}")
            if self.fs.accessible(remote_path):
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


class BiomeEvent:
    """
    Wrapper for a single Biome event extracted from a stream.

    :param DarwinSymbol raw_event: Raw Objective-C event object.
    :param str stream: Stream identifier.
    """

    def __init__(self, raw_event: DarwinSymbol, stream: str):
        self.native = raw_event
        self.stream = stream

    @cached_property
    def data(self) -> dict[str, Any]:
        """
        Event data.

        :return: Event data as a Python dict.
        :rtype: dict[str, Any]
        """
        return json.loads(self.native.objc_call("json").py())

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


class BiomeLibrary(Allocated):
    """
    Access to Biome streams and events.

    Resolve requested streams via the parent `Biome`, copies stream
    data to a temporary directory, and reads events using Biome store publishers.

    This object should either be deallocated (using `*.deallocate()`),
    or used as a context manager with a `with` statement.

    :param rpcclient.darwin.client.DarwinClient client: Connected Darwin client.
    :param Biome biome: Parent `Biome` instance.
    """

    def __init__(self, client, biome: Biome) -> None:
        Allocated.__init__(self)
        self._client = client
        self.biome = biome
        self.tmp_dir = self.biome.fs.remote_temp_dir()
        self.store_config = biome.BMStoreConfig_cls.objc_call("alloc").objc_call(
            "initWithStoreBasePath:segmentSize:", client.cf(str(self.tmp_dir)), 0x80000
        )
        try:
            self._BMEventClassForStreamIdentifier = client.symbols.BMEventClassForStreamIdentifier
        except SymbolAbsentError:
            self._BMEventClassForStreamIdentifier = None
        self._event_classes = {}

    @property
    def streams(self) -> set[str]:
        """
        Scan all configured Biome paths for accessible streams.

        Any entries prefixed with `_DKEvent` are ignored.

        :return: Stream identifiers discovered under the configured paths.
        :rtype: set[str]
        """
        return self.biome.streams

    def read_stream(self, stream: str, refresh: bool = True) -> list[BiomeEvent]:
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
        if refresh or not self.biome.fs.accessible(self.tmp_dir / stream):
            remote_path = self.biome.resolve_stream_path(stream)
            if remote_path is None:
                return []
            self.biome.fs.cp([remote_path], self.tmp_dir, recursive=True, force=True)
        return self._get_events_for_local_stream(stream)

    def _get_event_class(self, stream: str) -> DarwinSymbol:
        if stream in self._event_classes:
            return self._event_classes[stream]
        cf_stream_name = self._client.cf(stream)
        if self._BMEventClassForStreamIdentifier is not None:
            event_class = self._BMEventClassForStreamIdentifier(cf_stream_name)
        else:
            if stream.endswith(":tombstones"):
                return self._client.symbols.objc_getClass("BMTombstoneEvent")
            internal_library = self._client.symbols.BiomeLibraryAndInternalLibraryNode()
            stream_obj = internal_library.objc_call("streamWithIdentifier:error:", cf_stream_name, 0)
            event_class = (
                self._client.symbol(0)
                if stream_obj == 0
                else stream_obj.objc_call("configuration").objc_call("eventClass")
            )
        self._event_classes[stream] = event_class
        return event_class

    def _create_publisher(self, stream: str) -> DarwinSymbol:
        """
        Create and initialize a Biome store publisher for a given stream.

        :param str stream: Stream identifier.
        :return: Objective-C publisher object.
        :rtype: DarwinSymbol
        """
        cf_stream_name = self._client.cf(stream)
        event_class = self._get_event_class(stream)

        return self.biome.BPSBiomeStorePublisher_cls.objc_call("alloc").objc_call(
            "initWithStreamId:storeConfig:streamsAccessClient:eventDataClass:",
            cf_stream_name,
            self.store_config,
            0,
            event_class,
        )

    def _get_events_for_local_stream(self, stream: str) -> list[BiomeEvent]:
        """
        Read all available events for a local copy of the given stream.

        Assumes the stream data already exists under `tmp_dir`.

        :param str stream: Stream identifier.
        :return: Parsed events.
        :rtype: list[BiomeEvent]
        """
        publisher = self._create_publisher(stream)
        publisher.objc_call("startWithSubscriber:", 0)
        events: list[BiomeEvent] = []
        while publisher.objc_call("finished") != 1:
            event = publisher.objc_call("nextEvent")
            if event != 0:
                events.append(BiomeEvent(event, stream))
        return events

    def _deallocate(self) -> None:
        """
        Release allocated Objective-C objects and temporary resources.

        Called by `Allocated` during cleanup.
        """
        self.store_config.objc_call("release")
        self.tmp_dir.deallocate()
