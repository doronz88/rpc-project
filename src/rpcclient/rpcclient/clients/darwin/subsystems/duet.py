from abc import ABC, abstractmethod
from datetime import datetime
from functools import cached_property
from typing import Any, Optional

from rpcclient.clients.darwin.symbol import DarwinSymbol
from rpcclient.core.allocated import Allocated
from rpcclient.exceptions import RpcClientException


class Duet:
    def __init__(self, client) -> None:
        """
        :param rpcclient.darwin.client.DarwinClient client:
        """
        self._client = client
        self._client.load_framework('DuetActivityScheduler')
        self.NSArray_cls = client.symbols.objc_getClass('NSArray')
        self.CDPaths_cls = client.symbols.objc_getClass('_CDPaths')
        self.DKEventQuery_cls = client.symbols.objc_getClass('_DKEventQuery')
        self.DKKnowledgeStore_cls = client.symbols.objc_getClass('_DKKnowledgeStore')
        self.DKKnowledgeStorage_cls = client.symbols.objc_getClass('_DKKnowledgeStorage')
        self.DKSystemEventStreams_cls = client.symbols.objc_getClass('_DKSystemEventStreams')
        self.DKSystemEventStreams_cls_cls = client.symbols.object_getClass(self.DKSystemEventStreams_cls)

    def knowledge_store(self) -> 'KnowledgeStoreDup':
        """Copy the on device knowledge store to a temp directory and open it read only."""
        return KnowledgeStoreDup(self._client, self)

    def knowledge_store_xpc(self) -> 'KnowledgeStoreXPC':
        """Connect directly to the live knowledge store via XPC."""
        return KnowledgeStoreXPC(self._client, self)


class DKEvent:
    """Thin, *pythonic* wrapper around a private `_DKEvent` ObjectiveC object."""

    def __init__(self, event: DarwinSymbol) -> None:
        """Initialise the wrapper.

        :param event: Underlying `_DKEvent` ObjectiveC event.
        """
        self.native = event

    @cached_property
    def start(self) -> datetime:
        """Return the event's *start* timestamp.

        :returns: Event start time.
        """
        return self.native.objc_call('startDate').py()

    @cached_property
    def end(self) -> datetime:
        """Return the event's *end* timestamp (may equal *start*).

        :returns: Event end time.
        """
        return self.native.objc_call('endDate').py()

    @cached_property
    def metadata(self) -> str:
        """Return the event's metadata dictionary, if present.

        :returns: Metadata mapping or `None` when absent.
        """
        return self.native.objc_call('metadata').cfdesc

    @cached_property
    def stream(self) -> str:
        """Return the name of the stream this event belongs to.

        :returns: Stream name.
        """
        return self.native.objc_call('stream').objc_call('name').py()

    @cached_property
    def value(self) -> Any:
        """Return the primary value associated with the event.

        :returns: Stream specific value type.
        """
        return self.native.objc_call('value').objc_call('primaryValue').py()

    def __str__(self) -> str:
        """Pretty print the event for quick inspection.

        :returns: Formatted multi line string representation.
        """
        output = f'DKEvent - {self.stream}\n\n'
        output += f' value:\t{self.value}\n'
        output += f' start:\t{self.start}\n'
        output += f' end:\t{self.end}'
        output += f' metadata:\n{self.metadata}'
        return output


