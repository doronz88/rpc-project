from enum import Enum

kCFAllocatorDefault = 0
MACH_PORT_NULL = 0
AVAudioSessionCategoryOptionDefaultToSpeaker = 0x8

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
