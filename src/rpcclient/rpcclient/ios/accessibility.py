import dataclasses
import time
from enum import IntEnum
from typing import List

from rpcclient.darwin.symbol import DarwinSymbol
from rpcclient.exceptions import MissingLibraryError, ElementNotFoundError, RpcAccessibilityTurnedOffError
from rpcclient.structs.consts import RTLD_NOW


class Direction(IntEnum):
    Next = 1
    Prev = 2


class FrameStyle(IntEnum):
    Default = 0
    Blue = 0
    Green = 1
    Yellow = 4
    LightGreen = 5
    Invisible = 6


@dataclasses.dataclass
class CGPoint:
    x: float
    y: float

    def __str__(self) -> str:
        return f'{{{self.x}, {self.y}}}'


@dataclasses.dataclass
class CGSize:
    width: float
    height: float

    def __str__(self) -> str:
        return f'{{{self.width}, {self.height}}}'


@dataclasses.dataclass
class CGRect:
    origin: CGPoint
    size: CGSize

    def __str__(self) -> str:
        return f'{{{self.origin}, {self.size}}}'


class AXElement(DarwinSymbol):
    """
    Wrapper to device's AXElement objective-c object.
    This object was written after reversing XADInspectorManager different methods.
    """

    @property
    def first_element(self):
        """ get first element in hierarchy """
        result = self._element_for_attribute(3000)
        if not result:
            raise ElementNotFoundError('failed to get first element in hierarchy')

        if result.ui_element.objc_call('boolWithAXAttribute:', 2046):
            result = result._element_for_attribute(3000)
        return result

    @property
    def last_element(self):
        """ get last element in hierarchy """
        result = self._element_for_attribute(3016)
        if not result:
            raise ElementNotFoundError('failed to get last element in hierarchy')

        if result.ui_element.objc_call('boolWithAXAttribute:', 2046):
            result = result._element_for_attribute(3016)
        return result

    @property
    def identifier(self) -> str:
        """ get element's identifier """
        return self.objc_call('label').py(encoding='utf8')

    @property
    def url(self) -> str:
        """ get element's url """
        return self.objc_call('url').py(encoding='utf8')

    @property
    def path(self) -> DarwinSymbol:
        """ get element's path """
        return self.objc_call('path')

    @property
    def frame(self) -> CGRect:
        """ get element's frame """
        d = self.objc_call('frame', return_raw=True).d
        return CGRect(origin=CGPoint(x=d[0], y=d[1]), size=CGSize(width=d[2], height=d[3]))

    @property
    def label(self) -> str:
        """ get element's label (actual displayed text) """
        return self.objc_call('label').py(encoding='utf8')

    @property
    def value(self) -> str:
        """ get element's value (actual set value) """
        return self.objc_call('value').py(encoding='utf8')

    @property
    def bundle_identifier(self) -> str:
        """ get element's bundle identifier """
        return self.objc_call('bundleId').py(encoding='utf8')

    @property
    def pid(self) -> int:
        """ get element's pid """
        return self.objc_call('pid').c_uint16

    @property
    def screen_locked(self) -> bool:
        """ get screen lock state """
        return self.objc_call('isScreenLocked') == 1

    @property
    def is_accessibility_opaque_element_provider(self) -> bool:
        return self.objc_call('isAccessibilityOpaqueElementProvider') != 0

    @property
    def parent(self):
        tmp = self._element_for_attribute(2066)
        if tmp:
            return tmp

        tmp = self._element_for_attribute(2092)
        if tmp:
            return tmp.parent

        return None

    @property
    def ui_element(self) -> DarwinSymbol:
        """ get encapsulated AXUIElement """
        return self.objc_call('uiElement')

    def highlight(self):
        frame = self.frame
        self._client.accessibility.draw_frame(frame.origin.x, frame.origin.y, frame.size.width, frame.size.height)

    def scroll_to_visible(self):
        """ scroll until element becomes fully visible """
        self.objc_call('scrollToVisible')

    def press(self):
        """ press element """
        self.objc_call('press')

    def long_press(self):
        """ long press element """
        self.objc_call('longPress')

    def __iter__(self):
        current = self.first_element
        while current:
            yield current
            current = current.next()

    def _element_for_attribute(self, axattribute: int, parameter=None):
        if parameter is None:
            result = self.objc_call('elementForAttribute:', axattribute)
        else:
            result = self.objc_call('elementForAttribute:parameter:', axattribute, parameter)
        return AXElement.create(result, self._client)

    def _next_opaque(self, direction=Direction.Next):
        element = self

        if not element.is_accessibility_opaque_element_provider:
            element = self.parent

        if not element:
            return

        element = element._element_for_attribute(95225, self._client.cf([
            direction,
            0,
            self._client.symbols.objc_getClass('NSValue').objc_call('valueWithRange:', 0x7fffffff, 0),
            'AXAudit'
        ]))

        if element:
            ui_element = element.ui_element
            if ui_element and ui_element.objc_call('boolWithAXAttribute:', 2046):
                return element._next_opaque

        return element

    def _next_elements_with_count(self, count: int):
        return [AXElement.create(e, self._client) for e in self.objc_call('nextElementsWithCount:', count).py()]

    def _previous_elements_with_count(self, count: int):
        return [AXElement.create(e, self._client) for e in self.objc_call('previousElementsWithCount:', count).py()]

    def _set_assistive_focus(self, focused: bool):
        self.ui_element.objc_call('setAXAttribute:withObject:synchronous:', 2018, self._client.cf({
            'focused': int(focused), 'assistiveTech': 'AXAudit'}), 0)
        parent = self._element_for_attribute(2092)
        if parent:
            parent._set_assistive_focus(focused)

    def next(self, direction=Direction.Next, cyclic=False):
        """
        Will get and scroll to the next element in the current view.

        This method was created by reversing [XADInspectorManager _nextElementNavigationInDirection:forElement:]
        so we don't really know much about the used consts.
        """
        next_opaque = self._next_opaque(direction)

        if not self.is_accessibility_opaque_element_provider and next_opaque:
            return next_opaque

        if direction == Direction.Next:
            next_or_prev_list = self._next_elements_with_count(1)
        else:
            next_or_prev_list = self._previous_elements_with_count(1)

        if next_or_prev_list:
            result = next_or_prev_list[0]
            if result.is_accessibility_opaque_element_provider:
                focused_element = self._element_for_attribute(95226, self._client.cf('AXAudit'))
                if focused_element:
                    focused_element._set_assistive_focus(False)
                result._set_assistive_focus(False)
                result = result._next_opaque(direction)

            if result and not result.is_accessibility_opaque_element_provider:
                return result

        result = self._next_opaque(direction)
        if result:
            return result

        if not self.is_accessibility_opaque_element_provider:
            parent = self.parent
            if parent:
                return parent.next(direction)

        if cyclic:
            if direction == Direction.Next:
                return self.first_element
            return self.last_element

        return None


