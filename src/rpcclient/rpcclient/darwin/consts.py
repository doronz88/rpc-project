from enum import Enum, IntEnum, IntFlag, auto

kCFAllocatorDefault = 0
MACH_PORT_NULL = 0


class AVAudioSessionRouteSharingPolicy(IntEnum):
    Default = 0
    LongFormAudio = 1
    Independent = 2
    LongFormVideo = 3
    LongForm = LongFormAudio


class AVAudioSessionCategoryOptions(IntFlag):
    MixWithOthers = 0x1
    DuckOthers = 0x2
    AllowBluetooth = 0x4
    DefaultToSpeaker = 0x8
    InterruptSpokenAudioAndMixWithOthers = 0x11
    AllowBluetoothA2DP = 0x20
    AllowAirPlay = 0x40
    OverrideMutedMicrophoneInterruption = 0x80


class CFPropertyListFormat(IntEnum):
    kCFPropertyListOpenStepFormat = 1
    kCFPropertyListXMLFormat_v1_0 = 100
    kCFPropertyListBinaryFormat_v1_0 = 200


class CFPropertyListMutabilityOptions(IntEnum):
    kCFPropertyListImmutable = 0
    kCFPropertyListMutableContainers = 1 << 0,
    kCFPropertyListMutableContainersAndLeaves = 1 << 1,


class IOPMUserActiveType(IntEnum):
    kIOPMUserActiveLocal = 0  # User is local on the system
    kIOPMUserActiveRemote = 1  # Remote User connected to the system


kIOPMAssertionLevelOff = 0
kIOPMAssertionLevelOn = 255

# Types from MacTypes.h

# Basic C types
kCFNumberSInt8Type = 1
kCFNumberSInt16Type = 2
kCFNumberSInt32Type = 3
kCFNumberSInt64Type = 4
kCFNumberFloat32Type = 5
kCFNumberFloat64Type = 6  # 64-bit IEEE 754

# Other
kCFNumberCharType = 7
kCFNumberShortType = 8
kCFNumberIntType = 9
kCFNumberLongType = 10
kCFNumberLongLongType = 11
kCFNumberFloatType = 12
kCFNumberDoubleType = 13
kCFNumberCFIndexType = 14
kCFNumberMaxType = 14

# Types from IOKitKeys.h

# registry plane names
kIOServicePlane = 'IOService'
kIOPowerPlane = 'IOPower'
kIODeviceTreePlane = 'IODeviceTree'
kIOAudioPlane = 'IOAudio'
kIOFireWirePlane = 'IOFireWire'
kIOUSBPlane = 'IOUSB'

VM_REGION_INFO_MAX = 1024
VM_REGION_BASIC_INFO_64 = 9
VM_REGION_BASIC_INFO = 10

VM_FLAGS_FIXED = 0x0000
VM_FLAGS_ANYWHERE = 0x0001
VM_FLAGS_PURGABLE = 0x0002
VM_FLAGS_NO_PMAP_CHECK = 0x0004
VM_FLAGS_OVERWRITE = 0x0008

TASK_DYLD_INFO = 17

THREAD_BASIC_INFO = 3

# the i386_xxxx form is kept for legacy purposes since these types
# are externally known... eventually they should be deprecated.
# our internal implementation has moved to the following naming convention
#
#   x86_xxxx32 names are used to deal with 32 bit states
#   x86_xxxx64 names are used to deal with 64 bit states
#   x86_xxxx   names are used to deal with either 32 or 64 bit states via a self-describing mechanism
#

# these are the legacy names which should be deprecated in the future
# they are externally known which is the only reason we don't just get
# rid of them
#
i386_THREAD_STATE = 1
i386_FLOAT_STATE = 2
i386_EXCEPTION_STATE = 3

# THREAD_STATE_FLAVOR_LIST 0
# 	these are the supported flavors
#
x86_THREAD_STATE32 = 1
x86_FLOAT_STATE32 = 2
x86_EXCEPTION_STATE32 = 3
x86_THREAD_STATE64 = 4
x86_FLOAT_STATE64 = 5
x86_EXCEPTION_STATE64 = 6
x86_THREAD_STATE = 7
x86_FLOAT_STATE = 8
x86_EXCEPTION_STATE = 9
x86_DEBUG_STATE32 = 10
x86_DEBUG_STATE64 = 11
x86_DEBUG_STATE = 12
THREAD_STATE_NONE = 13


class ARMThreadFlavors(Enum):
    ARM_THREAD_STATE = 1
    ARM_VFP_STATE = 2
    ARM_EXCEPTION_STATE = 3
    ARM_DEBUG_STATE = 4
    ARN_THREAD_STATE_NONE = 5
    ARM_THREAD_STATE64 = 6
    ARM_EXCEPTION_STATE64 = 7


class CFStringEncoding(Enum):
    kCFStringEncodingMacRoman = 0
    kCFStringEncodingWindowsLatin1 = 0x0500  # ANSI codepage 1252
    kCFStringEncodingISOLatin1 = 0x0201  # ISO 8859-1
    kCFStringEncodingNextStepLatin = 0x0B01  # NextStep encoding
    kCFStringEncodingASCII = 0x0600  # 0..127 (in creating CFString values greater than 0x7F are

    # kTextEncodingUnicodeDefault  + kTextEncodingDefaultFormat (aka kUnicode16BitFormat)
    kCFStringEncodingUnicode = 0x0100

    kCFStringEncodingUTF8 = 0x08000100  # kTextEncodingUnicodeDefault + kUnicodeUTF8Format
    kCFStringEncodingNonLossyASCII = 0x0BFF  # 7bit Unicode variants used by Cocoa & Java

    # kTextEncodingUnicodeDefault + kUnicodeUTF16Format (alias of kCFStringEncodingUnicode)
    kCFStringEncodingUTF16 = 0x0100

    kCFStringEncodingUTF16BE = 0x10000100  # kTextEncodingUnicodeDefault + kUnicodeUTF16BEFormat
    kCFStringEncodingUTF16LE = 0x14000100  # kTextEncodingUnicodeDefault + kUnicodeUTF16LEFormat

    kCFStringEncodingUTF32 = 0x0c000100  # kTextEncodingUnicodeDefault + kUnicodeUTF32Format
    kCFStringEncodingUTF32BE = 0x18000100  # kTextEncodingUnicodeDefault + kUnicodeUTF32BEFormat
    kCFStringEncodingUTF32LE = 0x1c000100  # kTextEncodingUnicodeDefault + kUnicodeUTF32LEFormat


