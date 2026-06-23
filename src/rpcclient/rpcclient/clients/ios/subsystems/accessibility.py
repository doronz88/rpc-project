import dataclasses
import time
from collections.abc import AsyncGenerator, AsyncIterator
from enum import IntEnum, IntFlag
from typing import TYPE_CHECKING, Any, Generic
from typing_extensions import Self

from construct import Container

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.core._types import ClientBound
from rpcclient.core.client import RemoteCallArg
from rpcclient.core.symbol import AbstractSymbol
from rpcclient.exceptions import (
    ElementNotFoundError,
    FirstElementNotFoundError,
    LastElementNotFoundError,
    RpcAccessibilityTurnedOffError,
    RpcFailedToGetPrimaryAppError,
)
from rpcclient.utils import cached_async_method


if TYPE_CHECKING:
    from rpcclient.clients.ios.client import IosClient


class AXDirection(IntEnum):
    Next = 1
    Previous = 2


class FrameStyle(IntEnum):
    Default = 0
    Blue = 0
    Green = 1
    Yellow = 4
    LightGreen = 5
    Invisible = 6


class AXTraits(IntFlag):
    kAXButtonTrait = 0x01
    kAXLinkTrait = 0x02
    kAXVisitedTrait = 0x100000000
    kAXHeaderTrait = 0x10000
    kAXFooterTrait = 0x4000000
    kAXWebContentTrait = 0x20000
    kAXTextEntryTrait = 0x40000
    kAXImageTrait = 0x4
    kAXSelectedTrait = 0x8
    kAXPlaysSoundTrait = 0x10
    kAXKeyboardKeyTrait = 0x20
    kAXStaticTextTrait = 0x40
    kAXSummaryElementTrait = 0x80
    kAXNotEnabledTrait = 0x100
    kAXPickerElementTrait = 0x80000
    kAXUpdatesFrequentlyTrait = 0x200
    kAXIsEditingTrait = 0x200000
    kAXLaunchIconTrait = 0x400000
    kAXFolderIconTrait = 0x4000000000000
    kAXSearchFieldTrait = 0x400
    kAXStatusBarElementTrait = 0x800000
    kAXAllowsLayoutChangeInStatusBarTrait = 0x400000000000000
    kAXSecureTextFieldTrait = 0x1000000
    kAXBackButtonTrait = 0x8000000
    kAXToggleTrait = 0x20000000000000
    kAXSelectionDismissesItemTrait = 0x80000000
    kAXScrollableTrait = 0x200000000
    kAXSpacerTrait = 0x400000000
    kAXTableIndexTrait = 0x800000000
    kAXMapTrait = 0x1000000000
    kAXTextOperationsAvailableTrait = 0x2000000000
    kAXDraggableTrait = 0x4000000000
    kAXGesturePracticeRegionTrait = 0x8000000000
    kAXPopupButtonTrait = 0x10000000000
    kAXAllowsNativeSlidingTrait = 0x20000000000
    kAXTouchContainerTrait = 0x200000000000
    kAXSupportsZoomTrait = 0x400000000000
    kAXTextAreaTrait = 0x800000000000
    kAXBookContentTrait = 0x1000000000000
    kAXStartsMediaSessionTrait = 0x800
    kAXAdjustableTrait = 0x1000
    kAXMenuItemTrait = 0x10000000000000
    kAXAutoCorrectCandidateTrait = 0x20000000
    kAXDeleteKeyTrait = 0x40000000
    kAXTabButtonTrait = 0x10000000
    kAXIgnoreItemChooserTrait = 0x40000000000000
    kAXAllowsDirectInteractionTrait = 0x2000
    kAXCausesPageTurnTrait = 0x4000
    kAXTabBarTrait = 0x8000
    kAXRadioButtonTrait = 0x100000
    kAXMathEquationTrait = 0x40000000000
    kAXInactiveTrait = 0x2000000
    kAXSupportsTrackingDetailTrait = 0x80000000000000
    kAXAlertTrait = 0x100000000000000
    kAXReadOnlyTrait = 0x8000000000000
    kAXProminentIconTrait = 0x1000000000000000


