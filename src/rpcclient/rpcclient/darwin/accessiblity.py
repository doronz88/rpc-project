import time
from typing import List

from rpcclient.darwin.symbol import DarwinSymbol
from rpcclient.exceptions import MissingLibraryError, ElementNotFoundError
from rpcclient.structs.consts import RTLD_NOW

DIRECTION_NEXT = 1
DIRECTION_PREV = 1


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
    def label(self) -> str:
        """ get element's label (actual displayed text) """
        return self.objc_call('label').py(encoding='utf8')

    @property
    def value(self) -> str:
        """ get element's value (actual set value) """
        return self.objc_call('value').py(encoding='utf8')

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
            current = current._next()

    def _element_for_attribute(self, axattribute: int, parameter=None):
        if parameter is None:
            result = self.objc_call('elementForAttribute:', axattribute)
        else:
            result = self.objc_call('elementForAttribute:parameter:', axattribute, parameter)
        return AXElement.create(result, self._client)

    def _next_opaque(self, direction=DIRECTION_NEXT):
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

    def _next(self, direction=DIRECTION_NEXT, cyclic=False):
        """
        Will get and scroll to the next element in the current view.

        This method was created by reversing [XADInspectorManager _nextElementNavigationInDirection:forElement:]
        so we don't really know much about the used consts.
        """
        next_opaque = self._next_opaque(direction)

        if not self.is_accessibility_opaque_element_provider and next_opaque:
            return next_opaque

        if direction == DIRECTION_NEXT:
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
                return parent._next(direction)

        if cyclic:
            if direction == DIRECTION_NEXT:
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

    @property
    def primary_app(self):
        return self._axelement(self._client.symbols.objc_getClass('AXElement').objc_call('primaryApp'))

    def get_element_by_label(self, label: str) -> AXElement:
        """ get an AXElement by given label """
        for element in self.primary_app:
            if element.label == label:
                return element
        raise ElementNotFoundError(f'failed to find AXElement by label: "{label}"')

    def press_labels(self, labels: List[str], interval=1):
        """
        press a sequence of labels
        :param labels: label list to press
        :param interval: interval in seconds to sleep between each press
        """
        for label in labels:
            self.get_element_by_label(label).press()

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

    def _axelement(self, symbol: DarwinSymbol):
        return AXElement.create(symbol, self._client)