class NSStringEncoding(Enum):
    NSASCIIStringEncoding = 1  # 0..127 only
    NSNEXTSTEPStringEncoding = 2
    NSJapaneseEUCStringEncoding = 3
    NSUTF8StringEncoding = 4
    NSISOLatin1StringEncoding = 5
    NSSymbolStringEncoding = 6
    NSNonLossyASCIIStringEncoding = 7
    NSShiftJISStringEncoding = 8  # kCFStringEncodingDOSJapanese
    NSISOLatin2StringEncoding = 9
    NSUnicodeStringEncoding = 10
    NSWindowsCP1251StringEncoding = 11  # Cyrillic; same as AdobeStandardCyrillic
    NSWindowsCP1252StringEncoding = 12  # WinLatin1
    NSWindowsCP1253StringEncoding = 13  # Greek
    NSWindowsCP1254StringEncoding = 14  # Turkish
    NSWindowsCP1250StringEncoding = 15  # WinLatin2
    NSISO2022JPStringEncoding = 21  # ISO 2022 Japanese encoding for e-mail
    NSMacOSRomanStringEncoding = 30

    NSUTF16StringEncoding = NSUnicodeStringEncoding  # An alias for NSUnicodeStringEncoding

    NSUTF16BigEndianStringEncoding = 0x90000100  # NSUTF16StringEncoding encoding with explicit endianness specified
    NSUTF16LittleEndianStringEncoding = 0x94000100  # NSUTF16StringEncoding encoding with explicit endianness specified

    NSUTF32StringEncoding = 0x8c000100
    NSUTF32BigEndianStringEncoding = 0x98000100  # NSUTF32StringEncoding encoding with explicit endianness specified
    NSUTF32LittleEndianStringEncoding = 0x9c000100  # NSUTF32StringEncoding encoding with explicit endianness specified


# Taken from:
# https://opensource.apple.com/source/IOHIDFamily/IOHIDFamily-421.6/IOHIDFamily/IOHIDUsageTables.h.auto.html

kHIDPage_Undefined = 0x00
kHIDPage_GenericDesktop = 0x01
kHIDPage_Simulation = 0x02
kHIDPage_VR = 0x03
kHIDPage_Sport = 0x04
kHIDPage_Game = 0x05
# Reserved 0x06

# USB Device Class Definition for Human Interface Devices (HID). Note: the usage type for all key codes
# is Selector (Sel).
kHIDPage_KeyboardOrKeypad = 0x07
kHIDPage_LEDs = 0x08
kHIDPage_Button = 0x09
kHIDPage_Ordinal = 0x0A
kHIDPage_Telephony = 0x0B
kHIDPage_Consumer = 0x0C
kHIDPage_Digitizer = 0x0D
# Reserved 0x0E
kHIDPage_PID = 0x0F  # USB Physical Interface Device definitions for force feedback and related devices.
kHIDPage_Unicode = 0x10
# Reserved 0x11 - 0x13
kHIDPage_AlphanumericDisplay = 0x14
# Reserved 0x15 - 0x7F
# Monitor 0x80 - 0x83	 USB Device Class Definition for Monitor Devices
# Power 0x84 - 0x87	 USB Device Class Definition for Power Devices
kHIDPage_PowerDevice = 0x84  # Power Device Page
kHIDPage_BatterySystem = 0x85  # Battery System Page
# Reserved 0x88 - 0x8B
kHIDPage_BarCodeScanner = 0x8C  # (Point of Sale) USB Device Class Definition for Bar Code Scanner Devices
kHIDPage_WeighingDevice = 0x8D  # (Point of Sale) USB Device Class Definition for Weighing Devices
kHIDPage_Scale = 0x8D  # (Point of Sale) USB Device Class Definition for Scale Devices
kHIDPage_MagneticStripeReader = 0x8E
# ReservedPointofSalepages 0x8F
kHIDPage_CameraControl = 0x90  # USB Device Class Definition for Image Class Devices
kHIDPage_Arcade = 0x91  # OAAF Definitions for arcade and coinop related Devices
# Reserved 0x92 - 0xFEFF
# VendorDefined 0xFF00 - 0xFFFF
kHIDPage_VendorDefinedStart = 0xFF00

kHIDUsage_Undefined = 0x00