class Accessibility:
    """ Accessibility utils """

    def __init__(self, client):
        """
        :param rpcclient.darwin.client.DarwinClient client:
        """
        self._client = client
        self._load_ax_runtime()
        self._load_accessibility_ui()
        self._ui_client = client.symbols.objc_getClass('AXUIClient').objc_call('alloc').objc_call(
            'initWithIdentifier:serviceBundleName:',
            client.cf('AXAuditAXUIClientIdentifier'),
            client.cf('AXAuditAXUIService'))

    @property
    def primary_app(self):
        if not self.enabled:
            raise RpcAccessibilityTurnedOffError()
        return self._axelement(self._client.symbols.objc_getClass('AXElement').objc_call('primaryApp'))

    @property
    def enabled(self) -> bool:
        return bool(self._client.symbols._AXSApplicationAccessibilityEnabled() or
                    self._client.symbols._AXSAutomationEnabled())

    @enabled.setter
    def enabled(self, value: bool):
        self._client.symbols._AXSSetAutomationEnabled(int(value))

    def hide_frame(self):
        self.draw_frame(0, 0, 0, 0)

    def set_frame_style(self, value: int):
        self._ui_client.objc_call('sendSynchronousMessage:withIdentifier:error:',
                                  self._client.cf({'frameStyle': value}), 2, 0)

    def draw_frame(self, x: float, y: float, width: float, height: float):
        rect = {'frame': f' {{{{{x},{y}}}, {{{width},{height}}}}}'}
        self._ui_client.objc_call('sendSynchronousMessage:withIdentifier:error:', self._client.cf(rect), 1, 0)

    def get_element_by_label(self, label: str, auto_scroll=True, draw_frame=True) -> AXElement:
        """ get an AXElement by given label """
        for element in self.primary_app:
            if auto_scroll:
                element.scroll_to_visible()

            if element.label == label:
                return element

            if draw_frame:
                element.highlight()

        if draw_frame:
            self.hide_frame()

        raise ElementNotFoundError(f'failed to find AXElement by label: "{label}"')

    def press_elements_by_labels(self, labels: List[str], interval=2, draw_frame=True):
        """
        press a sequence of labels
        :param labels: label list to press
        :param interval: interval in seconds to sleep between each press
        :param draw_frame: draw a frame over the current element
        """
        for label in labels:
            self.get_element_by_label(label, draw_frame=draw_frame).press()

            if draw_frame:
                self.hide_frame()

            # wait before next interation
            time.sleep(interval)

    def _load_ax_runtime(self):
        options = [
            '/System/Library/PrivateFrameworks/AXRuntime.framework/AXRuntime',
        ]
        for option in options:
            if self._client.dlopen(option, RTLD_NOW):
                return
        raise MissingLibraryError('failed to load AXRuntime')

    def _load_accessibility_ui(self):
        options = [
            '/System/Library/PrivateFrameworks/AccessibilityUI.framework/AccessibilityUI',
        ]
        for option in options:
            if self._client.dlopen(option, RTLD_NOW):
                return
        raise MissingLibraryError('failed to load AccessibilityUI')

    def _axelement(self, symbol: DarwinSymbol):
        return AXElement.create(symbol, self._client)
