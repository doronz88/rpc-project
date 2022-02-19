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