kHIDUsage_KeyboardErrorRollOver = 0x01  # ErrorRollOver
kHIDUsage_KeyboardPOSTFail = 0x02  # POSTFail
kHIDUsage_KeyboardErrorUndefined = 0x03  # ErrorUndefined
kHIDUsage_KeyboardA = 0x04  # a or A
kHIDUsage_KeyboardB = 0x05  # b or B
kHIDUsage_KeyboardC = 0x06  # c or C
kHIDUsage_KeyboardD = 0x07  # d or D
kHIDUsage_KeyboardE = 0x08  # e or E
kHIDUsage_KeyboardF = 0x09  # f or F
kHIDUsage_KeyboardG = 0x0A  # g or G
kHIDUsage_KeyboardH = 0x0B  # h or H
kHIDUsage_KeyboardI = 0x0C  # i or I
kHIDUsage_KeyboardJ = 0x0D  # j or J
kHIDUsage_KeyboardK = 0x0E  # k or K
kHIDUsage_KeyboardL = 0x0F  # l or L
kHIDUsage_KeyboardM = 0x10  # m or M
kHIDUsage_KeyboardN = 0x11  # n or N
kHIDUsage_KeyboardO = 0x12  # o or O
kHIDUsage_KeyboardP = 0x13  # p or P
kHIDUsage_KeyboardQ = 0x14  # q or Q
kHIDUsage_KeyboardR = 0x15  # r or R
kHIDUsage_KeyboardS = 0x16  # s or S
kHIDUsage_KeyboardT = 0x17  # t or T
kHIDUsage_KeyboardU = 0x18  # u or U
kHIDUsage_KeyboardV = 0x19  # v or V
kHIDUsage_KeyboardW = 0x1A  # w or W
kHIDUsage_KeyboardX = 0x1B  # x or X
kHIDUsage_KeyboardY = 0x1C  # y or Y
kHIDUsage_KeyboardZ = 0x1D  # z or Z
kHIDUsage_Keyboard1 = 0x1E  # 1 or !
kHIDUsage_Keyboard2 = 0x1F  # 2 or @
kHIDUsage_Keyboard3 = 0x20  # 3 or #
kHIDUsage_Keyboard4 = 0x21  # 4 or $
kHIDUsage_Keyboard5 = 0x22  # 5 or %
kHIDUsage_Keyboard6 = 0x23  # 6 or ^
kHIDUsage_Keyboard7 = 0x24  # 7 or &
kHIDUsage_Keyboard8 = 0x25  # 8 or *
kHIDUsage_Keyboard9 = 0x26  # 9 or (
kHIDUsage_Keyboard0 = 0x27  # 0 or )
kHIDUsage_KeyboardReturnOrEnter = 0x28  # Return (Enter)
kHIDUsage_KeyboardEscape = 0x29  # Escape
kHIDUsage_KeyboardDeleteOrBackspace = 0x2A  # Delete (Backspace)
kHIDUsage_KeyboardTab = 0x2B  # Tab
kHIDUsage_KeyboardSpacebar = 0x2C  # Spacebar
kHIDUsage_KeyboardHyphen = 0x2D  # - or _
kHIDUsage_KeyboardEqualSign = 0x2E  # = or +
kHIDUsage_KeyboardOpenBracket = 0x2F  # [ or {
kHIDUsage_KeyboardCloseBracket = 0x30  # ] or }
kHIDUsage_KeyboardBackslash = 0x31  # \ or |
kHIDUsage_KeyboardNonUSPound = 0x32  # Non-US # or _
kHIDUsage_KeyboardSemicolon = 0x33  # ; or :
kHIDUsage_KeyboardQuote = 0x34  # ' or "
kHIDUsage_KeyboardGraveAccentAndTilde = 0x35  # Grave Accent and Tilde
kHIDUsage_KeyboardComma = 0x36  # or <
kHIDUsage_KeyboardPeriod = 0x37  # . or >
kHIDUsage_KeyboardSlash = 0x38  # / or ?
kHIDUsage_KeyboardCapsLock = 0x39  # Caps Lock
kHIDUsage_KeyboardF1 = 0x3A  # F1
kHIDUsage_KeyboardF2 = 0x3B  # F2
kHIDUsage_KeyboardF3 = 0x3C  # F3
kHIDUsage_KeyboardF4 = 0x3D  # F4
kHIDUsage_KeyboardF5 = 0x3E  # F5
kHIDUsage_KeyboardF6 = 0x3F  # F6
kHIDUsage_KeyboardF7 = 0x40  # F7
kHIDUsage_KeyboardF8 = 0x41  # F8
kHIDUsage_KeyboardF9 = 0x42  # F9
kHIDUsage_KeyboardF10 = 0x43  # F10
kHIDUsage_KeyboardF11 = 0x44  # F11
kHIDUsage_KeyboardF12 = 0x45  # F12
kHIDUsage_KeyboardPrintScreen = 0x46  # Print Screen
kHIDUsage_KeyboardScrollLock = 0x47  # Scroll Lock
kHIDUsage_KeyboardPause = 0x48  # Pause
kHIDUsage_KeyboardInsert = 0x49  # Insert
kHIDUsage_KeyboardHome = 0x4A  # Home
kHIDUsage_KeyboardPageUp = 0x4B  # Page Up
kHIDUsage_KeyboardDeleteForward = 0x4C  # Delete Forward
kHIDUsage_KeyboardEnd = 0x4D  # End
kHIDUsage_KeyboardPageDown = 0x4E  # Page Down
kHIDUsage_KeyboardRightArrow = 0x4F  # Right Arrow
kHIDUsage_KeyboardLeftArrow = 0x50  # Left Arrow
kHIDUsage_KeyboardDownArrow = 0x51  # Down Arrow
kHIDUsage_KeyboardUpArrow = 0x52  # Up Arrow
kHIDUsage_KeypadNumLock = 0x53  # Keypad NumLock or Clear
kHIDUsage_KeypadSlash = 0x54  # Keypad /
kHIDUsage_KeypadAsterisk = 0x55  # Keypad *
kHIDUsage_KeypadHyphen = 0x56  # Keypad -
kHIDUsage_KeypadPlus = 0x57  # Keypad +
kHIDUsage_KeypadEnter = 0x58  # Keypad Enter
kHIDUsage_Keypad1 = 0x59  # Keypad 1 or End
kHIDUsage_Keypad2 = 0x5A  # Keypad 2 or Down Arrow
kHIDUsage_Keypad3 = 0x5B  # Keypad 3 or Page Down
kHIDUsage_Keypad4 = 0x5C  # Keypad 4 or Left Arrow
kHIDUsage_Keypad5 = 0x5D  # Keypad 5
kHIDUsage_Keypad6 = 0x5E  # Keypad 6 or Right Arrow
kHIDUsage_Keypad7 = 0x5F  # Keypad 7 or Home
kHIDUsage_Keypad8 = 0x60  # Keypad 8 or Up Arrow
kHIDUsage_Keypad9 = 0x61  # Keypad 9 or Page Up
kHIDUsage_Keypad0 = 0x62  # Keypad 0 or Insert
kHIDUsage_KeypadPeriod = 0x63  # Keypad . or Delete
kHIDUsage_KeyboardNonUSBackslash = 0x64  # Non-US \ or |
kHIDUsage_KeyboardApplication = 0x65  # Application
kHIDUsage_KeyboardPower = 0x66  # Power
kHIDUsage_KeypadEqualSign = 0x67  # Keypad =
kHIDUsage_KeyboardF13 = 0x68  # F13
kHIDUsage_KeyboardF14 = 0x69  # F14
kHIDUsage_KeyboardF15 = 0x6A  # F15
kHIDUsage_KeyboardF16 = 0x6B  # F16
kHIDUsage_KeyboardF17 = 0x6C  # F17
kHIDUsage_KeyboardF18 = 0x6D  # F18
kHIDUsage_KeyboardF19 = 0x6E  # F19
kHIDUsage_KeyboardF20 = 0x6F  # F20
kHIDUsage_KeyboardF21 = 0x70  # F21
kHIDUsage_KeyboardF22 = 0x71  # F22
kHIDUsage_KeyboardF23 = 0x72  # F23
kHIDUsage_KeyboardF24 = 0x73  # F24
kHIDUsage_KeyboardExecute = 0x74  # Execute
kHIDUsage_KeyboardHelp = 0x75  # Help
kHIDUsage_KeyboardMenu = 0x76  # Menu
kHIDUsage_KeyboardSelect = 0x77  # Select
kHIDUsage_KeyboardStop = 0x78  # Stop
kHIDUsage_KeyboardAgain = 0x79  # Again
kHIDUsage_KeyboardUndo = 0x7A  # Undo
kHIDUsage_KeyboardCut = 0x7B  # Cut
kHIDUsage_KeyboardCopy = 0x7C  # Copy
kHIDUsage_KeyboardPaste = 0x7D  # Paste
kHIDUsage_KeyboardFind = 0x7E  # Find
kHIDUsage_KeyboardMute = 0x7F  # Mute
kHIDUsage_KeyboardVolumeUp = 0x80  # Volume Up
kHIDUsage_KeyboardVolumeDown = 0x81  # Volume Down
kHIDUsage_KeyboardLockingCapsLock = 0x82  # Locking Caps Lock
kHIDUsage_KeyboardLockingNumLock = 0x83  # Locking Num Lock
kHIDUsage_KeyboardLockingScrollLock = 0x84  # Locking Scroll Lock
kHIDUsage_KeypadComma = 0x85  # Keypad Comma
kHIDUsage_KeypadEqualSignAS400 = 0x86  # Keypad Equal Sign for AS/400
kHIDUsage_KeyboardInternational1 = 0x87  # International1
kHIDUsage_KeyboardInternational2 = 0x88  # International2
kHIDUsage_KeyboardInternational3 = 0x89  # International3
kHIDUsage_KeyboardInternational4 = 0x8A  # International4
kHIDUsage_KeyboardInternational5 = 0x8B  # International5
kHIDUsage_KeyboardInternational6 = 0x8C  # International6
kHIDUsage_KeyboardInternational7 = 0x8D  # International7
kHIDUsage_KeyboardInternational8 = 0x8E  # International8
kHIDUsage_KeyboardInternational9 = 0x8F  # International9
kHIDUsage_KeyboardLANG1 = 0x90  # LANG1
kHIDUsage_KeyboardLANG2 = 0x91  # LANG2
kHIDUsage_KeyboardLANG3 = 0x92  # LANG3
kHIDUsage_KeyboardLANG4 = 0x93  # LANG4
kHIDUsage_KeyboardLANG5 = 0x94  # LANG5
kHIDUsage_KeyboardLANG6 = 0x95  # LANG6
kHIDUsage_KeyboardLANG7 = 0x96  # LANG7
kHIDUsage_KeyboardLANG8 = 0x97  # LANG8
kHIDUsage_KeyboardLANG9 = 0x98  # LANG9
kHIDUsage_KeyboardAlternateErase = 0x99  # AlternateErase
kHIDUsage_KeyboardSysReqOrAttention = 0x9A  # SysReq/Attention
kHIDUsage_KeyboardCancel = 0x9B  # Cancel
kHIDUsage_KeyboardClear = 0x9C  # Clear
kHIDUsage_KeyboardPrior = 0x9D  # Prior
kHIDUsage_KeyboardReturn = 0x9E  # Return
kHIDUsage_KeyboardSeparator = 0x9F  # Separator
kHIDUsage_KeyboardOut = 0xA0  # Out
kHIDUsage_KeyboardOper = 0xA1  # Oper
kHIDUsage_KeyboardClearOrAgain = 0xA2  # Clear/Again
kHIDUsage_KeyboardCrSelOrProps = 0xA3  # CrSel/Props
kHIDUsage_KeyboardExSel = 0xA4  # ExSel
# 0xA5-0xDF Reserved
kHIDUsage_KeyboardLeftControl = 0xE0  # Left Control
kHIDUsage_KeyboardLeftShift = 0xE1  # Left Shift
kHIDUsage_KeyboardLeftAlt = 0xE2  # Left Alt
kHIDUsage_KeyboardLeftGUI = 0xE3  # Left GUI
kHIDUsage_KeyboardRightControl = 0xE4  # Right Control
kHIDUsage_KeyboardRightShift = 0xE5  # Right Shift
kHIDUsage_KeyboardRightAlt = 0xE6  # Right Alt
kHIDUsage_KeyboardRightGUI = 0xE7  # Right GUI
# 0xE8-0xFFFF Reserved
kHIDUsage_Keyboard_Reserved = 0xFFFF

