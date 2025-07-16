import tempfile
from abc import ABC, abstractmethod
from datetime import datetime
from functools import cached_property
from pathlib import Path
from pprint import pformat
from typing import Any, List, Optional

from rpcclient.darwin.symbol import DarwinSymbol
from rpcclient.exceptions import RpcClientException


class Duet:
    def __init__(self, client):
        """
        :param client: Active *rpcclient* instance.
        """
        self._client = client

    def knowledge_store_copy_ctx(self):
        """Copy the on device knowledge store locally and open it read only."""
        return KnowledgeStoreCopyContext(self._client)

    def knowledge_store_xpc_ctx(self):
        """Connect directly to the live knowledge store via XPC."""
        return XPCKnowledgeStoreContext(self._client)


class DKEvent:
    """Thin, *pythonic* wrapper around a private ``_DKEvent`` ObjectiveC object."""

    def __init__(self, event: DarwinSymbol):
        """Initialise the wrapper.

        :param event: Underlying ``_DKEvent`` ObjectiveC event.
        """
        self.origin = event

    @cached_property
    def start(self) -> datetime:
        """Return the event's *start* timestamp.

        :returns: Event start time.
        """
        return self.origin.objc_call('startDate').py()

    @cached_property
    def end(self) -> datetime:
        """Return the event's *end* timestamp (may equal *start*).

        :returns: Event end time.
        """
        return self.origin.objc_call('endDate').py()

    @cached_property
    def metadata(self) -> Optional[dict[str, Any]]:
        """Return the event's metadata dictionary, if present.

        :returns: Metadata mapping or ``None`` when absent.
        """
        return self.origin.objc_call('metadata').py()

    @cached_property
    def stream(self) -> str:
        """Return the name of the stream this event belongs to.

        :returns: Stream name.
        """
        return self.origin.objc_call('stream').objc_call('name').py()

    @cached_property
    def value(self):
        """Return the primary value associated with the event.

        :returns: Stream specific value type.
        """
        return self.origin.objc_call('value').objc_call('primaryValue').py()

    def __str__(self) -> str:
        """Pretty print the event for quick inspection.

        :returns: Formatted multi line string representation.
        """
        output = f'DKEvent - {self.stream}\n\n'
        output += f' value:\t{self.value}\n'
        output += f' start:\t{self.start}\n'
        output += f' end:\t{self.end}'
        if self.metadata is not None:
            output += f'\n metadata: \n{pformat(self.metadata, compact=True, width=120, indent=2)}'
        return output


class KnowledgeStoreContext(ABC):
    """Abstract context manager that exposes helper queries for ``_DKKnowledgeStore``."""

    def __init__(self, client):
        """Collect available system event streams and store the *rpcclient* handle.

        :param client: Active *rpcclient* instance.
        """
        self._client = client
        self.streams: dict[str, DarwinSymbol] = {}
        _DKSystemEventStreams = self._client.symbols.objc_getClass('_DKSystemEventStreams')
        _DKSystemEventStreams_cls = self._client.symbols.object_getClass(_DKSystemEventStreams)
        with self._client.safe_malloc(8) as count:
            methods = self._client.symbols.class_copyMethodList(_DKSystemEventStreams_cls, count)
            for i in range(count[0]):
                method_name = self._client.symbols.sel_getName(
                    self._client.symbols.method_getName(methods[i])
                ).peek_str()
                stream = _DKSystemEventStreams.objc_call(method_name)
                self.streams[stream.objc_call('name').py()] = stream

    def query_events(self, stream: str) -> Optional[List['DKEvent']]:
        """Retrieve all events for a single stream.

        :param stream: Stream identifier.
        :returns: List of events or ``None`` when the stream is empty.
        """
        raw_events = self._query_raw_events(stream)
        event_count = raw_events.objc_call('count')
        return (
            [DKEvent(raw_events.objc_call('objectAtIndex:', i)) for i in range(event_count)]
            if event_count != 0
            else None
        )

    def query_events_streams(self, streams: Optional[List[str]] = None) -> dict[str, List['DKEvent']]:
        """Query multiple streams at once.

        :param streams: Specific streams to query. ``None`` queries all known streams.
        :returns: Mapping of stream name to event list (absent when stream empty).
        """
        events: dict[str, List[DKEvent]] = {}
        streams = list(self.streams.keys()) if streams is None else streams
        for stream in streams:
            events_for_stream = self.query_events(stream)
            if events_for_stream is not None:
                events[stream] = events_for_stream
        return events

    def _query_raw_events(self, stream: str) -> DarwinSymbol:
        """Build and execute a ``_DKEventQuery`` limited to *stream*.

        :param stream: Stream name.
        :returns: ObjectiveC array containing raw ``_DKEvent`` objects.
        """
        query = self._client.symbols.objc_getClass('_DKEventQuery').objc_call('new')
        query.objc_call('autorelease')
        with self._client.safe_malloc(8) as buf:
            buf[0] = self.streams[stream]
            arr = self._client.symbols.objc_getClass('NSArray').objc_call(
                'arrayWithObjects:count:', buf, 1
            )
            query.objc_call('setEventStreams:', arr)
            return self._execute_query(query)

    def _execute_query(self, query: DarwinSymbol) -> DarwinSymbol:
        """Run *query* through the concrete :pyattr:`knowledge_store` implementation.

        :param query: Configured ``_DKEventQuery`` instance.
        :returns: ObjectiveC array with results.
        :raises RpcClientException: If :pyattr:`knowledge_store` is not yet initialized.
        """
        if self.knowledge_store is None:
            raise RpcClientException('KnowledgeStore not initialized')
        with self._client.safe_malloc(8) as error:
            return self.knowledge_store.objc_call('executeQuery:error:', query, error)

    @abstractmethod
    def __enter__(self) -> 'KnowledgeStoreContext':
        """Enter the context manager.

        :returns: Self reference.
        """

    @abstractmethod
    def __exit__(self, type, value, traceback):
        """Handle context teardown in subclasses.

        :param type:      Exception type, if any.
        :param value:     Exception instance, if any.
        :param traceback: Traceback object, if any.
        """

    @property
    @abstractmethod
    def knowledge_store(self) -> Optional[DarwinSymbol]:
        """Return the platform specific ``_DKKnowledgeStore`` handle.

        :returns: Concrete store or ``None`` if not yet initialised.
        """


