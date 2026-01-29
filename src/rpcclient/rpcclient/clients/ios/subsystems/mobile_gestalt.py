from typing import TYPE_CHECKING

from rpcclient.clients.darwin.common import CfSerializable

if TYPE_CHECKING:
    from rpcclient.clients.ios.client import IosClient


class MobileGestalt:
    """Thin wrapper around MobileGestalt MGCopyAnswer/MGSetAnswer keys."""

    def __init__(self, client: "IosClient") -> None:
        self._client = client

    # Identifying Information

    @property
    def DiskUsage(self) -> CfSerializable:
        return self.get_answer("DiskUsage")

    @property
    def ModelNumber(self) -> CfSerializable:
        return self.get_answer("ModelNumber")

    @property
    def SIMTrayStatus(self) -> CfSerializable:
        return self.get_answer("SIMTrayStatus")

    @property
    def SerialNumber(self) -> CfSerializable:
        return self.get_answer("SerialNumber")

    @property
    def MLBSerialNumber(self) -> CfSerializable:
        return self.get_answer("MLBSerialNumber")

    @property
    def UniqueDeviceID(self) -> CfSerializable:
        return self.get_answer("UniqueDeviceID")

    @property
    def UniqueDeviceIDData(self) -> CfSerializable:
        return self.get_answer("UniqueDeviceIDData")

    @property
    def UniqueChipID(self) -> CfSerializable:
        return self.get_answer("UniqueChipID")

    @property
    def InverseDeviceID(self) -> CfSerializable:
        return self.get_answer("InverseDeviceID")

    @property
    def DiagData(self) -> CfSerializable:
        return self.get_answer("DiagData")

    @property
    def DieId(self) -> CfSerializable:
        return self.get_answer("DieId")

    @property
    def CPUArchitecture(self) -> CfSerializable:
        return self.get_answer("CPUArchitecture")

    @property
    def PartitionType(self) -> CfSerializable:
        return self.get_answer("PartitionType")

    @property
    def UserAssignedDeviceName(self) -> CfSerializable:
        return self.get_answer("UserAssignedDeviceName")

    # Bluetooth Information

    @property
    def BluetoothAddress(self) -> CfSerializable:
        return self.get_answer("BluetoothAddress")

    # Battery Information

    @property
    def RequiredBatteryLevelForSoftwareUpdate(self) -> CfSerializable:
        return self.get_answer("RequiredBatteryLevelForSoftwareUpdate")

    @property
    def BatteryIsFullyCharged(self) -> CfSerializable:
        return self.get_answer("BatteryIsFullyCharged")

    @property
    def BatteryIsCharging(self) -> CfSerializable:
        return self.get_answer("BatteryIsCharging")

    @property
    def BatteryCurrentCapacity(self) -> CfSerializable:
        return self.get_answer("BatteryCurrentCapacity")

    @property
    def ExternalPowerSourceConnected(self) -> CfSerializable:
        return self.get_answer("ExternalPowerSourceConnected")

    # Baseband Information

    @property
    def BasebandSerialNumber(self) -> CfSerializable:
        return self.get_answer("BasebandSerialNumber")

    @property
    def BasebandCertId(self) -> CfSerializable:
        return self.get_answer("BasebandCertId")

    @property
    def BasebandChipId(self) -> CfSerializable:
        return self.get_answer("BasebandChipId")

    @property
    def BasebandFirmwareManifestData(self) -> CfSerializable:
        return self.get_answer("BasebandFirmwareManifestData")

    @property
    def BasebandFirmwareVersion(self) -> CfSerializable:
        return self.get_answer("BasebandFirmwareVersion")

    @property
    def BasebandKeyHashInformation(self) -> CfSerializable:
        return self.get_answer("BasebandKeyHashInformation")

    # Telephony Information

    @property
    def CarrierBundleInfoArray(self) -> CfSerializable:
        return self.get_answer("CarrierBundleInfoArray")

    @property
    def CarrierInstallCapability(self) -> CfSerializable:
        return self.get_answer("CarrierInstallCapability")

    @property
    def InternationalMobileEquipmentIdentity(self) -> CfSerializable:
        return self.get_answer("InternationalMobileEquipmentIdentity")

    @property
    def MobileSubscriberCountryCode(self) -> CfSerializable:
        return self.get_answer("MobileSubscriberCountryCode")

    @property
    def MobileSubscriberNetworkCode(self) -> CfSerializable:
        return self.get_answer("MobileSubscriberNetworkCode")

    # Device Information

    @property
    def ChipID(self) -> CfSerializable:
        return self.get_answer("ChipID")

    @property
    def ComputerName(self) -> CfSerializable:
        return self.get_answer("ComputerName")

    @property
    def DeviceVariant(self) -> CfSerializable:
        return self.get_answer("DeviceVariant")

    @property
    def HWModelStr(self) -> CfSerializable:
        return self.get_answer("HWModelStr")

    @property
    def BoardId(self) -> CfSerializable:
        return self.get_answer("BoardId")

    @property
    def HardwarePlatform(self) -> CfSerializable:
        return self.get_answer("HardwarePlatform")

    @property
    def DeviceName(self) -> CfSerializable:
        return self.get_answer("DeviceName")

    @property
    def DeviceColor(self) -> CfSerializable:
        return self.get_answer("DeviceColor")

    @property
    def DeviceClassNumber(self) -> CfSerializable:
        return self.get_answer("DeviceClassNumber")

    @property
    def DeviceClass(self) -> CfSerializable:
        return self.get_answer("DeviceClass")

    @property
    def BuildVersion(self) -> CfSerializable:
        return self.get_answer("BuildVersion")

    @property
    def ProductName(self) -> CfSerializable:
        return self.get_answer("ProductName")

    @property
    def ProductType(self) -> CfSerializable:
        return self.get_answer("ProductType")

    @property
    def ProductVersion(self) -> CfSerializable:
        return self.get_answer("ProductVersion")

    @property
    def FirmwareNonce(self) -> CfSerializable:
        return self.get_answer("FirmwareNonce")

    @property
    def FirmwareVersion(self) -> CfSerializable:
        return self.get_answer("FirmwareVersion")

    @property
    def FirmwarePreflightInfo(self) -> CfSerializable:
        return self.get_answer("FirmwarePreflightInfo")

    @property
    def IntegratedCircuitCardIdentifier(self) -> CfSerializable:
        return self.get_answer("IntegratedCircuitCardIdentifier")

    @property
    def AirplaneMode(self) -> bool:
        return self.get_answer("AirplaneMode")

    @property
    def AllowYouTube(self) -> CfSerializable:
        return self.get_answer("AllowYouTube")

    @property
    def AllowYouTubePlugin(self) -> CfSerializable:
        return self.get_answer("AllowYouTubePlugin")

    @property
    def MinimumSupportediTunesVersion(self) -> CfSerializable:
        return self.get_answer("MinimumSupportediTunesVersion")

    @property
    def ProximitySensorCalibration(self) -> CfSerializable:
        return self.get_answer("ProximitySensorCalibration")

    @property
    def RegionCode(self) -> CfSerializable:
        return self.get_answer("RegionCode")

    @property
    def RegionInfo(self) -> CfSerializable:
        return self.get_answer("RegionInfo")

    @property
    def RegulatoryIdentifiers(self) -> CfSerializable:
        return self.get_answer("RegulatoryIdentifiers")

    @property
    def SBAllowSensitiveUI(self) -> CfSerializable:
        return self.get_answer("SBAllowSensitiveUI")

    @property
    def SBCanForceDebuggingInfo(self) -> CfSerializable:
        return self.get_answer("SBCanForceDebuggingInfo")

    @property
    def SDIOManufacturerTuple(self) -> CfSerializable:
        return self.get_answer("SDIOManufacturerTuple")

    @property
    def SDIOProductInfo(self) -> CfSerializable:
        return self.get_answer("SDIOProductInfo")

    @property
    def ShouldHactivate(self) -> CfSerializable:
        return self.get_answer("ShouldHactivate")

    @property
    def SigningFuse(self) -> CfSerializable:
        return self.get_answer("SigningFuse")

    @property
    def SoftwareBehavior(self) -> CfSerializable:
        return self.get_answer("SoftwareBehavior")

    @property
    def SoftwareBundleVersion(self) -> CfSerializable:
        return self.get_answer("SoftwareBundleVersion")

    @property
    def SupportedDeviceFamilies(self) -> CfSerializable:
        return self.get_answer("SupportedDeviceFamilies")

    @property
    def SupportedKeyboards(self) -> CfSerializable:
        return self.get_answer("SupportedKeyboards")

    @property
    def TotalSystemAvailable(self) -> CfSerializable:
        return self.get_answer("TotalSystemAvailable")

    # Capability Information

    @property
    def AllDeviceCapabilities(self) -> CfSerializable:
        return self.get_answer("AllDeviceCapabilities")

    @property
    def AppleInternalInstallCapability(self) -> CfSerializable:
        return self.get_answer("AppleInternalInstallCapability")

    @property
    def ExternalChargeCapability(self) -> CfSerializable:
        return self.get_answer("ExternalChargeCapability")

    @property
    def ForwardCameraCapability(self) -> CfSerializable:
        return self.get_answer("ForwardCameraCapability")

    @property
    def PanoramaCameraCapability(self) -> CfSerializable:
        return self.get_answer("PanoramaCameraCapability")

    @property
    def RearCameraCapability(self) -> CfSerializable:
        return self.get_answer("RearCameraCapability")

    @property
    def HasAllFeaturesCapability(self) -> CfSerializable:
        return self.get_answer("HasAllFeaturesCapability")

    @property
    def HasBaseband(self) -> CfSerializable:
        return self.get_answer("HasBaseband")

    @property
    def HasInternalSettingsBundle(self) -> CfSerializable:
        return self.get_answer("HasInternalSettingsBundle")

    @property
    def HasSpringBoard(self) -> CfSerializable:
        return self.get_answer("HasSpringBoard")

    @property
    def InternalBuild(self) -> CfSerializable:
        return self.get_answer("InternalBuild")

    @property
    def IsSimulator(self) -> CfSerializable:
        return self.get_answer("IsSimulator")

    @property
    def IsThereEnoughBatteryLevelForSoftwareUpdate(self) -> CfSerializable:
        return self.get_answer("IsThereEnoughBatteryLevelForSoftwareUpdate")

    @property
    def IsUIBuild(self) -> CfSerializable:
        return self.get_answer("IsUIBuild")

    @property
    def PasswordConfigured(self) -> CfSerializable:
        return self.get_answer("PasswordConfigured")

    @property
    def PasswordProtected(self) -> CfSerializable:
        return self.get_answer("PasswordProtected")

    # Regional Behaviour

    @property
    def RegionalBehaviorAll(self) -> CfSerializable:
        return self.get_answer("RegionalBehaviorAll")

    @property
    def RegionalBehaviorChinaBrick(self) -> CfSerializable:
        return self.get_answer("RegionalBehaviorChinaBrick")

    @property
    def RegionalBehaviorEUVolumeLimit(self) -> CfSerializable:
        return self.get_answer("RegionalBehaviorEUVolumeLimit")

    @property
    def RegionalBehaviorGB18030(self) -> CfSerializable:
        return self.get_answer("RegionalBehaviorGB18030")

    @property
    def RegionalBehaviorGoogleMail(self) -> CfSerializable:
        return self.get_answer("RegionalBehaviorGoogleMail")

    @property
    def RegionalBehaviorNTSC(self) -> CfSerializable:
        return self.get_answer("RegionalBehaviorNTSC")

    @property
    def RegionalBehaviorNoPasscodeLocationTiles(self) -> CfSerializable:
        return self.get_answer("RegionalBehaviorNoPasscodeLocationTiles")

    @property
    def RegionalBehaviorNoVOIP(self) -> CfSerializable:
        return self.get_answer("RegionalBehaviorNoVOIP")

    @property
    def RegionalBehaviorNoWiFi(self) -> CfSerializable:
        return self.get_answer("RegionalBehaviorNoWiFi")

    @property
    def RegionalBehaviorShutterClick(self) -> CfSerializable:
        return self.get_answer("RegionalBehaviorShutterClick")

    @property
    def RegionalBehaviorVolumeLimit(self) -> CfSerializable:
        return self.get_answer("RegionalBehaviorVolumeLimit")

    # Wireless Information

    @property
    def ActiveWirelessTechnology(self) -> CfSerializable:
        return self.get_answer("ActiveWirelessTechnology")

    @property
    def WifiAddress(self) -> CfSerializable:
        return self.get_answer("WifiAddress")

    @property
    def WifiAddressData(self) -> CfSerializable:
        return self.get_answer("WifiAddressData")

    @property
    def WifiVendor(self) -> CfSerializable:
        return self.get_answer("WifiVendor")

    # FaceTime Information

    @property
    def FaceTimeBitRate2G(self) -> CfSerializable:
        return self.get_answer("FaceTimeBitRate2G")

    @property
    def FaceTimeBitRate3G(self) -> CfSerializable:
        return self.get_answer("FaceTimeBitRate3G")

    @property
    def FaceTimeBitRateLTE(self) -> CfSerializable:
        return self.get_answer("FaceTimeBitRateLTE")

    @property
    def FaceTimeBitRateWiFi(self) -> CfSerializable:
        return self.get_answer("FaceTimeBitRateWiFi")

    @property
    def FaceTimeDecodings(self) -> CfSerializable:
        return self.get_answer("FaceTimeDecodings")

    @property
    def FaceTimeEncodings(self) -> CfSerializable:
        return self.get_answer("FaceTimeEncodings")

    @property
    def FaceTimePreferredDecoding(self) -> CfSerializable:
        return self.get_answer("FaceTimePreferredDecoding")

    @property
    def FaceTimePreferredEncoding(self) -> CfSerializable:
        return self.get_answer("FaceTimePreferredEncoding")

    # More Device Capabilities

    @property
    def DeviceSupportsFaceTime(self) -> CfSerializable:
        return self.get_answer("DeviceSupportsFaceTime")

    @property
    def DeviceSupportsTethering(self) -> CfSerializable:
        return self.get_answer("DeviceSupportsTethering")

    @property
    def DeviceSupportsSimplisticRoadMesh(self) -> CfSerializable:
        return self.get_answer("DeviceSupportsSimplisticRoadMesh")

    @property
    def DeviceSupportsNavigation(self) -> CfSerializable:
        return self.get_answer("DeviceSupportsNavigation")

    @property
    def DeviceSupportsLineIn(self) -> CfSerializable:
        return self.get_answer("DeviceSupportsLineIn")

    @property
    def DeviceSupports9Pin(self) -> CfSerializable:
        return self.get_answer("DeviceSupports9Pin")

    @property
    def DeviceSupports720p(self) -> CfSerializable:
        return self.get_answer("DeviceSupports720p")

    @property
    def DeviceSupports4G(self) -> CfSerializable:
        return self.get_answer("DeviceSupports4G")

    @property
    def DeviceSupports3DMaps(self) -> CfSerializable:
        return self.get_answer("DeviceSupports3DMaps")

    @property
    def DeviceSupports3DImagery(self) -> CfSerializable:
        return self.get_answer("DeviceSupports3DImagery")

    @property
    def DeviceSupports1080p(self) -> CfSerializable:
        return self.get_answer("DeviceSupports1080p")

    def get_answer(self, key: str) -> CfSerializable:
        """Return the MGCopyAnswer value for a given key."""
        return self._client.symbols.MGCopyAnswer(self._client.cf(key)).py()

    def set_answer(self, key: str, value: CfSerializable) -> CfSerializable:
        """Set the MGSetAnswer value for a given key."""
        return self._client.symbols.MGSetAnswer(self._client.cf(key), self._client.cf(value))