kHIDUsage_Csmr_ConsumerControl = 0x01  # Application Collection
kHIDUsage_Csmr_NumericKeyPad = 0x02  # Named Array
kHIDUsage_Csmr_ProgrammableButtons = 0x03  # Named Array
# 0x03 - 0x1F Reserved
kHIDUsage_Csmr_Plus10 = 0x20  # One-Shot Control
kHIDUsage_Csmr_Plus100 = 0x21  # One-Shot Control
kHIDUsage_Csmr_AMOrPM = 0x22  # One-Shot Control
# 0x23 - 0x3F Reserved
kHIDUsage_Csmr_Power = 0x30  # On/Off Control
kHIDUsage_Csmr_Reset = 0x31  # One-Shot Control
kHIDUsage_Csmr_Sleep = 0x32  # One-Shot Control
kHIDUsage_Csmr_SleepAfter = 0x33  # One-Shot Control
kHIDUsage_Csmr_SleepMode = 0x34  # Re-Trigger Control
kHIDUsage_Csmr_Illumination = 0x35  # On/Off Control
kHIDUsage_Csmr_FunctionButtons = 0x36  # Named Array
# 0x37 - 0x3F Reserved
kHIDUsage_Csmr_Menu = 0x40  # On/Off Control
kHIDUsage_Csmr_MenuPick = 0x41  # One-Shot Control
kHIDUsage_Csmr_MenuUp = 0x42  # One-Shot Control
kHIDUsage_Csmr_MenuDown = 0x43  # One-Shot Control
kHIDUsage_Csmr_MenuLeft = 0x44  # One-Shot Control
kHIDUsage_Csmr_MenuRight = 0x45  # One-Shot Control
kHIDUsage_Csmr_MenuEscape = 0x46  # One-Shot Control
kHIDUsage_Csmr_MenuValueIncrease = 0x47  # One-Shot Control
kHIDUsage_Csmr_MenuValueDecrease = 0x48  # One-Shot Control
# 0x49 - 0x5F Reserved
kHIDUsage_Csmr_DataOnScreen = 0x60  # On/Off Control
kHIDUsage_Csmr_ClosedCaption = 0x61  # On/Off Control
kHIDUsage_Csmr_ClosedCaptionSelect = 0x62  # Selector
kHIDUsage_Csmr_VCROrTV = 0x63  # On/Off Control
kHIDUsage_Csmr_BroadcastMode = 0x64  # One-Shot Control
kHIDUsage_Csmr_Snapshot = 0x65  # One-Shot Control
kHIDUsage_Csmr_Still = 0x66  # One-Shot Control
# 0x67 - 0x7F Reserved
kHIDUsage_Csmr_Selection = 0x80  # Named Array
kHIDUsage_Csmr_Assign = 0x81  # Selector
kHIDUsage_Csmr_ModeStep = 0x82  # One-Shot Control
kHIDUsage_Csmr_RecallLast = 0x83  # One-Shot Control
kHIDUsage_Csmr_EnterChannel = 0x84  # One-Shot Control
kHIDUsage_Csmr_OrderMovie = 0x85  # One-Shot Control
kHIDUsage_Csmr_Channel = 0x86  # Linear Control
kHIDUsage_Csmr_MediaSelection = 0x87  # Selector
kHIDUsage_Csmr_MediaSelectComputer = 0x88  # Selector
kHIDUsage_Csmr_MediaSelectTV = 0x89  # Selector
kHIDUsage_Csmr_MediaSelectWWW = 0x8A  # Selector
kHIDUsage_Csmr_MediaSelectDVD = 0x8B  # Selector
kHIDUsage_Csmr_MediaSelectTelephone = 0x8C  # Selector
kHIDUsage_Csmr_MediaSelectProgramGuide = 0x8D  # Selector
kHIDUsage_Csmr_MediaSelectVideoPhone = 0x8E  # Selector
kHIDUsage_Csmr_MediaSelectGames = 0x8F  # Selector
kHIDUsage_Csmr_MediaSelectMessages = 0x90  # Selector
kHIDUsage_Csmr_MediaSelectCD = 0x91  # Selector
kHIDUsage_Csmr_MediaSelectVCR = 0x92  # Selector
kHIDUsage_Csmr_MediaSelectTuner = 0x93  # Selector
kHIDUsage_Csmr_Quit = 0x94  # One-Shot Control
kHIDUsage_Csmr_Help = 0x95  # On/Off Control
kHIDUsage_Csmr_MediaSelectTape = 0x96  # Selector
kHIDUsage_Csmr_MediaSelectCable = 0x97  # Selector
kHIDUsage_Csmr_MediaSelectSatellite = 0x98  # Selector
kHIDUsage_Csmr_MediaSelectSecurity = 0x99  # Selector
kHIDUsage_Csmr_MediaSelectHome = 0x9A  # Selector
kHIDUsage_Csmr_MediaSelectCall = 0x9B  # Selector
kHIDUsage_Csmr_ChannelIncrement = 0x9C  # One-Shot Control
kHIDUsage_Csmr_ChannelDecrement = 0x9D  # One-Shot Control
kHIDUsage_Csmr_Media = 0x9E  # Selector
# 0x9F Reserved
kHIDUsage_Csmr_VCRPlus = 0xA0  # One-Shot Control
kHIDUsage_Csmr_Once = 0xA1  # One-Shot Control
kHIDUsage_Csmr_Daily = 0xA2  # One-Shot Control
kHIDUsage_Csmr_Weekly = 0xA3  # One-Shot Control
kHIDUsage_Csmr_Monthly = 0xA4  # One-Shot Control
# 0xA5 - 0xAF Reserved
kHIDUsage_Csmr_Play = 0xB0  # On/Off Control
kHIDUsage_Csmr_Pause = 0xB1  # On/Off Control
kHIDUsage_Csmr_Record = 0xB2  # On/Off Control
kHIDUsage_Csmr_FastForward = 0xB3  # On/Off Control
kHIDUsage_Csmr_Rewind = 0xB4  # On/Off Control
kHIDUsage_Csmr_ScanNextTrack = 0xB5  # One-Shot Control
kHIDUsage_Csmr_ScanPreviousTrack = 0xB6  # One-Shot Control
kHIDUsage_Csmr_Stop = 0xB7  # One-Shot Control
kHIDUsage_Csmr_Eject = 0xB8  # One-Shot Control
kHIDUsage_Csmr_RandomPlay = 0xB9  # On/Off Control
kHIDUsage_Csmr_SelectDisc = 0xBA  # Named Array
kHIDUsage_Csmr_EnterDisc = 0xBB  # Momentary Control
kHIDUsage_Csmr_Repeat = 0xBC  # One-Shot Control
kHIDUsage_Csmr_Tracking = 0xBD  # Linear Control
kHIDUsage_Csmr_TrackNormal = 0xBE  # One-Shot Control
kHIDUsage_Csmr_SlowTracking = 0xBF  # Linear Control
kHIDUsage_Csmr_FrameForward = 0xC0  # Re-Trigger Control
kHIDUsage_Csmr_FrameBack = 0xC1  # Re-Trigger Control
kHIDUsage_Csmr_Mark = 0xC2  # One-Shot Control
kHIDUsage_Csmr_ClearMark = 0xC3  # One-Shot Control
kHIDUsage_Csmr_RepeatFromMark = 0xC4  # On/Off Control
kHIDUsage_Csmr_ReturnToMark = 0xC5  # One-Shot Control
kHIDUsage_Csmr_SearchMarkForward = 0xC6  # One-Shot Control
kHIDUsage_Csmr_SearchMarkBackwards = 0xC7  # One-Shot Control
kHIDUsage_Csmr_CounterReset = 0xC8  # One-Shot Control
kHIDUsage_Csmr_ShowCounter = 0xC9  # One-Shot Control
kHIDUsage_Csmr_TrackingIncrement = 0xCA  # Re-Trigger Control
kHIDUsage_Csmr_TrackingDecrement = 0xCB  # Re-Trigger Control
kHIDUsage_Csmr_StopOrEject = 0xCC  # One-Shot Control
kHIDUsage_Csmr_PlayOrPause = 0xCD  # One-Shot Control
kHIDUsage_Csmr_PlayOrSkip = 0xCE  # One-Shot Control
# 0xCF - 0xDF Reserved
kHIDUsage_Csmr_Volume = 0xE0  # Linear Control
kHIDUsage_Csmr_Balance = 0xE1  # Linear Control
kHIDUsage_Csmr_Mute = 0xE2  # On/Off Control
kHIDUsage_Csmr_Bass = 0xE3  # Linear Control
kHIDUsage_Csmr_Treble = 0xE4  # Linear Control
kHIDUsage_Csmr_BassBoost = 0xE5  # On/Off Control
kHIDUsage_Csmr_SurroundMode = 0xE6  # One-Shot Control
kHIDUsage_Csmr_Loudness = 0xE7  # On/Off Control
kHIDUsage_Csmr_MPX = 0xE8  # On/Off Control
kHIDUsage_Csmr_VolumeIncrement = 0xE9  # Re-Trigger Control
kHIDUsage_Csmr_VolumeDecrement = 0xEA  # Re-Trigger Control
# 0xEB - 0xEF Reserved
kHIDUsage_Csmr_Speed = 0xF0  # Selector
kHIDUsage_Csmr_PlaybackSpeed = 0xF1  # Named Array
kHIDUsage_Csmr_StandardPlay = 0xF2  # Selector
kHIDUsage_Csmr_LongPlay = 0xF3  # Selector
kHIDUsage_Csmr_ExtendedPlay = 0xF4  # Selector
kHIDUsage_Csmr_Slow = 0xF5  # One-Shot Control
# 0xF6 - 0xFF Reserved
kHIDUsage_Csmr_FanEnable = 0x100  # On/Off Control
kHIDUsage_Csmr_FanSpeed = 0x101  # Linear Control
kHIDUsage_Csmr_LightEnable = 0x102  # On/Off Control
kHIDUsage_Csmr_LightIlluminationLevel = 0x103  # Linear Control
kHIDUsage_Csmr_ClimateControlEnable = 0x104  # On/Off Control
kHIDUsage_Csmr_RoomTemperature = 0x105  # Linear Control
kHIDUsage_Csmr_SecurityEnable = 0x106  # On/Off Control
kHIDUsage_Csmr_FireAlarm = 0x107  # One-Shot Control
kHIDUsage_Csmr_PoliceAlarm = 0x108  # One-Shot Control
# 0x109 - 0x14F Reserved
kHIDUsage_Csmr_BalanceRight = 0x150  # Re-Trigger Control
kHIDUsage_Csmr_BalanceLeft = 0x151  # Re-Trigger Control
kHIDUsage_Csmr_BassIncrement = 0x152  # Re-Trigger Control
kHIDUsage_Csmr_BassDecrement = 0x153  # Re-Trigger Control
kHIDUsage_Csmr_TrebleIncrement = 0x154  # Re-Trigger Control
kHIDUsage_Csmr_TrebleDecrement = 0x155  # Re-Trigger Control
# 0x156 - 0x15F Reserved
kHIDUsage_Csmr_SpeakerSystem = 0x160  # Logical Collection
kHIDUsage_Csmr_ChannelLeft = 0x161  # Logical Collection
kHIDUsage_Csmr_ChannelRight = 0x162  # Logical Collection
kHIDUsage_Csmr_ChannelCenter = 0x163  # Logical Collection
kHIDUsage_Csmr_ChannelFront = 0x164  # Logical Collection
kHIDUsage_Csmr_ChannelCenterFront = 0x165  # Logical Collection
kHIDUsage_Csmr_ChannelSide = 0x166  # Logical Collection
kHIDUsage_Csmr_ChannelSurround = 0x167  # Logical Collection
kHIDUsage_Csmr_ChannelLowFrequencyEnhancement = 0x168  # Logical Collection
kHIDUsage_Csmr_ChannelTop = 0x169  # Logical Collection
kHIDUsage_Csmr_ChannelUnknown = 0x16A  # Logical Collection
# 0x16B - 0x16F Reserved
kHIDUsage_Csmr_SubChannel = 0x170  # Linear Control
kHIDUsage_Csmr_SubChannelIncrement = 0x171  # One-Shot Control
kHIDUsage_Csmr_SubChannelDecrement = 0x172  # One-Shot Control
kHIDUsage_Csmr_AlternateAudioIncrement = 0x173  # One-Shot Control
kHIDUsage_Csmr_AlternateAudioDecrement = 0x174  # One-Shot Control
# 0x175 - 0x17F Reserved
kHIDUsage_Csmr_ApplicationLaunchButtons = 0x180  # Named Array
kHIDUsage_Csmr_ALLaunchButtonConfigurationTool = 0x181  # Selector
kHIDUsage_Csmr_ALProgrammableButtonConfiguration = 0x182  # Selector
kHIDUsage_Csmr_ALConsumerControlConfiguration = 0x183  # Selector
kHIDUsage_Csmr_ALWordProcessor = 0x184  # Selector
kHIDUsage_Csmr_ALTextEditor = 0x185  # Selector
kHIDUsage_Csmr_ALSpreadsheet = 0x186  # Selector
kHIDUsage_Csmr_ALGraphicsEditor = 0x187  # Selector
kHIDUsage_Csmr_ALPresentationApp = 0x188  # Selector
kHIDUsage_Csmr_ALDatabaseApp = 0x189  # Selector
kHIDUsage_Csmr_ALEmailReader = 0x18A  # Selector
kHIDUsage_Csmr_ALNewsreader = 0x18B  # Selector
kHIDUsage_Csmr_ALVoicemail = 0x18C  # Selector
kHIDUsage_Csmr_ALContactsOrAddressBook = 0x18D  # Selector
kHIDUsage_Csmr_ALCalendarOrSchedule = 0x18E  # Selector
kHIDUsage_Csmr_ALTaskOrProjectManager = 0x18F  # Selector
kHIDUsage_Csmr_ALLogOrJournalOrTimecard = 0x190  # Selector
kHIDUsage_Csmr_ALCheckbookOrFinance = 0x191  # Selector
kHIDUsage_Csmr_ALCalculator = 0x192  # Selector
kHIDUsage_Csmr_ALAOrVCaptureOrPlayback = 0x193  # Selector
kHIDUsage_Csmr_ALLocalMachineBrowser = 0x194  # Selector
kHIDUsage_Csmr_ALLANOrWANBrowser = 0x195  # Selector
kHIDUsage_Csmr_ALInternetBrowser = 0x196  # Selector
kHIDUsage_Csmr_ALRemoteNetworkingOrISPConnect = 0x197  # Selector
kHIDUsage_Csmr_ALNetworkConference = 0x198  # Selector
kHIDUsage_Csmr_ALNetworkChat = 0x199  # Selector
kHIDUsage_Csmr_ALTelephonyOrDialer = 0x19A  # Selector
kHIDUsage_Csmr_ALLogon = 0x19B  # Selector
kHIDUsage_Csmr_ALLogoff = 0x19C  # Selector
kHIDUsage_Csmr_ALLogonOrLogoff = 0x19D  # Selector
kHIDUsage_Csmr_ALTerminalLockOrScreensaver = 0x19E  # Selector
kHIDUsage_Csmr_ALControlPanel = 0x19F  # Selector
kHIDUsage_Csmr_ALCommandLineProcessorOrRun = 0x1A0  # Selector
kHIDUsage_Csmr_ALProcessOrTaskManager = 0x1A1  # Selector
kHIDUsage_Csmr_AL = 0x1A2  # Selector
kHIDUsage_Csmr_ALNextTaskOrApplication = 0x1A3  # Selector
kHIDUsage_Csmr_ALPreviousTaskOrApplication = 0x1A4  # Selector
kHIDUsage_Csmr_ALPreemptiveHaltTaskOrApplication = 0x1A5  # Selector
kHIDUsage_Csmr_ALIntegratedHelpCenter = 0x1A6  # Selector
kHIDUsage_Csmr_ALDocuments = 0x1A7  # Selector
kHIDUsage_Csmr_ALThesaurus = 0x1A8  # Selector
kHIDUsage_Csmr_ALDictionary = 0x1A9  # Selector
kHIDUsage_Csmr_ALDesktop = 0x1AA  # Selector
kHIDUsage_Csmr_ALSpellCheck = 0x1AB  # Selector
kHIDUsage_Csmr_ALGrammerCheck = 0x1AC  # Selector
kHIDUsage_Csmr_ALWirelessStatus = 0x1AD  # Selector
kHIDUsage_Csmr_ALKeyboardLayout = 0x1AE  # Selector
kHIDUsage_Csmr_ALVirusProtection = 0x1AF  # Selector
kHIDUsage_Csmr_ALEncryption = 0x1B0  # Selector
kHIDUsage_Csmr_ALScreenSaver = 0x1B1  # Selector
kHIDUsage_Csmr_ALAlarms = 0x1B2  # Selector
kHIDUsage_Csmr_ALClock = 0x1B3  # Selector
kHIDUsage_Csmr_ALFileBrowser = 0x1B4  # Selector
kHIDUsage_Csmr_ALPowerStatus = 0x1B5  # Selector
# 0x1A6 - 0x1FF Reserved
kHIDUsage_Csmr_GenericGUIApplicationControls = 0x200  # Named Array
kHIDUsage_Csmr_ACNew = 0x201  # Selector
kHIDUsage_Csmr_ACOpen = 0x202  # Selector
kHIDUsage_Csmr_ACClose = 0x203  # Selector
kHIDUsage_Csmr_ACExit = 0x204  # Selector
kHIDUsage_Csmr_ACMaximize = 0x205  # Selector
kHIDUsage_Csmr_ACMinimize = 0x206  # Selector
kHIDUsage_Csmr_ACSave = 0x207  # Selector
kHIDUsage_Csmr_ACPrint = 0x208  # Selector
kHIDUsage_Csmr_ACProperties = 0x209  # Selector
kHIDUsage_Csmr_ACUndo = 0x21A  # Selector
kHIDUsage_Csmr_ACCopy = 0x21B  # Selector
kHIDUsage_Csmr_ACCut = 0x21C  # Selector
kHIDUsage_Csmr_ACPaste = 0x21D  # Selector
kHIDUsage_Csmr_AC = 0x21E  # Selector
kHIDUsage_Csmr_ACFind = 0x21F  # Selector
kHIDUsage_Csmr_ACFindandReplace = 0x220  # Selector
kHIDUsage_Csmr_ACSearch = 0x221  # Selector
kHIDUsage_Csmr_ACGoTo = 0x222  # Selector
kHIDUsage_Csmr_ACHome = 0x223  # Selector
kHIDUsage_Csmr_ACBack = 0x224  # Selector
kHIDUsage_Csmr_ACForward = 0x225  # Selector
kHIDUsage_Csmr_ACStop = 0x226  # Selector
kHIDUsage_Csmr_ACRefresh = 0x227  # Selector
kHIDUsage_Csmr_ACPreviousLink = 0x228  # Selector
kHIDUsage_Csmr_ACNextLink = 0x229  # Selector
kHIDUsage_Csmr_ACBookmarks = 0x22A  # Selector
kHIDUsage_Csmr_ACHistory = 0x22B  # Selector
kHIDUsage_Csmr_ACSubscriptions = 0x22C  # Selector
kHIDUsage_Csmr_ACZoomIn = 0x22D  # Selector
kHIDUsage_Csmr_ACZoomOut = 0x22E  # Selector
kHIDUsage_Csmr_ACZoom = 0x22F  # Selector
kHIDUsage_Csmr_ACFullScreenView = 0x230  # Selector
kHIDUsage_Csmr_ACNormalView = 0x231  # Selector
kHIDUsage_Csmr_ACViewToggle = 0x232  # Selector
kHIDUsage_Csmr_ACScrollUp = 0x233  # Selector
kHIDUsage_Csmr_ACScrollDown = 0x234  # Selector
kHIDUsage_Csmr_ACScroll = 0x235  # Selector
kHIDUsage_Csmr_ACPanLeft = 0x236  # Selector
kHIDUsage_Csmr_ACPanRight = 0x237  # Selector
kHIDUsage_Csmr_ACPan = 0x238  # Selector
kHIDUsage_Csmr_ACNewWindow = 0x239  # Selector
kHIDUsage_Csmr_ACTileHorizontally = 0x23A  # Selector
kHIDUsage_Csmr_ACTileVertically = 0x23B  # Selector
kHIDUsage_Csmr_ACFormat = 0x23C  # Selector
# 0x23D - 0xFFFF Reserved
kHIDUsage_Csmr_Reserved = 0xFFFF