class KnowledgeStoreCopyContext(KnowledgeStoreContext):
    """Copy the on device knowledge store locally and open it read only."""

    def __init__(self, client):
        """Prepare placeholders for temp directory and store handle.

        :param client: Active *rpcclient* instance.
        """
        super().__init__(client)
        self.tmp_dir_ctx: Optional[tempfile.TemporaryDirectory[str]] = None
        self._knowledge_store: Optional[DarwinSymbol] = None

    def __enter__(self) -> 'KnowledgeStoreCopyContext':
        """Create a local copy of the store and return the ready context.

        :returns: Context with a read only store backing.
        """
        if self.tmp_dir_ctx is not None or self._knowledge_store is not None:
            raise RpcClientException('KnowledgeStore copy context already initialised')
        self.tmp_dir_ctx = tempfile.TemporaryDirectory()
        tmp_dir = self.tmp_dir_ctx.__enter__()
        remote_path = self._client.symbols.objc_getClass('_CDPaths').objc_call('knowledgeDirectory').py()
        self._client.fs.pull([remote_path], tmp_dir, recursive=True)
        local_path = str(Path(tmp_dir) / Path(remote_path).parts[-1])
        knowledge_storage = self._client.symbols.objc_getClass('_DKKnowledgeStorage').objc_call(
            'storageWithDirectory:readOnly:', self._client.cf(local_path), 1
        )
        knowledge_store = self._client.symbols.objc_getClass('_DKKnowledgeStore').objc_call('alloc')
        self._knowledge_store = knowledge_store.objc_call(
            'initWithKnowledgeStoreHandle:readOnly:', knowledge_storage, 1
        )
        return self

    def __exit__(self, type, value, traceback):
        """Close the store and clean up the temporary directory."""
        if self.tmp_dir_ctx is None or self._knowledge_store is None:
            raise RpcClientException('KnowledgeStore copy context not initialised')
        self._knowledge_store.objc_call('release')
        self._knowledge_store = None
        self.tmp_dir_ctx.__exit__(type, value, traceback)
        self.tmp_dir_ctx = None

    @property
    def knowledge_store(self) -> Optional[DarwinSymbol]:
        """Expose the read only copied knowledge store handle.

        :returns: Store handle or ``None`` if context not entered.
        :rtype:   DarwinSymbol | None
        """
        return self._knowledge_store


class XPCKnowledgeStoreContext(KnowledgeStoreContext):
    """Connect directly to the live knowledge store via XPC."""

    def __init__(self, client):
        """Fetch the shared ``knowledgeStore`` singleton from the device.

        :param client: Active *rpcclient* instance.
        """
        super().__init__(client)
        self._knowledge_store: DarwinSymbol = client.symbols.objc_getClass('_DKKnowledgeStore').objc_call(
            'knowledgeStore'
        )

    def __enter__(self) -> 'XPCKnowledgeStoreContext':
        """Return the context (no extra setup required).

        :returns: Self reference.
        """
        return self

    def __exit__(self, type, value, traceback):
        """No explicit teardown needed for the XPC singleton."""
        pass

    @property
    def knowledge_store(self) -> Optional[DarwinSymbol]:
        """Expose the live XPC backed knowledge store handle.

        :returns: Store handle.
        """
        return self._knowledge_store
