from typing import TYPE_CHECKING, Generic

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.clients.darwin.common import CfSerializable, CfSerializableAny, CfSerializableT
from rpcclient.core._types import ClientBound


if TYPE_CHECKING:
    from rpcclient.clients.ios.client import IosClient


class MobileGestalt(ClientBound["IosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """Thin wrapper around MobileGestalt MGCopyAnswer/MGSetAnswer keys."""

    def __init__(self, client: "IosClient[DarwinSymbolT_co]") -> None:
        self._client = client

    # Identifying Information

    async def DiskUsage(self) -> CfSerializable:
        return await self.get_answer("DiskUsage")

    async def ModelNumber(self) -> CfSerializable:
        return await self.get_answer("ModelNumber")

    async def SIMTrayStatus(self) -> CfSerializable:
        return await self.get_answer("SIMTrayStatus")

    async def SerialNumber(self) -> CfSerializable:
        return await self.get_answer("SerialNumber")

    async def MLBSerialNumber(self) -> CfSerializable:
        return await self.get_answer("MLBSerialNumber")

    async def UniqueDeviceID(self) -> CfSerializable:
        return await self.get_answer("UniqueDeviceID")

    async def UniqueDeviceIDData(self) -> CfSerializable:
        return await self.get_answer("UniqueDeviceIDData")

    async def UniqueChipID(self) -> CfSerializable:
        return await self.get_answer("UniqueChipID")

    async def InverseDeviceID(self) -> CfSerializable:
        return await self.get_answer("InverseDeviceID")

    async def DiagData(self) -> CfSerializable:
        return await self.get_answer("DiagData")

    async def DieId(self) -> CfSerializable:
        return await self.get_answer("DieId")

    async def CPUArchitecture(self) -> CfSerializable:
        return await self.get_answer("CPUArchitecture")

    async def PartitionType(self) -> CfSerializable:
        return await self.get_answer("PartitionType")

    async def UserAssignedDeviceName(self) -> CfSerializable:
        return await self.get_answer("UserAssignedDeviceName")

    # Bluetooth Information

    async def BluetoothAddress(self) -> CfSerializable:
        return await self.get_answer("BluetoothAddress")

    # Battery Information

    async def RequiredBatteryLevelForSoftwareUpdate(self) -> CfSerializable:
        return await self.get_answer("RequiredBatteryLevelForSoftwareUpdate")

    async def BatteryIsFullyCharged(self) -> CfSerializable:
        return await self.get_answer("BatteryIsFullyCharged")

    async def BatteryIsCharging(self) -> CfSerializable:
        return await self.get_answer("BatteryIsCharging")

    async def BatteryCurrentCapacity(self) -> CfSerializable:
        return await self.get_answer("BatteryCurrentCapacity")

    async def ExternalPowerSourceConnected(self) -> CfSerializable:
        return await self.get_answer("ExternalPowerSourceConnected")

    # Baseband Information

    async def BasebandSerialNumber(self) -> CfSerializable:
        return await self.get_answer("BasebandSerialNumber")

    async def BasebandCertId(self) -> CfSerializable:
        return await self.get_answer("BasebandCertId")

    async def BasebandChipId(self) -> CfSerializable:
        return await self.get_answer("BasebandChipId")

    async def BasebandFirmwareManifestData(self) -> CfSerializable:
        return await self.get_answer("BasebandFirmwareManifestData")

    async def BasebandFirmwareVersion(self) -> CfSerializable:
        return await self.get_answer("BasebandFirmwareVersion")

    async def BasebandKeyHashInformation(self) -> CfSerializable:
        return await self.get_answer("BasebandKeyHashInformation")

    # Telephony Information

    async def CarrierBundleInfoArray(self) -> CfSerializable:
        return await self.get_answer("CarrierBundleInfoArray")

    async def CarrierInstallCapability(self) -> CfSerializable:
        return await self.get_answer("CarrierInstallCapability")

    async def InternationalMobileEquipmentIdentity(self) -> CfSerializable:
        return await self.get_answer("InternationalMobileEquipmentIdentity")

    async def MobileSubscriberCountryCode(self) -> CfSerializable:
        return await self.get_answer("MobileSubscriberCountryCode")

    async def MobileSubscriberNetworkCode(self) -> CfSerializable:
        return await self.get_answer("MobileSubscriberNetworkCode")

    # Device Information

    async def ChipID(self) -> CfSerializable:
        return await self.get_answer("ChipID")

    async def ComputerName(self) -> CfSerializable:
        return await self.get_answer("ComputerName")

    async def DeviceVariant(self) -> CfSerializable:
        return await self.get_answer("DeviceVariant")

    async def HWModelStr(self) -> CfSerializable:
        return await self.get_answer("HWModelStr")

    async def BoardId(self) -> CfSerializable:
        return await self.get_answer("BoardId")

    async def HardwarePlatform(self) -> CfSerializable:
        return await self.get_answer("HardwarePlatform")

    async def DeviceName(self) -> CfSerializable:
        return await self.get_answer("DeviceName")

    async def DeviceColor(self) -> CfSerializable:
        return await self.get_answer("DeviceColor")

    async def DeviceClassNumber(self) -> CfSerializable:
        return await self.get_answer("DeviceClassNumber")

    async def DeviceClass(self) -> CfSerializable:
        return await self.get_answer("DeviceClass")

    async def BuildVersion(self) -> CfSerializable:
        return await self.get_answer("BuildVersion")

    async def ProductName(self) -> CfSerializable:
        return await self.get_answer("ProductName")

    async def ProductType(self) -> CfSerializable:
        return await self.get_answer("ProductType")

    async def ProductVersion(self) -> CfSerializable:
        return await self.get_answer("ProductVersion")

    async def FirmwareNonce(self) -> CfSerializable:
        return await self.get_answer("FirmwareNonce")

    async def FirmwareVersion(self) -> CfSerializable:
        return await self.get_answer("FirmwareVersion")

    async def FirmwarePreflightInfo(self) -> CfSerializable:
        return await self.get_answer("FirmwarePreflightInfo")

    async def IntegratedCircuitCardIdentifier(self) -> CfSerializable:
        return await self.get_answer("IntegratedCircuitCardIdentifier")

    async def AirplaneMode(self) -> bool:
        return await self.get_answer("AirplaneMode", bool)

    async def AllowYouTube(self) -> CfSerializable:
        return await self.get_answer("AllowYouTube")

    async def AllowYouTubePlugin(self) -> CfSerializable:
        return await self.get_answer("AllowYouTubePlugin")

    async def MinimumSupportediTunesVersion(self) -> CfSerializable:
        return await self.get_answer("MinimumSupportediTunesVersion")

    async def ProximitySensorCalibration(self) -> CfSerializable:
        return await self.get_answer("ProximitySensorCalibration")

    async def RegionCode(self) -> CfSerializable:
        return await self.get_answer("RegionCode")

    async def RegionInfo(self) -> CfSerializable:
        return await self.get_answer("RegionInfo")

    async def RegulatoryIdentifiers(self) -> CfSerializable:
        return await self.get_answer("RegulatoryIdentifiers")

    async def SBAllowSensitiveUI(self) -> CfSerializable:
        return await self.get_answer("SBAllowSensitiveUI")

    async def SBCanForceDebuggingInfo(self) -> CfSerializable:
        return await self.get_answer("SBCanForceDebuggingInfo")

    async def SDIOManufacturerTuple(self) -> CfSerializable:
        return await self.get_answer("SDIOManufacturerTuple")

    async def SDIOProductInfo(self) -> CfSerializable:
        return await self.get_answer("SDIOProductInfo")

    async def ShouldHactivate(self) -> CfSerializable:
        return await self.get_answer("ShouldHactivate")

    async def SigningFuse(self) -> CfSerializable:
        return await self.get_answer("SigningFuse")

    async def SoftwareBehavior(self) -> CfSerializable:
        return await self.get_answer("SoftwareBehavior")

    async def SoftwareBundleVersion(self) -> CfSerializable:
        return await self.get_answer("SoftwareBundleVersion")

    async def SupportedDeviceFamilies(self) -> CfSerializable:
        return await self.get_answer("SupportedDeviceFamilies")

    async def SupportedKeyboards(self) -> CfSerializable:
        return await self.get_answer("SupportedKeyboards")

    async def TotalSystemAvailable(self) -> CfSerializable:
        return await self.get_answer("TotalSystemAvailable")

    # Capability Information

    async def AllDeviceCapabilities(self) -> CfSerializable:
        return await self.get_answer("AllDeviceCapabilities")

    async def AppleInternalInstallCapability(self) -> CfSerializable:
        return await self.get_answer("AppleInternalInstallCapability")

    async def ExternalChargeCapability(self) -> CfSerializable:
        return await self.get_answer("ExternalChargeCapability")

    async def ForwardCameraCapability(self) -> CfSerializable:
        return await self.get_answer("ForwardCameraCapability")

    async def PanoramaCameraCapability(self) -> CfSerializable:
        return await self.get_answer("PanoramaCameraCapability")

    async def RearCameraCapability(self) -> CfSerializable:
        return await self.get_answer("RearCameraCapability")

    async def HasAllFeaturesCapability(self) -> CfSerializable:
        return await self.get_answer("HasAllFeaturesCapability")

    async def HasBaseband(self) -> CfSerializable:
        return await self.get_answer("HasBaseband")

    async def HasInternalSettingsBundle(self) -> CfSerializable:
        return await self.get_answer("HasInternalSettingsBundle")

    async def HasSpringBoard(self) -> CfSerializable:
        return await self.get_answer("HasSpringBoard")

    async def InternalBuild(self) -> CfSerializable:
        return await self.get_answer("InternalBuild")

    async def IsSimulator(self) -> CfSerializable:
        return await self.get_answer("IsSimulator")

    async def IsThereEnoughBatteryLevelForSoftwareUpdate(self) -> CfSerializable:
        return await self.get_answer("IsThereEnoughBatteryLevelForSoftwareUpdate")

    async def IsUIBuild(self) -> CfSerializable:
        return await self.get_answer("IsUIBuild")

    async def PasswordConfigured(self) -> CfSerializable:
        return await self.get_answer("PasswordConfigured")

    async def PasswordProtected(self) -> CfSerializable:
        return await self.get_answer("PasswordProtected")

    # Regional Behaviour

    async def RegionalBehaviorAll(self) -> CfSerializable:
        return await self.get_answer("RegionalBehaviorAll")

    async def RegionalBehaviorChinaBrick(self) -> CfSerializable:
        return await self.get_answer("RegionalBehaviorChinaBrick")

    async def RegionalBehaviorEUVolumeLimit(self) -> CfSerializable:
        return await self.get_answer("RegionalBehaviorEUVolumeLimit")

    async def RegionalBehaviorGB18030(self) -> CfSerializable:
        return await self.get_answer("RegionalBehaviorGB18030")

    async def RegionalBehaviorGoogleMail(self) -> CfSerializable:
        return await self.get_answer("RegionalBehaviorGoogleMail")

    async def RegionalBehaviorNTSC(self) -> CfSerializable:
        return await self.get_answer("RegionalBehaviorNTSC")

    async def RegionalBehaviorNoPasscodeLocationTiles(self) -> CfSerializable:
        return await self.get_answer("RegionalBehaviorNoPasscodeLocationTiles")

    async def RegionalBehaviorNoVOIP(self) -> CfSerializable:
        return await self.get_answer("RegionalBehaviorNoVOIP")

    async def RegionalBehaviorNoWiFi(self) -> CfSerializable:
        return await self.get_answer("RegionalBehaviorNoWiFi")

    async def RegionalBehaviorShutterClick(self) -> CfSerializable:
        return await self.get_answer("RegionalBehaviorShutterClick")

    async def RegionalBehaviorVolumeLimit(self) -> CfSerializable:
        return await self.get_answer("RegionalBehaviorVolumeLimit")

    # Wireless Information

    async def ActiveWirelessTechnology(self) -> CfSerializable:
        return await self.get_answer("ActiveWirelessTechnology")

    async def WifiAddress(self) -> CfSerializable:
        return await self.get_answer("WifiAddress")

    async def WifiAddressData(self) -> CfSerializable:
        return await self.get_answer("WifiAddressData")

    async def WifiVendor(self) -> CfSerializable:
        return await self.get_answer("WifiVendor")

    # FaceTime Information

    async def FaceTimeBitRate2G(self) -> CfSerializable:
        return await self.get_answer("FaceTimeBitRate2G")

    async def FaceTimeBitRate3G(self) -> CfSerializable:
        return await self.get_answer("FaceTimeBitRate3G")

    async def FaceTimeBitRateLTE(self) -> CfSerializable:
        return await self.get_answer("FaceTimeBitRateLTE")

    async def FaceTimeBitRateWiFi(self) -> CfSerializable:
        return await self.get_answer("FaceTimeBitRateWiFi")

    async def FaceTimeDecodings(self) -> CfSerializable:
        return await self.get_answer("FaceTimeDecodings")

    async def FaceTimeEncodings(self) -> CfSerializable:
        return await self.get_answer("FaceTimeEncodings")

    async def FaceTimePreferredDecoding(self) -> CfSerializable:
        return await self.get_answer("FaceTimePreferredDecoding")

    async def FaceTimePreferredEncoding(self) -> CfSerializable:
        return await self.get_answer("FaceTimePreferredEncoding")

    # More Device Capabilities

    async def DeviceSupportsFaceTime(self) -> CfSerializable:
        return await self.get_answer("DeviceSupportsFaceTime")

    async def DeviceSupportsTethering(self) -> CfSerializable:
        return await self.get_answer("DeviceSupportsTethering")

    async def DeviceSupportsSimplisticRoadMesh(self) -> CfSerializable:
        return await self.get_answer("DeviceSupportsSimplisticRoadMesh")

    async def DeviceSupportsNavigation(self) -> CfSerializable:
        return await self.get_answer("DeviceSupportsNavigation")

    async def DeviceSupportsLineIn(self) -> CfSerializable:
        return await self.get_answer("DeviceSupportsLineIn")

    async def DeviceSupports9Pin(self) -> CfSerializable:
        return await self.get_answer("DeviceSupports9Pin")

    async def DeviceSupports720p(self) -> CfSerializable:
        return await self.get_answer("DeviceSupports720p")

    async def DeviceSupports4G(self) -> CfSerializable:
        return await self.get_answer("DeviceSupports4G")

    async def DeviceSupports3DMaps(self) -> CfSerializable:
        return await self.get_answer("DeviceSupports3DMaps")

    async def DeviceSupports3DImagery(self) -> CfSerializable:
        return await self.get_answer("DeviceSupports3DImagery")

    async def DeviceSupports1080p(self) -> CfSerializable:
        return await self.get_answer("DeviceSupports1080p")

    async def get_answer(
        self, key: str, typ: type[CfSerializableT] | tuple[type[CfSerializableT], ...] = CfSerializableAny
    ) -> CfSerializableT:
        """Return the MGCopyAnswer value for a given key."""
        return await (await self._client.symbols.MGCopyAnswer(await self._client.cf(key))).py(typ)

    async def set_answer(self, key: str, value: CfSerializable) -> CfSerializable:
        """Set the MGSetAnswer value for a given key."""
        return await self._client.symbols.MGSetAnswer(await self._client.cf(key), await self._client.cf(value))