kSecCodeMagicRequirement = 0xfade0c00  # single requirement
kSecCodeMagicRequirementSet = 0xfade0c01  # requirement set
kSecCodeMagicCodeDirectory = 0xfade0c02  # CodeDirectory
kSecCodeMagicEmbeddedSignature = 0xfade0cc0  # single-architecture embedded signature
kSecCodeMagicDetachedSignature = 0xfade0cc1  # detached multi-architecture signature
kSecCodeMagicEntitlement = 0xfade7171  # entitlement blob


class IOHIDDigitizerTransducerType(Enum):
    kIOHIDDigitizerTransducerTypeStylus = 0
    kIOHIDDigitizerTransducerTypePuck = 1
    kIOHIDDigitizerTransducerTypeFinger = 2
    kIOHIDDigitizerTransducerTypeHand = 3


class IOHIDSwipeMask(Enum):
    kIOHIDSwipeNone = 0x00000000
    kIOHIDSwipeUp = 0x00000001
    kIOHIDSwipeDown = 0x00000002
    kIOHIDSwipeLeft = 0x00000004
    kIOHIDSwipeRight = 0x00000008
    kIOHIDScaleExpand = 0x00000010
    kIOHIDScaleContract = 0x00000020
    kIOHIDRotateCW = 0x00000040
    kIOHIDRotateCCW = 0x00000080


