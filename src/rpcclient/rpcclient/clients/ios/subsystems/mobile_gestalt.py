from typing import TYPE_CHECKING, Generic

import zyncio

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.clients.darwin.common import CfSerializable, CfSerializableAny, CfSerializableT
from rpcclient.core._types import ClientBound


if TYPE_CHECKING:
    from rpcclient.clients.ios.client import BaseIosClient


class MobileGestalt(ClientBound["BaseIosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """Thin wrapper around MobileGestalt MGCopyAnswer/MGSetAnswer keys."""

    def __init__(self, client: "BaseIosClient[DarwinSymbolT_co]") -> None:
        self._client = client

    # Identifying Information

    @zyncio.zproperty
    async def DiskUsage(self) -> CfSerializable:
        return await self.get_answer.z("DiskUsage")

    @zyncio.zproperty
    async def ModelNumber(self) -> CfSerializable:
        return await self.get_answer.z("ModelNumber")

    @zyncio.zproperty
    async def SIMTrayStatus(self) -> CfSerializable:
        return await self.get_answer.z("SIMTrayStatus")

    @zyncio.zproperty
    async def SerialNumber(self) -> CfSerializable:
        return await self.get_answer.z("SerialNumber")

    @zyncio.zproperty
    async def MLBSerialNumber(self) -> CfSerializable:
        return await self.get_answer.z("MLBSerialNumber")

    @zyncio.zproperty
    async def UniqueDeviceID(self) -> CfSerializable:
        return await self.get_answer.z("UniqueDeviceID")

    @zyncio.zproperty
    async def UniqueDeviceIDData(self) -> CfSerializable:
        return await self.get_answer.z("UniqueDeviceIDData")

    @zyncio.zproperty
    async def UniqueChipID(self) -> CfSerializable:
        return await self.get_answer.z("UniqueChipID")

    @zyncio.zproperty
    async def InverseDeviceID(self) -> CfSerializable:
        return await self.get_answer.z("InverseDeviceID")

    @zyncio.zproperty
    async def DiagData(self) -> CfSerializable:
        return await self.get_answer.z("DiagData")

    @zyncio.zproperty
    async def DieId(self) -> CfSerializable:
        return await self.get_answer.z("DieId")

    @zyncio.zproperty
    async def CPUArchitecture(self) -> CfSerializable:
        return await self.get_answer.z("CPUArchitecture")

    @zyncio.zproperty
    async def PartitionType(self) -> CfSerializable:
        return await self.get_answer.z("PartitionType")

    @zyncio.zproperty
    async def UserAssignedDeviceName(self) -> CfSerializable:
        return await self.get_answer.z("UserAssignedDeviceName")

    # Bluetooth Information

    @zyncio.zproperty
    async def BluetoothAddress(self) -> CfSerializable:
        return await self.get_answer.z("BluetoothAddress")

    # Battery Information

    @zyncio.zproperty
    async def RequiredBatteryLevelForSoftwareUpdate(self) -> CfSerializable:
        return await self.get_answer.z("RequiredBatteryLevelForSoftwareUpdate")

    @zyncio.zproperty
    async def BatteryIsFullyCharged(self) -> CfSerializable:
        return await self.get_answer.z("BatteryIsFullyCharged")

    @zyncio.zproperty
    async def BatteryIsCharging(self) -> CfSerializable:
        return await self.get_answer.z("BatteryIsCharging")

    @zyncio.zproperty
    async def BatteryCurrentCapacity(self) -> CfSerializable:
        return await self.get_answer.z("BatteryCurrentCapacity")

    @zyncio.zproperty
    async def ExternalPowerSourceConnected(self) -> CfSerializable:
        return await self.get_answer.z("ExternalPowerSourceConnected")

    # Baseband Information

    @zyncio.zproperty
    async def BasebandSerialNumber(self) -> CfSerializable:
        return await self.get_answer.z("BasebandSerialNumber")

    @zyncio.zproperty
    async def BasebandCertId(self) -> CfSerializable:
        return await self.get_answer.z("BasebandCertId")

    @zyncio.zproperty
    async def BasebandChipId(self) -> CfSerializable:
        return await self.get_answer.z("BasebandChipId")

    @zyncio.zproperty
    async def BasebandFirmwareManifestData(self) -> CfSerializable:
        return await self.get_answer.z("BasebandFirmwareManifestData")

    @zyncio.zproperty
    async def BasebandFirmwareVersion(self) -> CfSerializable:
        return await self.get_answer.z("BasebandFirmwareVersion")

    @zyncio.zproperty
    async def BasebandKeyHashInformation(self) -> CfSerializable:
        return await self.get_answer.z("BasebandKeyHashInformation")

    # Telephony Information

    @zyncio.zproperty
    async def CarrierBundleInfoArray(self) -> CfSerializable:
        return await self.get_answer.z("CarrierBundleInfoArray")

    @zyncio.zproperty
    async def CarrierInstallCapability(self) -> CfSerializable:
        return await self.get_answer.z("CarrierInstallCapability")

    @zyncio.zproperty
    async def InternationalMobileEquipmentIdentity(self) -> CfSerializable:
        return await self.get_answer.z("InternationalMobileEquipmentIdentity")

    @zyncio.zproperty
    async def MobileSubscriberCountryCode(self) -> CfSerializable:
        return await self.get_answer.z("MobileSubscriberCountryCode")

    @zyncio.zproperty
    async def MobileSubscriberNetworkCode(self) -> CfSerializable:
        return await self.get_answer.z("MobileSubscriberNetworkCode")

    # Device Information

    @zyncio.zproperty
    async def ChipID(self) -> CfSerializable:
        return await self.get_answer.z("ChipID")

    @zyncio.zproperty
    async def ComputerName(self) -> CfSerializable:
        return await self.get_answer.z("ComputerName")

    @zyncio.zproperty
    async def DeviceVariant(self) -> CfSerializable:
        return await self.get_answer.z("DeviceVariant")

    @zyncio.zproperty
    async def HWModelStr(self) -> CfSerializable:
        return await self.get_answer.z("HWModelStr")

    @zyncio.zproperty
    async def BoardId(self) -> CfSerializable:
        return await self.get_answer.z("BoardId")

    @zyncio.zproperty
    async def HardwarePlatform(self) -> CfSerializable:
        return await self.get_answer.z("HardwarePlatform")

    @zyncio.zproperty
    async def DeviceName(self) -> CfSerializable:
        return await self.get_answer.z("DeviceName")

    @zyncio.zproperty
    async def DeviceColor(self) -> CfSerializable:
        return await self.get_answer.z("DeviceColor")

    @zyncio.zproperty
    async def DeviceClassNumber(self) -> CfSerializable:
        return await self.get_answer.z("DeviceClassNumber")

    @zyncio.zproperty
    async def DeviceClass(self) -> CfSerializable:
        return await self.get_answer.z("DeviceClass")

    @zyncio.zproperty
    async def BuildVersion(self) -> CfSerializable:
        return await self.get_answer.z("BuildVersion")

    @zyncio.zproperty
    async def ProductName(self) -> CfSerializable:
        return await self.get_answer.z("ProductName")

    @zyncio.zproperty
    async def ProductType(self) -> CfSerializable:
        return await self.get_answer.z("ProductType")

    @zyncio.zproperty
    async def ProductVersion(self) -> CfSerializable:
        return await self.get_answer.z("ProductVersion")

    @zyncio.zproperty
    async def FirmwareNonce(self) -> CfSerializable:
        return await self.get_answer.z("FirmwareNonce")

    @zyncio.zproperty
    async def FirmwareVersion(self) -> CfSerializable:
        return await self.get_answer.z("FirmwareVersion")

    @zyncio.zproperty
    async def FirmwarePreflightInfo(self) -> CfSerializable:
        return await self.get_answer.z("FirmwarePreflightInfo")

    @zyncio.zproperty
    async def IntegratedCircuitCardIdentifier(self) -> CfSerializable:
        return await self.get_answer.z("IntegratedCircuitCardIdentifier")

    @zyncio.zproperty
    async def AirplaneMode(self) -> bool:
        return await self.get_answer.z("AirplaneMode", bool)

    @zyncio.zproperty
    async def AllowYouTube(self) -> CfSerializable:
        return await self.get_answer.z("AllowYouTube")

    @zyncio.zproperty
    async def AllowYouTubePlugin(self) -> CfSerializable:
        return await self.get_answer.z("AllowYouTubePlugin")

    @zyncio.zproperty
    async def MinimumSupportediTunesVersion(self) -> CfSerializable:
        return await self.get_answer.z("MinimumSupportediTunesVersion")

    @zyncio.zproperty
    async def ProximitySensorCalibration(self) -> CfSerializable:
        return await self.get_answer.z("ProximitySensorCalibration")

    @zyncio.zproperty
    async def RegionCode(self) -> CfSerializable:
        return await self.get_answer.z("RegionCode")

    @zyncio.zproperty
    async def RegionInfo(self) -> CfSerializable:
        return await self.get_answer.z("RegionInfo")

    @zyncio.zproperty
    async def RegulatoryIdentifiers(self) -> CfSerializable:
        return await self.get_answer.z("RegulatoryIdentifiers")

    @zyncio.zproperty
    async def SBAllowSensitiveUI(self) -> CfSerializable:
        return await self.get_answer.z("SBAllowSensitiveUI")

    @zyncio.zproperty
    async def SBCanForceDebuggingInfo(self) -> CfSerializable:
        return await self.get_answer.z("SBCanForceDebuggingInfo")

    @zyncio.zproperty
    async def SDIOManufacturerTuple(self) -> CfSerializable:
        return await self.get_answer.z("SDIOManufacturerTuple")

    @zyncio.zproperty
    async def SDIOProductInfo(self) -> CfSerializable:
        return await self.get_answer.z("SDIOProductInfo")

    @zyncio.zproperty
    async def ShouldHactivate(self) -> CfSerializable:
        return await self.get_answer.z("ShouldHactivate")

    @zyncio.zproperty
    async def SigningFuse(self) -> CfSerializable:
        return await self.get_answer.z("SigningFuse")

    @zyncio.zproperty
    async def SoftwareBehavior(self) -> CfSerializable:
        return await self.get_answer.z("SoftwareBehavior")

    @zyncio.zproperty
    async def SoftwareBundleVersion(self) -> CfSerializable:
        return await self.get_answer.z("SoftwareBundleVersion")

    @zyncio.zproperty
    async def SupportedDeviceFamilies(self) -> CfSerializable:
        return await self.get_answer.z("SupportedDeviceFamilies")

    @zyncio.zproperty
    async def SupportedKeyboards(self) -> CfSerializable:
        return await self.get_answer.z("SupportedKeyboards")

    @zyncio.zproperty
    async def TotalSystemAvailable(self) -> CfSerializable:
        return await self.get_answer.z("TotalSystemAvailable")

    # Capability Information

    @zyncio.zproperty
    async def AllDeviceCapabilities(self) -> CfSerializable:
        return await self.get_answer.z("AllDeviceCapabilities")

    @zyncio.zproperty
    async def AppleInternalInstallCapability(self) -> CfSerializable:
        return await self.get_answer.z("AppleInternalInstallCapability")

    @zyncio.zproperty
    async def ExternalChargeCapability(self) -> CfSerializable:
        return await self.get_answer.z("ExternalChargeCapability")

    @zyncio.zproperty
    async def ForwardCameraCapability(self) -> CfSerializable:
        return await self.get_answer.z("ForwardCameraCapability")

    @zyncio.zproperty
    async def PanoramaCameraCapability(self) -> CfSerializable:
        return await self.get_answer.z("PanoramaCameraCapability")

    @zyncio.zproperty
    async def RearCameraCapability(self) -> CfSerializable:
        return await self.get_answer.z("RearCameraCapability")

    @zyncio.zproperty
    async def HasAllFeaturesCapability(self) -> CfSerializable:
        return await self.get_answer.z("HasAllFeaturesCapability")

    @zyncio.zproperty
    async def HasBaseband(self) -> CfSerializable:
        return await self.get_answer.z("HasBaseband")

    @zyncio.zproperty
    async def HasInternalSettingsBundle(self) -> CfSerializable:
        return await self.get_answer.z("HasInternalSettingsBundle")

    @zyncio.zproperty
    async def HasSpringBoard(self) -> CfSerializable:
        return await self.get_answer.z("HasSpringBoard")

    @zyncio.zproperty
    async def InternalBuild(self) -> CfSerializable:
        return await self.get_answer.z("InternalBuild")

    @zyncio.zproperty
    async def IsSimulator(self) -> CfSerializable:
        return await self.get_answer.z("IsSimulator")

    @zyncio.zproperty
    async def IsThereEnoughBatteryLevelForSoftwareUpdate(self) -> CfSerializable:
        return await self.get_answer.z("IsThereEnoughBatteryLevelForSoftwareUpdate")

    @zyncio.zproperty
    async def IsUIBuild(self) -> CfSerializable:
        return await self.get_answer.z("IsUIBuild")

    @zyncio.zproperty
    async def PasswordConfigured(self) -> CfSerializable:
        return await self.get_answer.z("PasswordConfigured")

    @zyncio.zproperty
    async def PasswordProtected(self) -> CfSerializable:
        return await self.get_answer.z("PasswordProtected")

    # Regional Behaviour

    @zyncio.zproperty
    async def RegionalBehaviorAll(self) -> CfSerializable:
        return await self.get_answer.z("RegionalBehaviorAll")

    @zyncio.zproperty
    async def RegionalBehaviorChinaBrick(self) -> CfSerializable:
        return await self.get_answer.z("RegionalBehaviorChinaBrick")

    @zyncio.zproperty
    async def RegionalBehaviorEUVolumeLimit(self) -> CfSerializable:
        return await self.get_answer.z("RegionalBehaviorEUVolumeLimit")

    @zyncio.zproperty
    async def RegionalBehaviorGB18030(self) -> CfSerializable:
        return await self.get_answer.z("RegionalBehaviorGB18030")

    @zyncio.zproperty
    async def RegionalBehaviorGoogleMail(self) -> CfSerializable:
        return await self.get_answer.z("RegionalBehaviorGoogleMail")

    @zyncio.zproperty
    async def RegionalBehaviorNTSC(self) -> CfSerializable:
        return await self.get_answer.z("RegionalBehaviorNTSC")

    @zyncio.zproperty
    async def RegionalBehaviorNoPasscodeLocationTiles(self) -> CfSerializable:
        return await self.get_answer.z("RegionalBehaviorNoPasscodeLocationTiles")

    @zyncio.zproperty
    async def RegionalBehaviorNoVOIP(self) -> CfSerializable:
        return await self.get_answer.z("RegionalBehaviorNoVOIP")

    @zyncio.zproperty
    async def RegionalBehaviorNoWiFi(self) -> CfSerializable:
        return await self.get_answer.z("RegionalBehaviorNoWiFi")

    @zyncio.zproperty
    async def RegionalBehaviorShutterClick(self) -> CfSerializable:
        return await self.get_answer.z("RegionalBehaviorShutterClick")

    @zyncio.zproperty
    async def RegionalBehaviorVolumeLimit(self) -> CfSerializable:
        return await self.get_answer.z("RegionalBehaviorVolumeLimit")

    # Wireless Information

    @zyncio.zproperty
    async def ActiveWirelessTechnology(self) -> CfSerializable:
        return await self.get_answer.z("ActiveWirelessTechnology")

    @zyncio.zproperty
    async def WifiAddress(self) -> CfSerializable:
        return await self.get_answer.z("WifiAddress")

    @zyncio.zproperty
    async def WifiAddressData(self) -> CfSerializable:
        return await self.get_answer.z("WifiAddressData")

    @zyncio.zproperty
    async def WifiVendor(self) -> CfSerializable:
        return await self.get_answer.z("WifiVendor")

    # FaceTime Information

    @zyncio.zproperty
    async def FaceTimeBitRate2G(self) -> CfSerializable:
        return await self.get_answer.z("FaceTimeBitRate2G")

    @zyncio.zproperty
    async def FaceTimeBitRate3G(self) -> CfSerializable:
        return await self.get_answer.z("FaceTimeBitRate3G")

    @zyncio.zproperty
    async def FaceTimeBitRateLTE(self) -> CfSerializable:
        return await self.get_answer.z("FaceTimeBitRateLTE")

    @zyncio.zproperty
    async def FaceTimeBitRateWiFi(self) -> CfSerializable:
        return await self.get_answer.z("FaceTimeBitRateWiFi")

    @zyncio.zproperty
    async def FaceTimeDecodings(self) -> CfSerializable:
        return await self.get_answer.z("FaceTimeDecodings")

    @zyncio.zproperty
    async def FaceTimeEncodings(self) -> CfSerializable:
        return await self.get_answer.z("FaceTimeEncodings")

    @zyncio.zproperty
    async def FaceTimePreferredDecoding(self) -> CfSerializable:
        return await self.get_answer.z("FaceTimePreferredDecoding")

    @zyncio.zproperty
    async def FaceTimePreferredEncoding(self) -> CfSerializable:
        return await self.get_answer.z("FaceTimePreferredEncoding")

    # More Device Capabilities

    @zyncio.zproperty
    async def DeviceSupportsFaceTime(self) -> CfSerializable:
        return await self.get_answer.z("DeviceSupportsFaceTime")

    @zyncio.zproperty
    async def DeviceSupportsTethering(self) -> CfSerializable:
        return await self.get_answer.z("DeviceSupportsTethering")

    @zyncio.zproperty
    async def DeviceSupportsSimplisticRoadMesh(self) -> CfSerializable:
        return await self.get_answer.z("DeviceSupportsSimplisticRoadMesh")

    @zyncio.zproperty
    async def DeviceSupportsNavigation(self) -> CfSerializable:
        return await self.get_answer.z("DeviceSupportsNavigation")

    @zyncio.zproperty
    async def DeviceSupportsLineIn(self) -> CfSerializable:
        return await self.get_answer.z("DeviceSupportsLineIn")

    @zyncio.zproperty
    async def DeviceSupports9Pin(self) -> CfSerializable:
        return await self.get_answer.z("DeviceSupports9Pin")

    @zyncio.zproperty
    async def DeviceSupports720p(self) -> CfSerializable:
        return await self.get_answer.z("DeviceSupports720p")

    @zyncio.zproperty
    async def DeviceSupports4G(self) -> CfSerializable:
        return await self.get_answer.z("DeviceSupports4G")

    @zyncio.zproperty
    async def DeviceSupports3DMaps(self) -> CfSerializable:
        return await self.get_answer.z("DeviceSupports3DMaps")

    @zyncio.zproperty
    async def DeviceSupports3DImagery(self) -> CfSerializable:
        return await self.get_answer.z("DeviceSupports3DImagery")

    @zyncio.zproperty
    async def DeviceSupports1080p(self) -> CfSerializable:
        return await self.get_answer.z("DeviceSupports1080p")

    @zyncio.zmethod
    async def get_answer(
        self, key: str, typ: type[CfSerializableT] | tuple[type[CfSerializableT], ...] = CfSerializableAny
    ) -> CfSerializableT:
        """Return the MGCopyAnswer value for a given key."""
        return await (await self._client.symbols.MGCopyAnswer.z(await self._client.cf.z(key))).py.z(typ)

    @zyncio.zmethod
    async def set_answer(self, key: str, value: CfSerializable) -> CfSerializable:
        """Set the MGSetAnswer value for a given key."""
        return await self._client.symbols.MGSetAnswer.z(await self._client.cf.z(key), await self._client.cf.z(value))
