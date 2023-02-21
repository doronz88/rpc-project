import dataclasses
import time
from enum import IntEnum, IntFlag
from typing import List, Optional

from rpcclient.darwin.symbol import DarwinSymbol
from rpcclient.exceptions import ElementNotFoundError, FirstElementNotFoundError, LastElementNotFoundError, \
    MissingLibraryError, RpcAccessibilityTurnedOffError
from rpcclient.structs.consts import RTLD_NOW


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
            raise FirstElementNotFoundError('failed to get first element in hierarchy')

        if result.ui_element.objc_call('boolWithAXAttribute:', 2046):
            result = result._element_for_attribute(3000)
        return result

    @property
    def last_element(self):
        """ get last element in hierarchy """
        result = self._element_for_attribute(3016)
        if not result:
            raise LastElementNotFoundError('failed to get last element in hierarchy')

        if result.ui_element.objc_call('boolWithAXAttribute:', 2046):
            result = result._element_for_attribute(3016)
        return result

    @property
    def identifier(self) -> str:
        """ get element's identifier """
        return self.objc_call('identifier').py(encoding='utf8')

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
    def label(self) -> Optional[str]:
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
    def process_name(self) -> str:
        """ get element's process name """
        return self.objc_call('processName').py()

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

    @property
    def traits(self) -> AXTraits:
        """ get current element traits """
        return AXTraits(self.objc_call('traits').c_uint64)

    @property
    def elements(self) -> List['AXElement']:
        """ get all current displayed elements """
        result = []
        elements = self.objc_call('explorerElements')
        for i in range(elements.objc_call('count')):
            result.append(self._client.accessibility.axelement(elements.objc_call('objectAtIndex:', i)))
        return result

    def insert_text(self, text: str) -> None:
        """ insert text into currently editable element """
        self.objc_call('insertText:', self._client.cf(text))

    def delete_text(self) -> None:
        """ delete a character from currently editable element """
        self.objc_call('deleteText')

    def highlight(self) -> None:
        """ draw a frame around the element (replace the old one if existing) """
        frame = self.frame
        self._client.accessibility.draw_frame(frame.origin.x, frame.origin.y, frame.size.width, frame.size.height)

    def scroll_to_visible(self) -> None:
        """ scroll until element becomes fully visible """
        self.objc_call('scrollToVisible')

    def press(self) -> None:
        """ press element """
        self.objc_call('press')

    def long_press(self) -> None:
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

    def _next_opaque(self, direction=AXDirection.Next):
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

    def _next_elements_with_count(self, count: int) -> List['AXElement']:
        elements = self.objc_call('nextElementsWithCount:', count)
        result = []
        for i in range(elements.objc_call('count')):
            result.append(AXElement.create(elements.objc_call('objectAtIndex:', i), self._client))
        return result

    def _previous_elements_with_count(self, count: int) -> List['AXElement']:
        elements = self.objc_call('previousElementsWithCount:', count)
        result = []
        for i in range(elements.objc_call('count')):
            result.append(AXElement.create(elements.objc_call('objectAtIndex:', i), self._client))
        return result

    def _set_assistive_focus(self, focused: bool):
        self.ui_element.objc_call('setAXAttribute:withObject:synchronous:', 2018, self._client.cf({
            'focused': int(focused), 'assistiveTech': 'AXAudit'}), 0)
        parent = self._element_for_attribute(2092)
        if parent:
            parent._set_assistive_focus(focused)

    def next(self, direction=AXDirection.Next, cyclic=False):
        """
        Will get and scroll to the next element in the current view.

        This method was created by reversing [XADInspectorManager _nextElementNavigationInDirection:forElement:]
        so we don't really know much about the used consts.
        """
        next_opaque = self._next_opaque(direction)

        if not self.is_accessibility_opaque_element_provider and next_opaque:
            return next_opaque

        if direction == AXDirection.Next:
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
                return parent.next(direction, cyclic=cyclic)

        if cyclic:
            if direction == AXDirection.Next:
                return self._client.accessibility.primary_app.first_element
            return self._client.accessibility.primary_app.last_element

        return None

    def compare_label(self, label: str, auto_scroll=True, draw_frame=True) -> bool:
        """
        compares given label with the self's

        will auto_scroll into current label if required
        """
        if auto_scroll:
            self.scroll_to_visible()

        if draw_frame:
            self.highlight()

        if self.label == label:
            return True
        return False

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} LABEL:{self.label}>'

    def __str__(self) -> str:
        result = self.label
        return result if result else 'NO LABEL'


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
    def primary_app(self) -> AXElement:
        if not self.enabled:
            raise RpcAccessibilityTurnedOffError()
        return self.axelement(self._client.symbols.objc_getClass('AXElement').objc_call('primaryApp'))

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

    def wait_for_element_by_label(self, label: str, auto_scroll=True, draw_frame=True, timeout=5,
                                  direction=AXDirection.Next, displayed_only=False) -> AXElement:
        """ busy-wait for an element to become available """
        start = time.time()
        while time.time() - start < timeout:
            try:
                return self._get_element_by_label(label, auto_scroll=auto_scroll, draw_frame=draw_frame,
                                                  direction=direction, displayed_only=displayed_only)
            except ElementNotFoundError:
                pass
            except AttributeError:
                pass
        raise ElementNotFoundError(f'failed to find AXElement by label: "{label}" after waiting for {timeout} seconds '
                                   f'for it to load')

    def _get_element_by_label(self, label: str, auto_scroll=True, draw_frame=True, direction=AXDirection.Next,
                              displayed_only=False) -> AXElement:
        """ get an AXElement by given label """
        if direction == AXDirection.Next:
            element = self.primary_app.first_element
            elements_list = self.primary_app.elements
        elif direction == AXDirection.Previous:
            element = self.primary_app.last_element
            elements_list = reversed(self.primary_app.elements)
        else:
            raise TypeError(f'bad value for: {direction}')

        if displayed_only:
            for element in elements_list:
                if element.compare_label(label, auto_scroll=False, draw_frame=draw_frame):
                    return element
        else:
            while True:
                if element is None:
                    break

                if element.compare_label(label, auto_scroll=auto_scroll, draw_frame=draw_frame):
                    if draw_frame:
                        self.hide_frame()
                    return element

                element = element.next(direction=direction)

        if draw_frame:
            self.hide_frame()

        raise ElementNotFoundError(f'failed to find AXElement by label: "{label}"')

    def press_elements_by_labels(self, labels: List[str], auto_scroll=True, draw_frame=True, timeout=5,
                                 direction: AXDirection = AXDirection.Next, displayed_only=False):
        """
        press a sequence of labels
        :param labels: label list to press
        :param auto_scroll: scroll over the chosen element
        :param draw_frame: draw a frame over the current element
        :param timeout: timeout to wait for each element to appear
        :param direction: the direction of search
        :param displayed_only: search just in the displayed elements
        """
        for label in labels:
            self.wait_for_element_by_label(label, auto_scroll=auto_scroll, draw_frame=draw_frame, timeout=timeout,
                                           direction=direction, displayed_only=displayed_only).press()

            if draw_frame:
                self.hide_frame()

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

    def axelement(self, symbol: DarwinSymbol) -> AXElement:
        return AXElement.create(symbol, self._client)