def IOHIDEventTypeMask(type_):
    return 1 << type_


def IOHIDEventFieldBase(type_):
    return type_ << 16


def IOHIDEventFieldOffsetOf(field):
    return field & 0xffff


class IOHIDEventType(Enum):
    kIOHIDEventTypeNULL = 0
    kIOHIDEventTypeVendorDefined = 1
    kIOHIDEventTypeButton = 2
    kIOHIDEventTypeKeyboard = 3
    kIOHIDEventTypeTranslation = 4
    kIOHIDEventTypeRotation = 5
    kIOHIDEventTypeScroll = 6
    kIOHIDEventTypeScale = 7
    kIOHIDEventTypeZoom = 8
    kIOHIDEventTypeVelocity = 9
    kIOHIDEventTypeOrientation = 10
    kIOHIDEventTypeDigitizer = 11
    kIOHIDEventTypeAmbientLightSensor = 12
    kIOHIDEventTypeAccelerometer = 13
    kIOHIDEventTypeProximity = 14
    kIOHIDEventTypeTemperature = 15
    kIOHIDEventTypeNavigationSwipe = 16
    kIOHIDEventTypePointer = 17
    kIOHIDEventTypeProgress = 18
    kIOHIDEventTypeMultiAxisPointer = 19
    kIOHIDEventTypeGyro = 20
    kIOHIDEventTypeCompass = 21
    kIOHIDEventTypeZoomToggle = 22
    kIOHIDEventTypeDockSwipe = 23  # just like kIOHIDEventTypeNavigationSwipe, but intended for consumption by Dock
    kIOHIDEventTypeSymbolicHotKey = 24
    kIOHIDEventTypePower = 25
    kIOHIDEventTypeLED = 26
    kIOHIDEventTypeFluidTouchGesture = 27  # This will eventually superseed Navagation and Dock swipes
    kIOHIDEventTypeBoundaryScroll = 28
    kIOHIDEventTypeBiometric = 29
    kIOHIDEventTypeUnicode = 30
    kIOHIDEventTypeAtmosphericPressure = 31
    kIOHIDEventTypeForce = 32
    kIOHIDEventTypeMotionActivity = 33
    kIOHIDEventTypeMotionGesture = 34
    kIOHIDEventTypeGameController = 35
    kIOHIDEventTypeHumidity = 36
    kIOHIDEventTypeCollection = 37
    kIOHIDEventTypeBrightness = 38
    kIOHIDEventTypeCount = 39  # This should always be last

    # DEPRECATED:
    kIOHIDEventTypeSwipe = 16
    kIOHIDEventTypeMouse = 17


