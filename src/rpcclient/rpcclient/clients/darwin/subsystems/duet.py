from datetime import datetime
from typing import TYPE_CHECKING, Generic
from typing_extensions import Self

import zyncio

from rpcclient.clients.darwin._types import DarwinSymbolT, DarwinSymbolT_co
from rpcclient.clients.darwin.common import CfSerializable
from rpcclient.core._types import ClientBound, SymbolBound
from rpcclient.core.allocated import Allocated
from rpcclient.core.subsystems.fs import RemoteTemporaryDir
from rpcclient.utils import assert_cast, cached_async_method


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import BaseDarwinClient, LazyObjectiveCClassSymbol


class Duet(ClientBound["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    def __init__(self, client: "BaseDarwinClient[DarwinSymbolT_co]") -> None:
        """
        :param rpcclient.darwin.client.DarwinClient client:
        """
        self._client = client

        client.load_framework_lazy("DuetActivityScheduler")
        self.NSArray_cls: LazyObjectiveCClassSymbol[DarwinSymbolT_co] = client.objc_get_class_lazy("NSArray")
        self.CDPaths_cls: LazyObjectiveCClassSymbol[DarwinSymbolT_co] = client.objc_get_class_lazy("_CDPaths")
        self.DKEventQuery_cls: LazyObjectiveCClassSymbol[DarwinSymbolT_co] = client.objc_get_class_lazy("_DKEventQuery")
        self.DKKnowledgeStore_cls: LazyObjectiveCClassSymbol[DarwinSymbolT_co] = client.objc_get_class_lazy(
            "_DKKnowledgeStore"
        )
        self.DKKnowledgeStorage_cls: LazyObjectiveCClassSymbol[DarwinSymbolT_co] = client.objc_get_class_lazy(
            "_DKKnowledgeStorage"
        )
        self.DKSystemEventStreams_cls: LazyObjectiveCClassSymbol[DarwinSymbolT_co] = client.objc_get_class_lazy(
            "_DKSystemEventStreams"
        )

    @zyncio.zproperty
    @cached_async_method
    async def DKSystemEventStreams_cls_cls(self) -> DarwinSymbolT_co:
        return await self._client.symbols.objc_getClass.z(await self.DKSystemEventStreams_cls.resolve())

    @zyncio.zmethod
    async def knowledge_store(self) -> "KnowledgeStoreDup[DarwinSymbolT_co]":
        """Copy the on device knowledge store to a temp directory and open it read only."""
        return await KnowledgeStoreDup.create(self._client)

    @zyncio.zmethod
    async def knowledge_store_xpc(self) -> "KnowledgeStoreXPC[DarwinSymbolT_co]":
        """Connect directly to the live knowledge store via XPC."""
        return await KnowledgeStoreXPC.create(self._client)


class DKEvent(SymbolBound[DarwinSymbolT_co]):
    """Thin, *pythonic* wrapper around a private `_DKEvent` ObjectiveC object."""

    def __init__(self, event: DarwinSymbolT_co) -> None:
        """Initialise the wrapper.

        :param event: Underlying `_DKEvent` ObjectiveC event.
        """
        self._symbol = event
        self.native: DarwinSymbolT_co = event

    @zyncio.zproperty
    @cached_async_method
    async def start(self) -> datetime:
        """Return the event's *start* timestamp.

        :returns: Event start time.
        """
        return await (await self.native.objc_call.z("startDate")).py.z(datetime)

    @zyncio.zproperty
    @cached_async_method
    async def end(self) -> datetime:
        """Return the event's *end* timestamp (may equal *start*).

        :returns: Event end time.
        """
        return await (await self.native.objc_call.z("endDate")).py.z(datetime)

    @zyncio.zproperty
    @cached_async_method
    async def metadata(self) -> str:
        """Return the event's metadata dictionary, if present.

        :returns: Metadata mapping or `None` when absent.
        """
        return assert_cast(str, await (await self.native.objc_call.z("metadata")).get_cfdesc())

    @zyncio.zproperty
    @cached_async_method
    async def stream(self) -> str:
        """Return the name of the stream this event belongs to.

        :returns: Stream name.
        """
        return await (await (await self.native.objc_call.z("stream")).objc_call.z("name")).py.z(str)

    @zyncio.zproperty
    @cached_async_method
    async def value(self) -> CfSerializable:
        """Return the primary value associated with the event.

        :returns: Stream specific value type.
        """
        return await (await (await self.native.objc_call.z("value")).objc_call.z("primaryValue")).py.z()

    @zyncio.zproperty
    async def description(self) -> str:
        """Pretty print the event for quick inspection.

        :returns: Formatted multi line string representation.
        """
        cls = type(self)
        output = f"DKEvent - {await cls.stream(self)}\n\n"
        output += f" value:\t{await cls.value(self)}\n"
        output += f" start:\t{await cls.start(self)}\n"
        output += f" end:\t{await cls.end(self)}"
        output += f" metadata:\n{await cls.metadata(self)}"
        return output

    def __str__(self) -> str:
        if zyncio.is_sync(self):
            return self.description
        return f"<{type(self).__name__} (async)>"


class KnowledgeStoreContext(Allocated["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """Abstract context manager that exposes helper queries for `_DKKnowledgeStore`."""

    def __init__(
        self,
        client: "BaseDarwinClient[DarwinSymbolT_co]",
        streams: dict[str, DarwinSymbolT_co],
        knowledge_store: DarwinSymbolT_co,
    ) -> None:
        """Collect available system event streams and store the *rpcclient* handle."""
        self._client = client
        self.streams: dict[str, DarwinSymbolT_co] = streams
        self._knowledge_store: DarwinSymbolT_co = knowledge_store

    @staticmethod
    async def get_streams(client: "BaseDarwinClient[DarwinSymbolT_co]") -> dict[str, DarwinSymbolT_co]:
        streams = {}

        async with client.safe_malloc.z(8) as count:
            duet = client.duet
            methods = await client.symbols.class_copyMethodList.z(
                await type(duet).DKSystemEventStreams_cls_cls(duet), count
            )
            for i in range(await count.getindex(0)):
                method_name = await (
                    await client.symbols.sel_getName.z(await client.symbols.method_getName.z(await methods.getindex(i)))
                ).peek_str.z()
                stream = await duet.DKSystemEventStreams_cls.objc_call.z(method_name)
                streams[await (await stream.objc_call.z("name")).py.z()] = stream

        return streams

    @zyncio.zmethod
    async def query_events(self, stream: str) -> list["DKEvent"]:
        """Retrieve all events for a single stream.

        :param stream: Stream identifier.
        :returns: List of events or `None` when the stream is empty.
        """
        raw_events = await self._query_raw_events(stream)
        event_count = await raw_events.objc_call.z("count") if raw_events != 0 else 0
        return (
            [DKEvent(await raw_events.objc_call.z("objectAtIndex:", i)) for i in range(event_count)]
            if event_count != 0
            else []
        )

    @zyncio.zmethod
    async def query_events_streams(self, streams: list[str] | None = None) -> dict[str, list["DKEvent"]]:
        """Query multiple streams at once.

        :param streams: Specific streams to query. `None` queries all known streams.
        :returns: Mapping of stream name to event list (absent when stream empty).
        """
        events: dict[str, list[DKEvent]] = {}
        streams = list(self.streams.keys()) if streams is None else streams
        for stream in streams:
            events_for_stream = await self.query_events.z(stream)
            if len(events_for_stream) != 0:
                events[stream] = events_for_stream
        return events

    async def _query_raw_events(self, stream: str) -> DarwinSymbolT_co:
        """Build and execute a `_DKEventQuery` limited to *stream*.

        :param stream: Stream name.
        :returns: ObjectiveC array containing raw `_DKEvent` objects.
        """
        query = await self._client.duet.DKEventQuery_cls.objc_call.z("new")
        try:
            async with self._client.safe_malloc.z(8) as buf:
                await buf.setindex(0, self.streams[stream])
                arr = await self._client.duet.NSArray_cls.objc_call.z("arrayWithObjects:count:", buf, 1)
                await query.objc_call.z("setEventStreams:", arr)
                return await self._execute_query(query)
        finally:
            await query.objc_call.z("release")

    async def _execute_query(self: "KnowledgeStoreContext[DarwinSymbolT]", query: DarwinSymbolT) -> DarwinSymbolT:
        """Run *query* through the concrete :pyattr:`knowledge_store` implementation.

        :param query: Configured `_DKEventQuery` instance.
        :returns: ObjectiveC array with results.
        :raises RpcClientException: If :pyattr:`knowledge_store` is not yet initialized.
        """
        async with self._client.safe_malloc.z(8) as error:
            return await self.knowledge_store.objc_call.z("executeQuery:error:", query, error)

    async def _deallocate(self) -> None:
        """Release the allocated knowledge store object"""
        await self.knowledge_store.objc_call.z("release")

    @property
    def knowledge_store(self) -> DarwinSymbolT_co:
        """Return the clients specific `_DKKnowledgeStore` handle.

        :returns: Concrete store.
        """
        return self._knowledge_store


class KnowledgeStoreDup(KnowledgeStoreContext[DarwinSymbolT_co]):
    """Copy the on device knowledge store to a temp directory and open it read only."""

    def __init__(
        self,
        client: "BaseDarwinClient[DarwinSymbolT_co]",
        streams: dict[str, DarwinSymbolT_co],
        knowledge_store: DarwinSymbolT_co,
        tmp_dir: "RemoteTemporaryDir[BaseDarwinClient[DarwinSymbolT_co]]",
    ) -> None:
        """Create the temp directory, copy knowledge store files inside and init knowledge store objects."""
        super().__init__(client, streams, knowledge_store)
        self.tmp_dir: RemoteTemporaryDir[BaseDarwinClient[DarwinSymbolT_co]] = tmp_dir

    @classmethod
    async def create(cls, client: "BaseDarwinClient[DarwinSymbolT_co]") -> Self:
        origin_path = client.fs.remote_path(
            await (await client.duet.CDPaths_cls.objc_call.z("knowledgeDirectory")).py.z(str)
        )
        tmp_dir = await client.fs.remote_temp_dir.z()
        tmp_knowledge_dir = str(tmp_dir / origin_path.name)
        try:
            await client.fs.cp.z([origin_path], tmp_dir, recursive=True, force=False)
            knowledge_storage = await client.duet.DKKnowledgeStorage_cls.objc_call.z(
                "storageWithDirectory:readOnly:", await client.cf.z(tmp_knowledge_dir), 1
            )
            knowledge_store = await client.duet.DKKnowledgeStore_cls.objc_call.z("alloc")
            knowledge_store = await knowledge_store.objc_call.z(
                "initWithKnowledgeStoreHandle:readOnly:", knowledge_storage, 1
            )
        except Exception:
            await tmp_dir.deallocate.z()
            raise

        return cls(
            client,
            await cls.get_streams(client),
            knowledge_storage,
            tmp_dir,
        )

    async def _deallocate(self) -> None:
        """Delete the allocated temp dir and release the allocated knowledge store object"""
        await self.tmp_dir.deallocate.z()
        await super()._deallocate()


class KnowledgeStoreXPC(KnowledgeStoreContext[DarwinSymbolT_co]):
    """Connect directly to the live knowledge store via XPC."""

    @classmethod
    async def create(cls, client: "BaseDarwinClient[DarwinSymbolT_co]") -> Self:
        return cls(
            client,
            await cls.get_streams(client),
            await client.duet.DKKnowledgeStore_cls.objc_call.z("knowledgeStore"),
        )