class KnowledgeStoreContext(ABC, Allocated):
    """Abstract context manager that exposes helper queries for `_DKKnowledgeStore`."""

    def __init__(self, client, duet: Duet) -> None:
        """Collect available system event streams and store the *rpcclient* handle.

        :param rpcclient.darwin.client.DarwinClient client:
        :param duet:
        """
        Allocated.__init__(self)
        self._client = client
        self._duet = duet
        self.streams: dict[str, DarwinSymbol] = {}
        with client.safe_malloc(8) as count:
            methods = client.symbols.class_copyMethodList(duet.DKSystemEventStreams_cls_cls, count)
            for i in range(count[0]):
                method_name = client.symbols.sel_getName(
                    client.symbols.method_getName(methods[i])
                ).peek_str()
                stream = duet.DKSystemEventStreams_cls.objc_call(method_name)
                self.streams[stream.objc_call('name').py()] = stream

    def query_events(self, stream: str) -> list['DKEvent']:
        """Retrieve all events for a single stream.

        :param stream: Stream identifier.
        :returns: List of events or `None` when the stream is empty.
        """
        raw_events = self._query_raw_events(stream)
        event_count = raw_events.objc_call('count') if 0 != raw_events else 0
        return (
            [DKEvent(raw_events.objc_call('objectAtIndex:', i)) for i in range(event_count)]
            if event_count != 0
            else []
        )

    def query_events_streams(self, streams: Optional[list[str]] = None) -> dict[str, list['DKEvent']]:
        """Query multiple streams at once.

        :param streams: Specific streams to query. `None` queries all known streams.
        :returns: Mapping of stream name to event list (absent when stream empty).
        """
        events: dict[str, list[DKEvent]] = {}
        streams = list(self.streams.keys()) if streams is None else streams
        for stream in streams:
            events_for_stream = self.query_events(stream)
            if 0 != len(events_for_stream):
                events[stream] = events_for_stream
        return events

    def _query_raw_events(self, stream: str) -> DarwinSymbol:
        """Build and execute a `_DKEventQuery` limited to *stream*.

        :param stream: Stream name.
        :returns: ObjectiveC array containing raw `_DKEvent` objects.
        """
        query = self._duet.DKEventQuery_cls.objc_call('new')
        try:
            with self._client.safe_malloc(8) as buf:
                buf[0] = self.streams[stream]
                arr = self._duet.NSArray_cls.objc_call(
                    'arrayWithObjects:count:', buf, 1
                )
                query.objc_call('setEventStreams:', arr)
                return self._execute_query(query)
        finally:
            query.objc_call('release')

    def _execute_query(self, query: DarwinSymbol) -> DarwinSymbol:
        """Run *query* through the concrete :pyattr:`knowledge_store` implementation.

        :param query: Configured `_DKEventQuery` instance.
        :returns: ObjectiveC array with results.
        :raises RpcClientException: If :pyattr:`knowledge_store` is not yet initialized.
        """
        if self.knowledge_store is None:
            raise RpcClientException('KnowledgeStore not initialized')
        with self._client.safe_malloc(8) as error:
            return self.knowledge_store.objc_call('executeQuery:error:', query, error)

    def _deallocate(self):
        """Release the allocated knowledge store object"""
        self.knowledge_store.objc_call('release')

    @property
    @abstractmethod
    def knowledge_store(self) -> DarwinSymbol:
        """Return the clients specific `_DKKnowledgeStore` handle.

        :returns: Concrete store.
        """
        pass


class KnowledgeStoreDup(KnowledgeStoreContext):
    """Copy the on device knowledge store to a temp directory and open it read only."""

    def __init__(self, client, duet: Duet) -> None:
        """Create the temp directory, copy knowledge store files inside and init knowledge store objects.

        :param rpcclient.darwin.client.DarwinClient client:
        :param duet:
        """
        super().__init__(client, duet)
        origin_path = client.fs.remote_path(duet.CDPaths_cls.objc_call('knowledgeDirectory').py())
        self.tmp_dir = client.fs.remote_temp_dir()
        tmp_knowledge_dir = str(self.tmp_dir / origin_path.name)
        try:
            client.fs.cp([origin_path], self.tmp_dir, recursive=True, force=False)
            knowledge_storage = self._duet.DKKnowledgeStorage_cls.objc_call(
                'storageWithDirectory:readOnly:', self._client.cf(tmp_knowledge_dir), 1
            )
            knowledge_store = self._duet.DKKnowledgeStore_cls.objc_call('alloc')
            self._knowledge_store = knowledge_store.objc_call(
                'initWithKnowledgeStoreHandle:readOnly:', knowledge_storage, 1
            )
        except Exception as e:
            self.tmp_dir.deallocate()
            raise e

    def _deallocate(self):
        """Delete the allocated temp dir and release the allocated knowledge store object"""
        self.tmp_dir.deallocate()
        super()._deallocate()

    @property
    def knowledge_store(self) -> Optional[DarwinSymbol]:
        """Expose the read only copied knowledge store handle.

        :returns: Store handle or `None` if context not entered.
        """
        return self._knowledge_store


class KnowledgeStoreXPC(KnowledgeStoreContext):
    """Connect directly to the live knowledge store via XPC."""

    def __init__(self, client, duet: Duet) -> None:
        """connect to the XPC knowledge store interface on the device.

        :param rpcclient.darwin.client.DarwinClient client:
        :param duet:
        """
        super().__init__(client, duet)
        self._knowledge_store: DarwinSymbol = duet.DKKnowledgeStore_cls.objc_call('knowledgeStore')

    @property
    def knowledge_store(self) -> Optional[DarwinSymbol]:
        """Expose the live XPC backed knowledge store handle.

        :returns: Store handle.
        """
        return self._knowledge_store