class IOHIDDigitizerEventMask(Enum):
    kIOHIDDigitizerEventRange = 1 << 0
    kIOHIDDigitizerEventTouch = 1 << 1
    kIOHIDDigitizerEventPosition = 1 << 2
    kIOHIDDigitizerEventStop = 1 << 3
    kIOHIDDigitizerEventPeak = 1 << 4
    kIOHIDDigitizerEventIdentity = 1 << 5
    kIOHIDDigitizerEventAttribute = 1 << 6
    kIOHIDDigitizerEventCancel = 1 << 7
    kIOHIDDigitizerEventStart = 1 << 8
    kIOHIDDigitizerEventResting = 1 << 9
    kIOHIDDigitizerEventFromEdgeFlat = 1 << 10
    kIOHIDDigitizerEventFromEdgeTip = 1 << 11
    kIOHIDDigitizerEventFromCorner = 1 << 12
    kIOHIDDigitizerEventSwipePending = 1 << 13
    kIOHIDDigitizerEventFromEdgeForcePending = 1 << 14
    kIOHIDDigitizerEventFromEdgeForceActive = 1 << 15
    kIOHIDDigitizerEventForcePopped = 1 << 16
    kIOHIDDigitizerEventSwipeUp = 1 << 24
    kIOHIDDigitizerEventSwipeDown = 1 << 25
    kIOHIDDigitizerEventSwipeLeft = 1 << 26
    kIOHIDDigitizerEventSwipeRight = 1 << 27
    kIOHIDDigitizerEventEstimatedAltitude = 1 << 28
    kIOHIDDigitizerEventEstimatedAzimuth = 1 << 29
    kIOHIDDigitizerEventEstimatedPressure = 1 << 30
    kIOHIDDigitizerEventSwipeMask = 0xF << 24


class IOHIDEventField(Enum):
    kIOHIDEventFieldIsRelative = IOHIDEventFieldBase(IOHIDEventType.kIOHIDEventTypeNULL.value)
    kIOHIDEventFieldIsCollection = auto()
    kIOHIDEventFieldIsPixelUnits = auto()
    kIOHIDEventFieldIsCenterOrigin = auto()
    kIOHIDEventFieldIsBuiltIn = auto()


class IOHIDEventOptionBits(Enum):
    kIOHIDEventOptionNone = 0
    kIOHIDEventOptionIsAbsolute = 1 << 0
    kIOHIDEventOptionIsCollection = 1 << 1
    kIOHIDEventOptionIsPixelUnits = 1 << 2
    kIOHIDEventOptionIsCenterOrigin = 1 << 3
    kIOHIDEventOptionIsBuiltIn = 1 << 4

    # misspellings
    kIOHIDEventOptionPixelUnits = kIOHIDEventOptionIsPixelUnits