@dataclasses.dataclass
class CGPoint:
    x: float
    y: float

    def __str__(self) -> str:
        return f"{{{self.x}, {self.y}}}"


@dataclasses.dataclass
class CGSize:
    width: float
    height: float

    def __str__(self) -> str:
        return f"{{{self.width}, {self.height}}}"


@dataclasses.dataclass
class CGRect:
    origin: CGPoint
    size: CGSize

    def __str__(self) -> str:
        return f"{{{self.origin}, {self.size}}}"


class AXElement(AbstractSymbol, ClientBound["IosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """
    Wrapper around the device AXElement Objective-C object.

    Built from reversed XADInspectorManager methods.
    """

    def __init__(self, value: int, client: "IosClient[DarwinSymbolT_co]") -> None:
        self._client = client
        self._sym: DarwinSymbolT_co = client.symbol(value)

    def _symbol_from_value(self, value: int) -> DarwinSymbolT_co:
        return self._client.symbol(value)

    async def peek(self, count: int, offset: int = 0) -> bytes:
        return await self._sym.peek(count, offset)

    async def poke(self, buf: bytes, offset: int = 0) -> Any:
        return await self._sym.poke(buf, offset)

    async def peek_str(self, encoding="utf-8") -> str:
        """peek string at given address"""
        return await self._sym.peek_str(encoding=encoding)

    @property
    def arch(self) -> object:
        return self._client.arch

    @property
    def endianness(self) -> str:
        return self._client._endianness

    async def get_dl_info(self) -> Container:
        return await self._sym.get_dl_info()

    async def objc_call(
        self, selector: str, *params: RemoteCallArg, va_list_index: int | None = None
    ) -> DarwinSymbolT_co:
        """call an objc method on a given object and return a symbol"""
        return await self._sym.objc_call(selector, *params, va_list_index=va_list_index)

    async def first_element(self) -> Self:
        """Return the first element in the accessibility hierarchy."""
        result = await self._element_for_attribute(3000)
        if not result:
            raise FirstElementNotFoundError("failed to get first element in hierarchy")

        if await (await type(result).ui_element(result)).objc_call("boolWithAXAttribute:", 2046):
            result = await result._element_for_attribute(3000)
        assert result is not None
        return result

    async def last_element(self) -> Self:
        """Return the last element in the accessibility hierarchy."""
        result = await self._element_for_attribute(3016)
        if not result:
            raise LastElementNotFoundError("failed to get last element in hierarchy")

        if await (await type(result).ui_element(result)).objc_call("boolWithAXAttribute:", 2046):
            result = await result._element_for_attribute(3016)

        assert result is not None
        return result

    async def identifier(self) -> str:
        """Return the element identifier."""
        return await (await self.objc_call("identifier")).py(str)

    async def url(self) -> str:
        """Return the element URL."""
        return await (await self.objc_call("url")).py(str)

    async def path(self) -> DarwinSymbolT_co:
        """Return the element path object."""
        return await self.objc_call("path")

    async def frame(self) -> CGRect:
        """Return the element frame as a CGRect."""
        result = await self._sym.objc_call_raw("frame")
        return CGRect(origin=CGPoint(x=result.d0, y=result.d1), size=CGSize(width=result.d2, height=result.d3))

    async def label(self) -> str | None:
        """Return the visible label text."""
        return await (await self.objc_call("label")).py(str)

    async def value(self) -> str:
        """Return the element value."""
        return await (await self.objc_call("value")).py(str)

    async def bundle_identifier(self) -> str:
        """Return the owning app bundle identifier."""
        return await (await self.objc_call("bundleId")).py(str)

    async def pid(self) -> int:
        """Return the owning process ID."""
        return (await self.objc_call("pid")).c_uint16

    async def process_name(self) -> str:
        """Return the owning process name."""
        return await (await self.objc_call("processName")).py(str)

    async def screen_locked(self) -> bool:
        """Return True if the screen is locked."""
        return await self.objc_call("isScreenLocked") == 1

    async def is_accessibility_opaque_element_provider(self) -> bool:
        """Return True if the element provides its own accessibility hierarchy."""
        return await self.objc_call("isAccessibilityOpaqueElementProvider") != 0

    async def parent(self) -> Self | None:
        """Return the parent element if available."""
        tmp = await self._element_for_attribute(2066)
        if tmp:
            return tmp

        tmp = await self._element_for_attribute(2092)
        if tmp:
            return await type(tmp).parent(tmp)

        return None

    async def ui_element(self) -> DarwinSymbolT_co:
        """Return the underlying AXUIElement."""
        return await self.objc_call("uiElement")

    async def traits(self) -> AXTraits:
        """Return the element traits as AXTraits."""
        return AXTraits((await self.objc_call("traits")).c_uint64)

    async def elements(self) -> list[Self]:
        """Return the list of currently displayed elements."""
        result = []
        elements = await self.objc_call("explorerElements")
        for i in range(await elements.objc_call("count")):
            result.append(self._client.accessibility.axelement(await elements.objc_call("objectAtIndex:", i)))
        return result

    async def insert_text(self, text: str) -> None:
        """Insert text into the focused editable element."""
        await self.objc_call("insertText:", await self._client.cf(text))

    async def delete_text(self) -> None:
        """Delete a character from the focused editable element."""
        await self.objc_call("deleteText")

    async def highlight(self) -> None:
        """Draw a frame around the element, replacing any existing frame."""
        frame = await type(self).frame(self)
        await self._client.accessibility.draw_frame(frame.origin.x, frame.origin.y, frame.size.width, frame.size.height)

    async def scroll_to_visible(self) -> None:
        """Scroll until the element becomes fully visible."""
        await self.objc_call("scrollToVisible")

    async def press(self) -> None:
        """Activate/press the element."""
        await self.objc_call("press")

    async def long_press(self) -> None:
        """Long-press the element."""
        await self.objc_call("longPress")

    async def _iter(self) -> "AsyncGenerator[AXElement[DarwinSymbolT_co]]":
        current = await type(self).first_element(self)
        while current:
            yield current
            current = await current.next()

    def __aiter__(self) -> "AsyncIterator[AXElement[DarwinSymbolT_co]]":
        return self._iter()

    async def _element_for_attribute(self, axattribute: int, parameter: Any | None = None) -> Self | None:
        if parameter is None:
            result = await self.objc_call("elementForAttribute:", axattribute)
        else:
            result = await self.objc_call("elementForAttribute:parameter:", axattribute, parameter)
        return type(self)(result, self._client)

    async def _next_opaque(self, direction: AXDirection = AXDirection.Next) -> Self | None:
        element = self

        if not await type(element).is_accessibility_opaque_element_provider(element):
            element = await type(self).parent(self)

        if not element:
            return None

        element = await element._element_for_attribute(
            95225,
            await self._client.cf([
                direction,
                0,
                await (await self._client.symbols.objc_getClass("NSValue")).objc_call("valueWithRange:", 0x7FFFFFFF, 0),
                "AXAudit",
            ]),
        )

        if element:
            ui_element = await type(element).ui_element(element)
            if ui_element and await ui_element.objc_call("boolWithAXAttribute:", 2046):
                return await element._next_opaque()

        return element

    async def _next_elements_with_count(self, count: int) -> list[Self]:
        elements = await self.objc_call("nextElementsWithCount:", count)
        result = []
        for i in range(await elements.objc_call("count")):
            result.append(type(self)(await elements.objc_call("objectAtIndex:", i), self._client))
        return result

    async def _previous_elements_with_count(self, count: int) -> list[Self]:
        elements = await self.objc_call("previousElementsWithCount:", count)
        result = []
        for i in range(await elements.objc_call("count")):
            result.append(type(self)(await elements.objc_call("objectAtIndex:", i), self._client))
        return result

    async def _set_assistive_focus(self, focused: bool) -> None:
        await (await type(self).ui_element(self)).objc_call(
            "setAXAttribute:withObject:synchronous:",
            2018,
            await self._client.cf({"focused": int(focused), "assistiveTech": "AXAudit"}),
            0,
        )
        parent = await self._element_for_attribute(2092)
        if parent:
            await parent._set_assistive_focus(focused)

    async def next(
        self, direction: AXDirection = AXDirection.Next, cyclic: bool = False
    ) -> "AXElement[DarwinSymbolT_co] | None":
        """
        Return and scroll to the next element in the current view.

        This method was created by reversing [XADInspectorManager _nextElementNavigationInDirection:forElement:]
        so we don't really know much about the used consts.
        """
        next_opaque = await self._next_opaque(direction)

        if not await type(self).is_accessibility_opaque_element_provider(self) and next_opaque:
            return next_opaque

        if direction == AXDirection.Next:
            next_or_prev_list = await self._next_elements_with_count(1)
        else:
            next_or_prev_list = await self._previous_elements_with_count(1)

        if next_or_prev_list:
            result = next_or_prev_list[0]
            if await type(result).is_accessibility_opaque_element_provider(result):
                focused_element = await self._element_for_attribute(95226, self._client.cf("AXAudit"))
                if focused_element:
                    await focused_element._set_assistive_focus(False)
                await result._set_assistive_focus(False)
                result = await result._next_opaque(direction)

            if result and not await type(result).is_accessibility_opaque_element_provider(result):
                return result

        result = await self._next_opaque(direction)
        if result:
            return result

        if not await type(self).is_accessibility_opaque_element_provider(self):
            parent = await type(self).parent(self)
            if parent:
                return await parent.next(direction, cyclic=cyclic)

        if cyclic:
            app = await self._client.accessibility._get_primary_app()
            if direction == AXDirection.Next:
                return await type(app).first_element(app)
            return await type(app).last_element(app)

        return None

    async def compare_label(self, label: str, auto_scroll: bool = True, draw_frame: bool = True) -> bool:
        """
        Compare a label against this element's label.

        Optionally, scroll to the element and draw a highlight frame.
        """
        if auto_scroll:
            await self.scroll_to_visible()

        if draw_frame:
            await self.highlight()

        return await type(self).label(self) == label

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} (async)>"

    def __str__(self) -> str:
        return repr(self)


class Accessibility(ClientBound["IosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """Accessibility utilities and UI element discovery."""

    def __init__(self, client: "IosClient[DarwinSymbolT_co]") -> None:
        """Initialize accessibility frameworks and UI client."""
        self._client = client
        self._client.load_framework_lazy("AXRuntime")
        self._client.load_framework_lazy("AccessibilityUI")

    @cached_async_method
    async def _get_ui_client(self) -> DarwinSymbolT_co:
        return await (await (await self._client.symbols.objc_getClass("AXUIClient")).objc_call("alloc")).objc_call(
            "initWithIdentifier:serviceBundleName:",
            await self._client.cf("AXAuditAXUIClientIdentifier"),
            await self._client.cf("AXAuditAXUIService"),
        )

    async def _get_primary_app(self) -> AXElement[DarwinSymbolT_co]:
        if not await type(self).get_enabled(self):
            raise RpcAccessibilityTurnedOffError()
        primary_app = await (await self._client.symbols.objc_getClass("AXElement")).objc_call("primaryApp")
        if primary_app == 0:
            raise RpcFailedToGetPrimaryAppError()
        return self.axelement(primary_app)

    async def primary_app(self) -> AXElement[DarwinSymbolT_co]:
        """Return the primary app AXElement."""
        return await self._get_primary_app()

    async def get_enabled(self) -> bool:
        """Return True if accessibility automation is enabled."""
        return bool(
            await self._client.symbols._AXSApplicationAccessibilityEnabled()
            or await self._client.symbols._AXSAutomationEnabled()
        )

    async def set_enabled(self, value: bool) -> None:
        """Enable or disable accessibility automation."""
        await self._client.symbols._AXSSetAutomationEnabled(int(value))

    async def hide_frame(self) -> None:
        """Hide the accessibility highlight frame."""
        await self.draw_frame(0, 0, 0, 0)

    async def set_frame_style(self, value: int) -> None:
        """Set the highlight frame style."""
        await (await self._get_ui_client()).objc_call(
            "sendSynchronousMessage:withIdentifier:error:", await self._client.cf({"frameStyle": value}), 2, 0
        )

    async def draw_frame(self, x: float, y: float, width: float, height: float) -> None:
        """Draw a highlight frame at the given coordinates."""
        rect = {"frame": f" {{{{{x},{y}}}, {{{width},{height}}}}}"}
        await (await self._get_ui_client()).objc_call(
            "sendSynchronousMessage:withIdentifier:error:", await self._client.cf(rect), 1, 0
        )

    async def wait_for_element_by_label(
        self,
        label: str,
        auto_scroll: bool = True,
        draw_frame: bool = True,
        timeout: float = 5,
        direction: AXDirection = AXDirection.Next,
        displayed_only: bool = False,
    ) -> AXElement:
        """Wait for an element with the given label to appear."""
        start = time.time()
        while time.time() - start < timeout:
            try:
                return await self._get_element_by_label(
                    label,
                    auto_scroll=auto_scroll,
                    draw_frame=draw_frame,
                    direction=direction,
                    displayed_only=displayed_only,
                )
            except ElementNotFoundError:
                pass
            except AttributeError:
                pass
        raise ElementNotFoundError(
            f'failed to find AXElement by label: "{label}" after waiting for {timeout} seconds for it to load'
        )

    async def _get_element_by_label(
        self,
        label: str,
        auto_scroll: bool = True,
        draw_frame: bool = True,
        direction: AXDirection = AXDirection.Next,
        displayed_only: bool = False,
    ) -> AXElement:
        """Return an AXElement with the given label."""
        app = await self._get_primary_app()
        if direction == AXDirection.Next:
            element = await type(app).first_element(app)
            elements_list = await type(app).elements(app)
        elif direction == AXDirection.Previous:
            element = await type(app).last_element(app)
            elements_list = reversed(await type(app).elements(app))
        else:
            raise TypeError(f"bad value for: {direction}")

        if displayed_only:
            for element in elements_list:
                if await element.compare_label(label, auto_scroll=False, draw_frame=draw_frame):
                    return element
        else:
            while True:
                if element is None:
                    break

                if await element.compare_label(label, auto_scroll=auto_scroll, draw_frame=draw_frame):
                    if draw_frame:
                        await self.hide_frame()
                    return element

                element = await element.next(direction=direction)

        if draw_frame:
            await self.hide_frame()

        raise ElementNotFoundError(f'failed to find AXElement by label: "{label}"')

    async def press_elements_by_labels(
        self,
        labels: list[str],
        auto_scroll: bool = True,
        draw_frame: bool = True,
        timeout: float = 5,
        direction: AXDirection = AXDirection.Next,
        displayed_only: bool = False,
    ) -> None:
        """
        Press a sequence of labels in order.

        :param labels: Label list to press.
        :param auto_scroll: Scroll to each chosen element.
        :param draw_frame: Draw a frame over the current element.
        :param timeout: Timeout to wait for each element to appear.
        :param direction: Direction to search.
        :param displayed_only: Search only displayed elements.
        """
        for label in labels:
            await (
                await self.wait_for_element_by_label(
                    label,
                    auto_scroll=auto_scroll,
                    draw_frame=draw_frame,
                    timeout=timeout,
                    direction=direction,
                    displayed_only=displayed_only,
                )
            ).press()

            if draw_frame:
                await self.hide_frame()

    def axelement(self, symbol: int) -> AXElement:
        """Wrap a DarwinSymbol as an AXElement."""
        return AXElement(symbol, self._client)
