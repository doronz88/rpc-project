class MobileGestalt:
    def __init__(self, client):
        self._client = client

    # Identifying Information

    @property
    def DiskUsage(self):
        return self.get_answer('DiskUsage')

    @property
    def ModelNumber(self):
        return self.get_answer('ModelNumber')

    @property
    def SIMTrayStatus(self):
        return self.get_answer('SIMTrayStatus')

    @property
    def SerialNumber(self):
        return self.get_answer('SerialNumber')

    @property
    def MLBSerialNumber(self):
        return self.get_answer('MLBSerialNumber')

    @property
    def UniqueDeviceID(self):
        return self.get_answer('UniqueDeviceID')

    @property
    def UniqueDeviceIDData(self):
        return self.get_answer('UniqueDeviceIDData')

    @property
    def UniqueChipID(self):
        return self.get_answer('UniqueChipID')

    @property
    def InverseDeviceID(self):
        return self.get_answer('InverseDeviceID')

    @property
    def DiagData(self):
        return self.get_answer('DiagData')

    @property
    def DieId(self):
        return self.get_answer('DieId')

    @property
    def CPUArchitecture(self):
        return self.get_answer('CPUArchitecture')

    @property
    def PartitionType(self):
        return self.get_answer('PartitionType')

    @property
    def UserAssignedDeviceName(self):
        return self.get_answer('UserAssignedDeviceName')

    # Bluetooth Information

    @property
    def BluetoothAddress(self):
        return self.get_answer('BluetoothAddress')

    # Battery Information

    @property
    def RequiredBatteryLevelForSoftwareUpdate(self):
        return self.get_answer('RequiredBatteryLevelForSoftwareUpdate')

    @property
    def BatteryIsFullyCharged(self):
        return self.get_answer('BatteryIsFullyCharged')

    @property
    def BatteryIsCharging(self):
        return self.get_answer('BatteryIsCharging')

    @property
    def BatteryCurrentCapacity(self):
        return self.get_answer('BatteryCurrentCapacity')

    @property
    def ExternalPowerSourceConnected(self):
        return self.get_answer('ExternalPowerSourceConnected')

    # Baseband Information

    @property
    def BasebandSerialNumber(self):
        return self.get_answer('BasebandSerialNumber')

    @property
    def BasebandCertId(self):
        return self.get_answer('BasebandCertId')

    @property
    def BasebandChipId(self):
        return self.get_answer('BasebandChipId')

    @property
    def BasebandFirmwareManifestData(self):
        return self.get_answer('BasebandFirmwareManifestData')

    @property
    def BasebandFirmwareVersion(self):
        return self.get_answer('BasebandFirmwareVersion')

    @property
    def BasebandKeyHashInformation(self):
        return self.get_answer('BasebandKeyHashInformation')

    # Telephony Information

    @property
    def CarrierBundleInfoArray(self):
        return self.get_answer('CarrierBundleInfoArray')

    @property
    def CarrierInstallCapability(self):
        return self.get_answer('CarrierInstallCapability')

    @property
    def InternationalMobileEquipmentIdentity(self):
        return self.get_answer('InternationalMobileEquipmentIdentity')

    @property
    def MobileSubscriberCountryCode(self):
        return self.get_answer('MobileSubscriberCountryCode')

    @property
    def MobileSubscriberNetworkCode(self):
        return self.get_answer('MobileSubscriberNetworkCode')

    # Device Information

    @property
    def ChipID(self):
        return self.get_answer('ChipID')

    @property
    def ComputerName(self):
        return self.get_answer('ComputerName')

    @property
    def DeviceVariant(self):
        return self.get_answer('DeviceVariant')

    @property
    def HWModelStr(self):
        return self.get_answer('HWModelStr')

    @property
    def BoardId(self):
        return self.get_answer('BoardId')

    @property
    def HardwarePlatform(self):
        return self.get_answer('HardwarePlatform')

    @property
    def DeviceName(self):
        return self.get_answer('DeviceName')

    @property
    def DeviceColor(self):
        return self.get_answer('DeviceColor')

    @property
    def DeviceClassNumber(self):
        return self.get_answer('DeviceClassNumber')

    @property
    def DeviceClass(self):
        return self.get_answer('DeviceClass')

    @property
    def BuildVersion(self):
        return self.get_answer('BuildVersion')

    @property
    def ProductName(self):
        return self.get_answer('ProductName')

    @property
    def ProductType(self):
        return self.get_answer('ProductType')

    @property
    def ProductVersion(self):
        return self.get_answer('ProductVersion')

    @property
    def FirmwareNonce(self):
        return self.get_answer('FirmwareNonce')

    @property
    def FirmwareVersion(self):
        return self.get_answer('FirmwareVersion')

    @property
    def FirmwarePreflightInfo(self):
        return self.get_answer('FirmwarePreflightInfo')

    @property
    def IntegratedCircuitCardIdentifier(self):
        return self.get_answer('IntegratedCircuitCardIdentifier')

    @property
    def AirplaneMode(self) -> bool:
        return self.get_answer('AirplaneMode')

    @property
    def AllowYouTube(self):
        return self.get_answer('AllowYouTube')

    @property
    def AllowYouTubePlugin(self):
        return self.get_answer('AllowYouTubePlugin')

    @property
    def MinimumSupportediTunesVersion(self):
        return self.get_answer('MinimumSupportediTunesVersion')

    @property
    def ProximitySensorCalibration(self):
        return self.get_answer('ProximitySensorCalibration')

    @property
    def RegionCode(self):
        return self.get_answer('RegionCode')

    @property
    def RegionInfo(self):
        return self.get_answer('RegionInfo')

    @property
    def RegulatoryIdentifiers(self):
        return self.get_answer('RegulatoryIdentifiers')

    @property
    def SBAllowSensitiveUI(self):
        return self.get_answer('SBAllowSensitiveUI')

    @property
    def SBCanForceDebuggingInfo(self):
        return self.get_answer('SBCanForceDebuggingInfo')

    @property
    def SDIOManufacturerTuple(self):
        return self.get_answer('SDIOManufacturerTuple')

    @property
    def SDIOProductInfo(self):
        return self.get_answer('SDIOProductInfo')

    @property
    def ShouldHactivate(self):
        return self.get_answer('ShouldHactivate')

    @property
    def SigningFuse(self):
        return self.get_answer('SigningFuse')

    @property
    def SoftwareBehavior(self):
        return self.get_answer('SoftwareBehavior')

    @property
    def SoftwareBundleVersion(self):
        return self.get_answer('SoftwareBundleVersion')

    @property
    def SupportedDeviceFamilies(self):
        return self.get_answer('SupportedDeviceFamilies')

    @property
    def SupportedKeyboards(self):
        return self.get_answer('SupportedKeyboards')

    @property
    def TotalSystemAvailable(self):
        return self.get_answer('TotalSystemAvailable')

    # Capability Information

    @property
    def AllDeviceCapabilities(self):
        return self.get_answer('AllDeviceCapabilities')

    @property
    def AppleInternalInstallCapability(self):
        return self.get_answer('AppleInternalInstallCapability')

    @property
    def ExternalChargeCapability(self):
        return self.get_answer('ExternalChargeCapability')

    @property
    def ForwardCameraCapability(self):
        return self.get_answer('ForwardCameraCapability')

    @property
    def PanoramaCameraCapability(self):
        return self.get_answer('PanoramaCameraCapability')

    @property
    def RearCameraCapability(self):
        return self.get_answer('RearCameraCapability')

    @property
    def HasAllFeaturesCapability(self):
        return self.get_answer('HasAllFeaturesCapability')

    @property
    def HasBaseband(self):
        return self.get_answer('HasBaseband')

    @property
    def HasInternalSettingsBundle(self):
        return self.get_answer('HasInternalSettingsBundle')

    @property
    def HasSpringBoard(self):
        return self.get_answer('HasSpringBoard')

    @property
    def InternalBuild(self):
        return self.get_answer('InternalBuild')

    @property
    def IsSimulator(self):
        return self.get_answer('IsSimulator')

    @property
    def IsThereEnoughBatteryLevelForSoftwareUpdate(self):
        return self.get_answer('IsThereEnoughBatteryLevelForSoftwareUpdate')

    @property
    def IsUIBuild(self):
        return self.get_answer('IsUIBuild')

    @property
    def PasswordConfigured(self):
        return self.get_answer('PasswordConfigured')

    # Regional Behaviour

    @property
    def RegionalBehaviorAll(self):
        return self.get_answer('RegionalBehaviorAll')

    @property
    def RegionalBehaviorChinaBrick(self):
        return self.get_answer('RegionalBehaviorChinaBrick')

    @property
    def RegionalBehaviorEUVolumeLimit(self):
        return self.get_answer('RegionalBehaviorEUVolumeLimit')

    @property
    def RegionalBehaviorGB18030(self):
        return self.get_answer('RegionalBehaviorGB18030')

    @property
    def RegionalBehaviorGoogleMail(self):
        return self.get_answer('RegionalBehaviorGoogleMail')

    @property
    def RegionalBehaviorNTSC(self):
        return self.get_answer('RegionalBehaviorNTSC')

    @property
    def RegionalBehaviorNoPasscodeLocationTiles(self):
        return self.get_answer('RegionalBehaviorNoPasscodeLocationTiles')

    @property
    def RegionalBehaviorNoVOIP(self):
        return self.get_answer('RegionalBehaviorNoVOIP')

    @property
    def RegionalBehaviorNoWiFi(self):
        return self.get_answer('RegionalBehaviorNoWiFi')

    @property
    def RegionalBehaviorShutterClick(self):
        return self.get_answer('RegionalBehaviorShutterClick')

    @property
    def RegionalBehaviorVolumeLimit(self):
        return self.get_answer('RegionalBehaviorVolumeLimit')

    # Wireless Information

    @property
    def ActiveWirelessTechnology(self):
        return self.get_answer('ActiveWirelessTechnology')

    @property
    def WifiAddress(self):
        return self.get_answer('WifiAddress')

    @property
    def WifiAddressData(self):
        return self.get_answer('WifiAddressData')

    @property
    def WifiVendor(self):
        return self.get_answer('WifiVendor')

    # FaceTime Information

    @property
    def FaceTimeBitRate2G(self):
        return self.get_answer('FaceTimeBitRate2G')

    @property
    def FaceTimeBitRate3G(self):
        return self.get_answer('FaceTimeBitRate3G')

    @property
    def FaceTimeBitRateLTE(self):
        return self.get_answer('FaceTimeBitRateLTE')

    @property
    def FaceTimeBitRateWiFi(self):
        return self.get_answer('FaceTimeBitRateWiFi')

    @property
    def FaceTimeDecodings(self):
        return self.get_answer('FaceTimeDecodings')

    @property
    def FaceTimeEncodings(self):
        return self.get_answer('FaceTimeEncodings')

    @property
    def FaceTimePreferredDecoding(self):
        return self.get_answer('FaceTimePreferredDecoding')

    @property
    def FaceTimePreferredEncoding(self):
        return self.get_answer('FaceTimePreferredEncoding')

    # More Device Capabilities

    @property
    def DeviceSupportsFaceTime(self):
        return self.get_answer('DeviceSupportsFaceTime')

    @property
    def DeviceSupportsTethering(self):
        return self.get_answer('DeviceSupportsTethering')

    @property
    def DeviceSupportsSimplisticRoadMesh(self):
        return self.get_answer('DeviceSupportsSimplisticRoadMesh')

    @property
    def DeviceSupportsNavigation(self):
        return self.get_answer('DeviceSupportsNavigation')

    @property
    def DeviceSupportsLineIn(self):
        return self.get_answer('DeviceSupportsLineIn')

    @property
    def DeviceSupports9Pin(self):
        return self.get_answer('DeviceSupports9Pin')

    @property
    def DeviceSupports720p(self):
        return self.get_answer('DeviceSupports720p')

    @property
    def DeviceSupports4G(self):
        return self.get_answer('DeviceSupports4G')

    @property
    def DeviceSupports3DMaps(self):
        return self.get_answer('DeviceSupports3DMaps')

    @property
    def DeviceSupports3DImagery(self):
        return self.get_answer('DeviceSupports3DImagery')

    @property
    def DeviceSupports1080p(self):
        return self.get_answer('DeviceSupports1080p')

    def get_answer(self, key: str):
        """ get a string answer from MobileGestalt """
        return self._client.symbols.MGCopyAnswer(self._client.cf(key)).py()

    def set_answer(self, key: str, value):
        """ set an answer into MobileGestalt """
        return self._client.symbols.MGSetAnswer(self._client.cf(key), self._client.cf(value))