class IOHIDEventFieldDigitizer(Enum):
    kIOHIDEventFieldDigitizerX = IOHIDEventFieldBase(IOHIDEventType.kIOHIDEventTypeDigitizer.value)
    kIOHIDEventFieldDigitizerY = auto()
    kIOHIDEventFieldDigitizerZ = auto()
    kIOHIDEventFieldDigitizerButtonMask = auto()
    kIOHIDEventFieldDigitizerType = auto()
    kIOHIDEventFieldDigitizerIndex = auto()
    kIOHIDEventFieldDigitizerIdentity = auto()
    kIOHIDEventFieldDigitizerEventMask = auto()
    kIOHIDEventFieldDigitizerRange = auto()
    kIOHIDEventFieldDigitizerTouch = auto()
    kIOHIDEventFieldDigitizerPressure = auto()
    kIOHIDEventFieldDigitizerAuxiliaryPressure = auto()  # BarrelPressure
    kIOHIDEventFieldDigitizerTwist = auto()
    kIOHIDEventFieldDigitizerTiltX = auto()
    kIOHIDEventFieldDigitizerTiltY = auto()
    kIOHIDEventFieldDigitizerAltitude = auto()
    kIOHIDEventFieldDigitizerAzimuth = auto()
    kIOHIDEventFieldDigitizerQuality = auto()
    kIOHIDEventFieldDigitizerDensity = auto()
    kIOHIDEventFieldDigitizerIrregularity = auto()
    kIOHIDEventFieldDigitizerMajorRadius = auto()
    kIOHIDEventFieldDigitizerMinorRadius = auto()
    kIOHIDEventFieldDigitizerCollection = auto()
    kIOHIDEventFieldDigitizerCollectionChord = auto()
    kIOHIDEventFieldDigitizerChildEventMask = auto()
    kIOHIDEventFieldDigitizerIsDisplayIntegrated = auto()
    kIOHIDEventFieldDigitizerQualityRadiiAccuracy = auto()
    kIOHIDEventFieldDigitizerGenerationCount = auto()
    kIOHIDEventFieldDigitizerWillUpdateMask = auto()
    kIOHIDEventFieldDigitizerDidUpdateMask = auto()
    kIOHIDEventFieldDigitizerEstimatedMask = auto()


kCGHIDEventTap = 0
kCGWindowListOptionAll = 0
kCGNullWindowID = 0

CG_KEY_A = 0
CG_KEY_S = 1
CG_KEY_D = 2
CG_KEY_F = 3
CG_KEY_H = 4
CG_KEY_G = 5
CG_KEY_Z = 6
CG_KEY_X = 7
CG_KEY_C = 8
CG_KEY_V = 9
CG_KEY_B = 11
CG_KEY_Q = 12
CG_KEY_W = 13
CG_KEY_E = 14
CG_KEY_R = 15
CG_KEY_Y = 16
CG_KEY_T = 17
CG_KEY_1 = 18
CG_KEY_2 = 19
CG_KEY_3 = 20
CG_KEY_4 = 21
CG_KEY_6 = 22
CG_KEY_5 = 23
CG_KEY_EQUAL = 24
CG_KEY_9 = 25
CG_KEY_7 = 26
CG_KEY_DASH = 27
CG_KEY_8 = 28
CG_KEY_0 = 29
CG_KEY_CLOSE_SQUARE_BRACKETS = 30
CG_KEY_O = 31
CG_KEY_U = 32
CG_KEY_OPEN_SQUARE_BRACKETS = 33
CG_KEY_I = 34
CG_KEY_P = 35
CG_KEY_RETURN = 36
CG_KEY_L = 37
CG_KEY_J = 38
CG_KEY_COLON = 39
CG_KEY_K = 40
CG_KEY_SEMICOLON = 41
CG_KEY_BACKSLASH = 42
CG_KEY_COMMA = 43
CG_KEY_SLASH = 44
CG_KEY_N = 45
CG_KEY_M = 46
CG_KEY_DOT = 47
CG_KEY_TAB = 48
CG_KEY_SPACE = 49
CG_KEY_TILDE = 50
CG_KEY_DELETE = 51
CG_KEY_ENTER = 52
CG_KEY_ESCAPE = 53
CG_KEY_ASTERISK = 67
CG_KEY_PLUS = 69
CG_KEY_CLEAR = 71
CG_KEY_F5 = 96
CG_KEY_F6 = 97
CG_KEY_F7 = 98
CG_KEY_F3 = 99
CG_KEY_F8 = 100
CG_KEY_F9 = 101
CG_KEY_F11 = 103
CG_KEY_F13 = 105
CG_KEY_F14 = 107
CG_KEY_F10 = 109
CG_KEY_F12 = 111
CG_KEY_F15 = 113
CG_KEY_HELP = 114
CG_KEY_HOME = 115
CG_KEY_PGUP = 116
CG_KEY_F4 = 118
CG_KEY_END = 119
CG_KEY_F2 = 120
CG_KEY_PGDN = 121
CG_KEY_F1 = 122
CG_KEY_LEFT = 123
CG_KEY_RIGHT = 124
CG_KEY_DOWN = 125
CG_KEY_UP = 126


class OsLogLevel(IntEnum):
    """ LogLevel. Extracted by reversing LevelForKey(id prefs, NSString *key) """

    OFF = 0
    NONE = 0
    UNDEFINED = 1  # no such plist key
    DEFAULT = 2
    INFO = 3
    DEBUG = 4


# Definitions of flags stored in file flags word.
# Super-user and owner changeable flags.

UF_SETTABLE = 0x0000ffff  # mask of owner changeable flags
UF_NODUMP = 0x00000001  # do not dump file
UF_IMMUTABLE = 0x00000002  # file may not be changed
UF_APPEND = 0x00000004  # writes to file may only append
UF_OPAQUE = 0x00000008  # directory is opaque wrt. union

# The following bit is reserved for FreeBSD.  It is not implemented
# in Mac OS X.

# UF_NOUNLINK =  0x00000010  # file may not be removed or renamed
UF_COMPRESSED = 0x00000020  # file is compressed (some file-systems)

# UF_TRACKED is used for dealing with document IDs.  We no longer issue
#  notifications for deletes or renames for files which have UF_TRACKED set.
UF_TRACKED = 0x00000040

UF_DATAVAULT = 0x00000080  # entitlement required for reading
# and writing

# Bits 0x0100 through 0x4000 are currently undefined.
UF_HIDDEN = 0x00008000  # hint that this item should not be
# displayed in a GUI
#
# Super-user changeable flags.

SF_SUPPORTED = 0x009f0000  # mask of superuser supported flags
SF_SETTABLE = 0x3fff0000  # mask of superuser changeable flags
SF_SYNTHETIC = 0xc0000000  # mask of system read-only synthetic flags
SF_ARCHIVED = 0x00010000  # file is archived
SF_IMMUTABLE = 0x00020000  # file may not be changed
SF_APPEND = 0x00040000  # writes to file may only append
SF_RESTRICTED = 0x00080000  # entitlement required for writing
SF_NOUNLINK = 0x00100000  # Item may not be removed, renamed or mounted on

# The following two bits are reserved for FreeBSD.  They are not
# implemented in Mac OS X.

# SF_SNAPSHOT =  0x00200000  # snapshot inode
# NOTE: There is no SF_HIDDEN bit.

SF_FIRMLINK = 0x00800000  # file is a firmlink

# Synthetic flags.
#
# These are read-only.  We keep them out of SF_SUPPORTED so that
# attempts to set them will fail.

SF_DATALESS = 0x40000000  # file is dataless object
