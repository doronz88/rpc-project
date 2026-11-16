# iOS subsystems

Subsystems available only on iOS clients.

## MobileGestalt

## rpcclient.clients.ios.subsystems.mobile_gestalt

### MobileGestalt

Bases: `ClientBound['IosClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

Thin wrapper around MobileGestalt MGCopyAnswer/MGSetAnswer keys.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/mobile_gestalt.py`

```
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
```

#### get_answer

```
get_answer(key: str, typ: type[CfSerializableT] | tuple[type[CfSerializableT], ...] = CfSerializableAny) -> CfSerializableT
```

Return the MGCopyAnswer value for a given key.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/mobile_gestalt.py`

```
async def get_answer(
    self, key: str, typ: type[CfSerializableT] | tuple[type[CfSerializableT], ...] = CfSerializableAny
) -> CfSerializableT:
    """Return the MGCopyAnswer value for a given key."""
    return await (await self._client.symbols.MGCopyAnswer(await self._client.cf(key))).py(typ)
```

#### set_answer

```
set_answer(key: str, value: CfSerializable) -> CfSerializable
```

Set the MGSetAnswer value for a given key.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/mobile_gestalt.py`

```
async def set_answer(self, key: str, value: CfSerializable) -> CfSerializable:
    """Set the MGSetAnswer value for a given key."""
    return await self._client.symbols.MGSetAnswer(await self._client.cf(key), await self._client.cf(value))
```

## SpringBoard

## rpcclient.clients.ios.subsystems.springboard

### SpringBoard

Bases: `ClientBound['IosClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

SpringBoardServices helpers.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/springboard.py`

```
class SpringBoard(ClientBound["IosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """SpringBoardServices helpers."""

    def __init__(self, client: "IosClient[DarwinSymbolT_co]") -> None:
        self._client = client

    async def get_spring_board_server_port(self) -> int:
        """Return the SpringBoard server port."""
        return await self._client.symbols.SBSSpringBoardServerPort()

    async def launch_application(self, bundle_identifier: str) -> None:
        """Launch an app via SpringBoardServices."""
        err = await self._client.symbols.SBSLaunchApplicationWithIdentifier(await self._client.cf(bundle_identifier), 0)
        if err != 0:
            raise RpcFailedLaunchingAppError(
                f"SBSLaunchApplicationWithIdentifier failed with: error code {err} - "
                f"{await (await self._client.symbols.SBSApplicationLaunchingErrorString(err)).py()}"
            )

    async def get_screen_lock_status(self) -> ScreenLockStatus:
        """Return lockscreen and passcode status via SpringBoardServices."""
        server_port = await self.get_spring_board_server_port()
        async with self._client.safe_malloc(8) as p_is_lock, self._client.safe_malloc(8) as p_is_passcode:
            await p_is_lock.setindex(0, 0)
            await p_is_passcode.setindex(0, 0)
            await self._client.symbols.SBGetScreenLockStatus(server_port, p_is_lock, p_is_passcode)
            return ScreenLockStatus(await p_is_lock.getindex(0) == 1, await p_is_passcode.getindex(0) == 1)

    async def open_sensitive_url_and_unlock(self, url: str, unlock: bool = True) -> None:
        """Open a URL with the system handler, optionally unlocking."""
        screen_lock_status = await self.get_screen_lock_status()
        if not unlock and screen_lock_status.lock:
            if screen_lock_status.passcode:
                raise RpcFailedLaunchingAppError(
                    "cannot open url while screen is locked with passcode. you must unlock device first"
                )
            raise RpcFailedLaunchingAppError("cannot open url while screen is locked, use unlock=True parameter")
        cf_url_ref = await (await self._client.symbols.objc_getClass("NSURL")).objc_call(
            "URLWithString:", await self._client.cf(url)
        )
        if not await self._client.symbols.SBSOpenSensitiveURLAndUnlock(cf_url_ref, unlock):
            raise RpcFailedLaunchingAppError("SBSOpenSensitiveURLAndUnlock failed")
```

#### get_spring_board_server_port

```
get_spring_board_server_port() -> int
```

Return the SpringBoard server port.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/springboard.py`

```
async def get_spring_board_server_port(self) -> int:
    """Return the SpringBoard server port."""
    return await self._client.symbols.SBSSpringBoardServerPort()
```

#### launch_application

```
launch_application(bundle_identifier: str) -> None
```

Launch an app via SpringBoardServices.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/springboard.py`

```
async def launch_application(self, bundle_identifier: str) -> None:
    """Launch an app via SpringBoardServices."""
    err = await self._client.symbols.SBSLaunchApplicationWithIdentifier(await self._client.cf(bundle_identifier), 0)
    if err != 0:
        raise RpcFailedLaunchingAppError(
            f"SBSLaunchApplicationWithIdentifier failed with: error code {err} - "
            f"{await (await self._client.symbols.SBSApplicationLaunchingErrorString(err)).py()}"
        )
```

#### get_screen_lock_status

```
get_screen_lock_status() -> ScreenLockStatus
```

Return lockscreen and passcode status via SpringBoardServices.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/springboard.py`

```
async def get_screen_lock_status(self) -> ScreenLockStatus:
    """Return lockscreen and passcode status via SpringBoardServices."""
    server_port = await self.get_spring_board_server_port()
    async with self._client.safe_malloc(8) as p_is_lock, self._client.safe_malloc(8) as p_is_passcode:
        await p_is_lock.setindex(0, 0)
        await p_is_passcode.setindex(0, 0)
        await self._client.symbols.SBGetScreenLockStatus(server_port, p_is_lock, p_is_passcode)
        return ScreenLockStatus(await p_is_lock.getindex(0) == 1, await p_is_passcode.getindex(0) == 1)
```

#### open_sensitive_url_and_unlock

```
open_sensitive_url_and_unlock(url: str, unlock: bool = True) -> None
```

Open a URL with the system handler, optionally unlocking.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/springboard.py`

```
async def open_sensitive_url_and_unlock(self, url: str, unlock: bool = True) -> None:
    """Open a URL with the system handler, optionally unlocking."""
    screen_lock_status = await self.get_screen_lock_status()
    if not unlock and screen_lock_status.lock:
        if screen_lock_status.passcode:
            raise RpcFailedLaunchingAppError(
                "cannot open url while screen is locked with passcode. you must unlock device first"
            )
        raise RpcFailedLaunchingAppError("cannot open url while screen is locked, use unlock=True parameter")
    cf_url_ref = await (await self._client.symbols.objc_getClass("NSURL")).objc_call(
        "URLWithString:", await self._client.cf(url)
    )
    if not await self._client.symbols.SBSOpenSensitiveURLAndUnlock(cf_url_ref, unlock):
        raise RpcFailedLaunchingAppError("SBSOpenSensitiveURLAndUnlock failed")
```

## Lockdown

## rpcclient.clients.ios.subsystems.lockdown

### PairRecord

Bases: `ClientBound['IosClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

Represents a Lockdown pairing record for a host.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/lockdown.py`

```
class PairRecord(ClientBound["IosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """Represents a Lockdown pairing record for a host."""

    def __init__(self, client: "IosClient[DarwinSymbolT_co]", host_id: str) -> None:
        self._client = client
        self._host_id: str = host_id

    @property
    def host_id(self) -> str:
        """Return the host ID for this pairing record."""
        return self._host_id

    async def record(self) -> dict:
        """Return the raw pairing record plist as a dictionary."""
        return plistlib.loads(
            await self._client.fs.read_file(posixpath.join(PAIR_RECORD_PATH, f"{self._host_id}.plist"))
        )

    async def get_date(self) -> datetime:
        """Return the pairing date for this host."""
        return (await type(self._client.lockdown).pair_dates(self._client.lockdown))[self._host_id]

    async def set_date(self, value: datetime) -> None:
        """Set the pairing date for this host."""
        await self._client.lockdown.set_pair_date(self._host_id, value)

    async def expiration_date(self) -> datetime:
        """Return the pairing expiration date (pairing date + 30 days)."""
        return await type(self).get_date(self) + timedelta(days=30)

    async def disable_expiration(self) -> None:
        """Disable expiration by setting the date far in the future."""
        await type(self).set_date(self, FAR_FUTURE_DATE)

    def __repr__(self) -> str:
        exp_str = ""
        return f"<{self.__class__.__name__} HOST_ID:{self.host_id}{exp_str}>"
```

#### host_id

```
host_id: str
```

Return the host ID for this pairing record.

#### record

```
record() -> dict
```

Return the raw pairing record plist as a dictionary.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/lockdown.py`

```
async def record(self) -> dict:
    """Return the raw pairing record plist as a dictionary."""
    return plistlib.loads(
        await self._client.fs.read_file(posixpath.join(PAIR_RECORD_PATH, f"{self._host_id}.plist"))
    )
```

#### get_date

```
get_date() -> datetime
```

Return the pairing date for this host.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/lockdown.py`

```
async def get_date(self) -> datetime:
    """Return the pairing date for this host."""
    return (await type(self._client.lockdown).pair_dates(self._client.lockdown))[self._host_id]
```

#### set_date

```
set_date(value: datetime) -> None
```

Set the pairing date for this host.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/lockdown.py`

```
async def set_date(self, value: datetime) -> None:
    """Set the pairing date for this host."""
    await self._client.lockdown.set_pair_date(self._host_id, value)
```

#### expiration_date

```
expiration_date() -> datetime
```

Return the pairing expiration date (pairing date + 30 days).

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/lockdown.py`

```
async def expiration_date(self) -> datetime:
    """Return the pairing expiration date (pairing date + 30 days)."""
    return await type(self).get_date(self) + timedelta(days=30)
```

#### disable_expiration

```
disable_expiration() -> None
```

Disable expiration by setting the date far in the future.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/lockdown.py`

```
async def disable_expiration(self) -> None:
    """Disable expiration by setting the date far in the future."""
    await type(self).set_date(self, FAR_FUTURE_DATE)
```

### Lockdown

Bases: `ClientBound['IosClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

Access and manage Lockdown pairing records and data ark.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/lockdown.py`

```
class Lockdown(ClientBound["IosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """Access and manage Lockdown pairing records and data ark."""

    def __init__(self, client: "IosClient[DarwinSymbolT_co]") -> None:
        self._client = client

    @staticmethod
    def get_host_id(hostname: str | None = None) -> str:
        """Return the uppercase host ID for a hostname (default: local hostname)."""
        hostname = platform.node() if hostname is None else hostname
        host_id = uuid.uuid3(uuid.NAMESPACE_DNS, hostname)
        return str(host_id).upper()

    async def pair_records(self) -> list[PairRecord]:
        """Return the list of existing pairing records."""
        return [
            PairRecord(self._client, filename.split(".")[0])
            for filename in await self._client.fs.listdir(PAIR_RECORD_PATH)
        ]

    async def pair_dates(self) -> dict:
        """Return a mapping of host_id -> pairing date."""
        raw = await self._client.preferences.cf.get_dict("com.apple.mobile.ldpair", "mobile", "kCFPreferencesAnyHost")
        return {host_id: datetime.fromtimestamp(timestmap) for host_id, timestmap in raw.items()}

    async def data_ark(self) -> SCPreference[DarwinSymbolT_co]:
        """Return the data_ark plist as an SCPreference handle."""
        return await self._client.preferences.sc.open(DATA_ARK_PATH)

    async def set_pair_date(self, host_id: str, date: datetime) -> None:
        """Set the pairing date for a given host ID."""
        await self._client.preferences.cf.set(
            host_id, int(date.timestamp()), "com.apple.mobile.ldpair", "mobile", "kCFPreferencesAnyHost"
        )

    async def get_pair_record_by_host_id(self, host_id: str) -> PairRecord[DarwinSymbolT_co]:
        """Return the PairRecord for a specific host ID."""
        return PairRecord(self._client, host_id)

    async def get_pair_record_by_hostname(self, hostname: str) -> PairRecord[DarwinSymbolT_co]:
        """Return the PairRecord for a hostname."""
        return PairRecord(self._client, self.get_host_id(hostname))

    async def get_self_pair_record(self) -> PairRecord[DarwinSymbolT_co]:
        """Return the PairRecord for the current host."""
        return await self.get_pair_record_by_host_id(self.get_host_id())

    async def add_pair_record(self, pair_record: dict, date: datetime, hostname: str | None = None) -> None:
        """Add a new pairing record and set its pairing date."""
        pair_record = dict(pair_record)
        # remove private key from pair record before adding it
        pair_record.pop("HostPrivateKey")

        host_id = self.get_host_id(hostname)
        await self._client.fs.write_file(
            posixpath.join(PAIR_RECORD_PATH, f"{host_id}.plist"), plistlib.dumps(pair_record)
        )
        await self.set_pair_date(host_id, date)

    async def disable_expiration_for_all_existing_pair_records(self) -> None:
        """Disable expiration for all existing pairing records."""
        for record in await type(self).pair_records(self):
            await record.disable_expiration()
```

#### get_host_id

```
get_host_id(hostname: str | None = None) -> str
```

Return the uppercase host ID for a hostname (default: local hostname).

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/lockdown.py`

```
@staticmethod
def get_host_id(hostname: str | None = None) -> str:
    """Return the uppercase host ID for a hostname (default: local hostname)."""
    hostname = platform.node() if hostname is None else hostname
    host_id = uuid.uuid3(uuid.NAMESPACE_DNS, hostname)
    return str(host_id).upper()
```

#### pair_records

```
pair_records() -> list[PairRecord]
```

Return the list of existing pairing records.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/lockdown.py`

```
async def pair_records(self) -> list[PairRecord]:
    """Return the list of existing pairing records."""
    return [
        PairRecord(self._client, filename.split(".")[0])
        for filename in await self._client.fs.listdir(PAIR_RECORD_PATH)
    ]
```

#### pair_dates

```
pair_dates() -> dict
```

Return a mapping of host_id -> pairing date.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/lockdown.py`

```
async def pair_dates(self) -> dict:
    """Return a mapping of host_id -> pairing date."""
    raw = await self._client.preferences.cf.get_dict("com.apple.mobile.ldpair", "mobile", "kCFPreferencesAnyHost")
    return {host_id: datetime.fromtimestamp(timestmap) for host_id, timestmap in raw.items()}
```

#### data_ark

```
data_ark() -> SCPreference[DarwinSymbolT_co]
```

Return the data_ark plist as an SCPreference handle.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/lockdown.py`

```
async def data_ark(self) -> SCPreference[DarwinSymbolT_co]:
    """Return the data_ark plist as an SCPreference handle."""
    return await self._client.preferences.sc.open(DATA_ARK_PATH)
```

#### set_pair_date

```
set_pair_date(host_id: str, date: datetime) -> None
```

Set the pairing date for a given host ID.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/lockdown.py`

```
async def set_pair_date(self, host_id: str, date: datetime) -> None:
    """Set the pairing date for a given host ID."""
    await self._client.preferences.cf.set(
        host_id, int(date.timestamp()), "com.apple.mobile.ldpair", "mobile", "kCFPreferencesAnyHost"
    )
```

#### get_pair_record_by_host_id

```
get_pair_record_by_host_id(host_id: str) -> PairRecord[DarwinSymbolT_co]
```

Return the PairRecord for a specific host ID.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/lockdown.py`

```
async def get_pair_record_by_host_id(self, host_id: str) -> PairRecord[DarwinSymbolT_co]:
    """Return the PairRecord for a specific host ID."""
    return PairRecord(self._client, host_id)
```

#### get_pair_record_by_hostname

```
get_pair_record_by_hostname(hostname: str) -> PairRecord[DarwinSymbolT_co]
```

Return the PairRecord for a hostname.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/lockdown.py`

```
async def get_pair_record_by_hostname(self, hostname: str) -> PairRecord[DarwinSymbolT_co]:
    """Return the PairRecord for a hostname."""
    return PairRecord(self._client, self.get_host_id(hostname))
```

#### get_self_pair_record

```
get_self_pair_record() -> PairRecord[DarwinSymbolT_co]
```

Return the PairRecord for the current host.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/lockdown.py`

```
async def get_self_pair_record(self) -> PairRecord[DarwinSymbolT_co]:
    """Return the PairRecord for the current host."""
    return await self.get_pair_record_by_host_id(self.get_host_id())
```

#### add_pair_record

```
add_pair_record(pair_record: dict, date: datetime, hostname: str | None = None) -> None
```

Add a new pairing record and set its pairing date.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/lockdown.py`

```
async def add_pair_record(self, pair_record: dict, date: datetime, hostname: str | None = None) -> None:
    """Add a new pairing record and set its pairing date."""
    pair_record = dict(pair_record)
    # remove private key from pair record before adding it
    pair_record.pop("HostPrivateKey")

    host_id = self.get_host_id(hostname)
    await self._client.fs.write_file(
        posixpath.join(PAIR_RECORD_PATH, f"{host_id}.plist"), plistlib.dumps(pair_record)
    )
    await self.set_pair_date(host_id, date)
```

#### disable_expiration_for_all_existing_pair_records

```
disable_expiration_for_all_existing_pair_records() -> None
```

Disable expiration for all existing pairing records.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/lockdown.py`

```
async def disable_expiration_for_all_existing_pair_records(self) -> None:
    """Disable expiration for all existing pairing records."""
    for record in await type(self).pair_records(self):
        await record.disable_expiration()
```

## Backlight

## rpcclient.clients.ios.subsystems.backlight

### Backlight

Bases: `ClientBound['IosClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

Display brightness controls.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/backlight.py`

```
class Backlight(ClientBound["IosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """Display brightness controls."""

    def __init__(self, client: "IosClient[DarwinSymbolT_co]") -> None:
        self._client = client

    @cached_async_method
    async def _get_brightness(self) -> DarwinSymbolT_co:
        BrightnessSystemClient = await self._client.symbols.objc_getClass("BrightnessSystemClient")
        if not BrightnessSystemClient:
            logging.error("failed to load BrightnessSystemClient class")
        return await BrightnessSystemClient.objc_call("new")

    async def get_brightness(self) -> float:
        """Return the display brightness in the range 0.0-1.0."""
        return (
            await (
                await (await self._get_brightness()).objc_call(
                    "copyPropertyForKey:", await self._client.cf("DisplayBrightness")
                )
            ).py(dict)
        )["Brightness"]

    async def set_brightness(self, value: float) -> None:
        """Set the display brightness in the range 0.0-1.0."""
        if not await (await self._get_brightness()).objc_call(
            "setProperty:forKey:", await self._client.cf(value), await self._client.cf("DisplayBrightness")
        ):
            raise BadReturnValueError("failed to set DisplayBrightness")
```

#### get_brightness

```
get_brightness() -> float
```

Return the display brightness in the range 0.0-1.0.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/backlight.py`

```
async def get_brightness(self) -> float:
    """Return the display brightness in the range 0.0-1.0."""
    return (
        await (
            await (await self._get_brightness()).objc_call(
                "copyPropertyForKey:", await self._client.cf("DisplayBrightness")
            )
        ).py(dict)
    )["Brightness"]
```

#### set_brightness

```
set_brightness(value: float) -> None
```

Set the display brightness in the range 0.0-1.0.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/backlight.py`

```
async def set_brightness(self, value: float) -> None:
    """Set the display brightness in the range 0.0-1.0."""
    if not await (await self._get_brightness()).objc_call(
        "setProperty:forKey:", await self._client.cf(value), await self._client.cf("DisplayBrightness")
    ):
        raise BadReturnValueError("failed to set DisplayBrightness")
```

## AMFI

## rpcclient.clients.ios.subsystems.amfi

### Amfi

Bases: `ClientBound['IosClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

AMFI utilities (AppleMobileFileIntegrity).

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/amfi.py`

```
class Amfi(ClientBound["IosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """AMFI utilities (AppleMobileFileIntegrity)."""

    def __init__(self, client: "IosClient[DarwinSymbolT_co]") -> None:
        self._client = client
        self._client.load_framework_lazy("AppleMobileFileIntegrity")

    async def set_developer_mode_status(self, enabled: bool) -> None:
        """Enable or disable Developer Mode via the AMFI XPC service."""
        cfreply = assert_cast(
            dict,
            await self._client.xpc.send_message_using_cf_serialization(
                "com.apple.amfi.xpc", {"action": int(not (enabled))}, False
            ),
        )["cfreply"]
        raw_response = next(iter(cfreply.values()))
        if b"success" not in raw_response:
            raise RpcSetDeveloperModeError()

    async def developer_mode_status(self) -> bool:
        """Return True if Developer Mode is enabled."""
        return bool(await self._client.symbols.amfi_developer_mode_status())
```

#### set_developer_mode_status

```
set_developer_mode_status(enabled: bool) -> None
```

Enable or disable Developer Mode via the AMFI XPC service.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/amfi.py`

```
async def set_developer_mode_status(self, enabled: bool) -> None:
    """Enable or disable Developer Mode via the AMFI XPC service."""
    cfreply = assert_cast(
        dict,
        await self._client.xpc.send_message_using_cf_serialization(
            "com.apple.amfi.xpc", {"action": int(not (enabled))}, False
        ),
    )["cfreply"]
    raw_response = next(iter(cfreply.values()))
    if b"success" not in raw_response:
        raise RpcSetDeveloperModeError()
```

#### developer_mode_status

```
developer_mode_status() -> bool
```

Return True if Developer Mode is enabled.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/amfi.py`

```
async def developer_mode_status(self) -> bool:
    """Return True if Developer Mode is enabled."""
    return bool(await self._client.symbols.amfi_developer_mode_status())
```

## Wi-Fi

## rpcclient.clients.ios.subsystems.wifi

### WifiSavedNetwork

Bases: `ClientBound['IosClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/wifi.py`

```
class WifiSavedNetwork(ClientBound["IosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    def __init__(
        self, client: "IosClient[DarwinSymbolT_co]", wifi_manager: DarwinSymbolT_co, network: DarwinSymbolT_co
    ) -> None:
        self._client = client
        self._wifi_manager: DarwinSymbolT_co = wifi_manager
        self._network: DarwinSymbolT_co = network

    async def ssid(self) -> bytes:
        """Return the network SSID as raw bytes."""
        return await self.get_property("SSID", bytes)

    async def bssid(self) -> str:
        """Return the network BSSID as a string."""
        return await self.get_property("BSSID", str)

    async def get_property(
        self, name: str, typ: type[CfSerializableT] | tuple[type[CfSerializableT], ...] = CfSerializableAny
    ) -> CfSerializableT:
        """Return a WiFiNetwork property by name from the underlying CF object."""
        return await (await self._client.symbols.WiFiNetworkGetProperty(self._network, await self._client.cf(name))).py(
            typ
        )

    async def forget(self) -> None:
        """Remove this network from the saved networks list."""
        await self._client.symbols.WiFiManagerClientRemoveNetwork(self._wifi_manager, self._network)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} (async)>"
```

#### ssid

```
ssid() -> bytes
```

Return the network SSID as raw bytes.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/wifi.py`

```
async def ssid(self) -> bytes:
    """Return the network SSID as raw bytes."""
    return await self.get_property("SSID", bytes)
```

#### bssid

```
bssid() -> str
```

Return the network BSSID as a string.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/wifi.py`

```
async def bssid(self) -> str:
    """Return the network BSSID as a string."""
    return await self.get_property("BSSID", str)
```

#### get_property

```
get_property(name: str, typ: type[CfSerializableT] | tuple[type[CfSerializableT], ...] = CfSerializableAny) -> CfSerializableT
```

Return a WiFiNetwork property by name from the underlying CF object.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/wifi.py`

```
async def get_property(
    self, name: str, typ: type[CfSerializableT] | tuple[type[CfSerializableT], ...] = CfSerializableAny
) -> CfSerializableT:
    """Return a WiFiNetwork property by name from the underlying CF object."""
    return await (await self._client.symbols.WiFiNetworkGetProperty(self._network, await self._client.cf(name))).py(
        typ
    )
```

#### forget

```
forget() -> None
```

Remove this network from the saved networks list.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/wifi.py`

```
async def forget(self) -> None:
    """Remove this network from the saved networks list."""
    await self._client.symbols.WiFiManagerClientRemoveNetwork(self._wifi_manager, self._network)
```

### WifiScannedNetwork

Bases: `ClientBound['IosClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/wifi.py`

```
class WifiScannedNetwork(ClientBound["IosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    def __init__(self, client: "IosClient[DarwinSymbolT_co]", interface: DarwinSymbolT_co, network: dict) -> None:
        self._client = client
        self._interface = interface
        self.network = network

    @property
    def ssid(self) -> bytes:
        """Return the scanned network SSID as raw bytes."""
        return self.network["SSID"]

    @property
    def bssid(self) -> str:
        """Return the scanned network BSSID as a string."""
        return self.network["BSSID"]

    @property
    def rssi(self) -> int:
        """Return the received signal strength indicator (RSSI)."""
        return ctypes.c_int64(self.network["RSSI"]).value

    @property
    def channel(self) -> int:
        """Return the Wi-Fi channel number."""
        return self.network["CHANNEL"]

    async def connect(self, password: str | None = None) -> None:
        """Associate to this network, optionally providing a password."""
        result = await self._client.symbols.Apple80211Associate(
            self._interface,
            await self._client.cf(self.network),
            await self._client.cf(password) if password else 0,
        )

        if result:
            raise BadReturnValueError(f"Apple80211Associate() failed with: {result}")

    async def disconnect(self) -> None:
        """Disassociate from the current network."""
        if await self._client.symbols.Apple80211Disassociate(self._interface):
            raise BadReturnValueError("Apple80211Disassociate() failed")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} (async)>"
```

#### ssid

```
ssid: bytes
```

Return the scanned network SSID as raw bytes.

#### bssid

```
bssid: str
```

Return the scanned network BSSID as a string.

#### rssi

```
rssi: int
```

Return the received signal strength indicator (RSSI).

#### channel

```
channel: int
```

Return the Wi-Fi channel number.

#### connect

```
connect(password: str | None = None) -> None
```

Associate to this network, optionally providing a password.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/wifi.py`

```
async def connect(self, password: str | None = None) -> None:
    """Associate to this network, optionally providing a password."""
    result = await self._client.symbols.Apple80211Associate(
        self._interface,
        await self._client.cf(self.network),
        await self._client.cf(password) if password else 0,
    )

    if result:
        raise BadReturnValueError(f"Apple80211Associate() failed with: {result}")
```

#### disconnect

```
disconnect() -> None
```

Disassociate from the current network.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/wifi.py`

```
async def disconnect(self) -> None:
    """Disassociate from the current network."""
    if await self._client.symbols.Apple80211Disassociate(self._interface):
        raise BadReturnValueError("Apple80211Disassociate() failed")
```

### WifiInterface

Bases: `Allocated['IosClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/wifi.py`

```
class WifiInterface(Allocated["IosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    def __init__(self, client: "IosClient[DarwinSymbolT_co]", interface: DarwinSymbolT_co) -> None:
        super().__init__()
        self._client = client
        self._interface: DarwinSymbolT_co = interface

    async def scan(self, options: dict | None = None) -> list[WifiScannedNetwork[DarwinSymbolT_co]]:
        """Scan for nearby networks and return a list of WifiScannedNetwork."""

        if options is None:
            options = {}

        result = []
        async with self._client.safe_malloc(8) as p_found_networks:
            while True:
                scan_result = await self._client.symbols.Apple80211Scan(
                    self._interface, p_found_networks, await self._client.cf(options)
                )
                if scan_result == 0:
                    break
                elif scan_result == -1:
                    raise BadReturnValueError("Apple80211Scan failed")
                # else, try again

            for network in await (await p_found_networks.getindex(0)).py(list):
                result.append(WifiScannedNetwork(self._client, self._interface, network))

        return result

    async def disconnect(self) -> None:
        """Disconnect from the currently associated Wi-Fi network."""
        await self._client.symbols.Apple80211Disassociate(self._interface)

    async def _deallocate(self) -> None:
        await self._client.symbols.Apple80211Close(self._interface)
```

#### scan

```
scan(options: dict | None = None) -> list[WifiScannedNetwork[DarwinSymbolT_co]]
```

Scan for nearby networks and return a list of WifiScannedNetwork.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/wifi.py`

```
async def scan(self, options: dict | None = None) -> list[WifiScannedNetwork[DarwinSymbolT_co]]:
    """Scan for nearby networks and return a list of WifiScannedNetwork."""

    if options is None:
        options = {}

    result = []
    async with self._client.safe_malloc(8) as p_found_networks:
        while True:
            scan_result = await self._client.symbols.Apple80211Scan(
                self._interface, p_found_networks, await self._client.cf(options)
            )
            if scan_result == 0:
                break
            elif scan_result == -1:
                raise BadReturnValueError("Apple80211Scan failed")
            # else, try again

        for network in await (await p_found_networks.getindex(0)).py(list):
            result.append(WifiScannedNetwork(self._client, self._interface, network))

    return result
```

#### disconnect

```
disconnect() -> None
```

Disconnect from the currently associated Wi-Fi network.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/wifi.py`

```
async def disconnect(self) -> None:
    """Disconnect from the currently associated Wi-Fi network."""
    await self._client.symbols.Apple80211Disassociate(self._interface)
```

### IosWifi

Bases: `ClientBound['IosClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

iOS Wi-Fi utilities backed by WiFiKit and Apple80211.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/wifi.py`

```
class IosWifi(ClientBound["IosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """iOS Wi-Fi utilities backed by WiFiKit and Apple80211."""

    def __init__(self, client: "IosClient[DarwinSymbolT_co]") -> None:
        self._client = client
        self._client.load_framework_lazy("WiFiKit")

    @cached_async_method
    async def _get_wifi_manager(self) -> DarwinSymbolT_co:
        wifi_manager = await self._client.symbols.WiFiManagerClientCreate(0, 0)
        if not wifi_manager:
            await self._client.raise_errno_exception("WiFiManagerClientCreate failed")
        return wifi_manager

    async def saved_networks(self) -> list[WifiSavedNetwork]:
        """Return saved Wi-Fi networks known to the device."""
        network_list = await (
            await self._client.symbols.WiFiManagerClientCopyNetworks(await self._get_wifi_manager())
        ).py((list, type(None)))
        if not network_list:
            return []

        return [WifiSavedNetwork(self._client, await self._get_wifi_manager(), network) for network in network_list]

    async def interfaces(self) -> list[str]:
        """Return a list of available Wi-Fi interface names."""
        async with self._client.safe_malloc(8) as p_interface:
            if await self._client.symbols.Apple80211Open(p_interface):
                await self._client.raise_errno_exception("Apple80211Open() failed")

            async with self._client.safe_malloc(8) as p_interface_names:
                if await self._client.symbols.Apple80211GetIfListCopy(await p_interface.getindex(0), p_interface_names):
                    await self._client.raise_errno_exception("Apple80211GetIfListCopy() failed")

                return await (await p_interface_names.getindex(0)).py(list)

    async def turn_on(self) -> None:
        """Enable Wi-Fi on the device."""
        await self._set(True)

    async def turn_off(self) -> None:
        """Disable Wi-Fi on the device."""
        await self._set(False)

    async def is_on(self) -> bool:
        """Return True if Wi-Fi is enabled."""
        return bool(
            await (
                await self._client.symbols.WiFiManagerClientCopyProperty(
                    await self._get_wifi_manager(), await self._client.cf("AllowEnable")
                )
            ).py()
        )

    async def get_interface(self, interface_name: str | None = None) -> WifiInterface[DarwinSymbolT_co]:
        """Return a bound interface handle for scanning and associating."""
        async with self._client.safe_malloc(8) as p_handle:
            if await self._client.symbols.Apple80211Open(p_handle):
                await self._client.raise_errno_exception("Apple80211Open() failed")
            handle = await p_handle.getindex(0)

        if interface_name is None:
            wifi_interfaces = await type(self).interfaces(self)

            if not wifi_interfaces:
                raise RpcClientException("no available wifi interfaces were found")

            interface_name = wifi_interfaces[0]

        if await self._client.symbols.Apple80211BindToInterface(handle, await self._client.cf(interface_name)):
            await self._client.raise_errno_exception("Apple80211BindToInterface failed")

        return WifiInterface(self._client, handle)

    async def _set(self, is_on: bool) -> None:
        if not await self._client.symbols.WiFiManagerClientSetProperty(
            await self._get_wifi_manager(), await self._client.cf("AllowEnable"), await self._client.cf(is_on)
        ):
            raise BadReturnValueError("WiFiManagerClientSetProperty() failed")
```

#### saved_networks

```
saved_networks() -> list[WifiSavedNetwork]
```

Return saved Wi-Fi networks known to the device.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/wifi.py`

```
async def saved_networks(self) -> list[WifiSavedNetwork]:
    """Return saved Wi-Fi networks known to the device."""
    network_list = await (
        await self._client.symbols.WiFiManagerClientCopyNetworks(await self._get_wifi_manager())
    ).py((list, type(None)))
    if not network_list:
        return []

    return [WifiSavedNetwork(self._client, await self._get_wifi_manager(), network) for network in network_list]
```

#### interfaces

```
interfaces() -> list[str]
```

Return a list of available Wi-Fi interface names.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/wifi.py`

```
async def interfaces(self) -> list[str]:
    """Return a list of available Wi-Fi interface names."""
    async with self._client.safe_malloc(8) as p_interface:
        if await self._client.symbols.Apple80211Open(p_interface):
            await self._client.raise_errno_exception("Apple80211Open() failed")

        async with self._client.safe_malloc(8) as p_interface_names:
            if await self._client.symbols.Apple80211GetIfListCopy(await p_interface.getindex(0), p_interface_names):
                await self._client.raise_errno_exception("Apple80211GetIfListCopy() failed")

            return await (await p_interface_names.getindex(0)).py(list)
```

#### turn_on

```
turn_on() -> None
```

Enable Wi-Fi on the device.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/wifi.py`

```
async def turn_on(self) -> None:
    """Enable Wi-Fi on the device."""
    await self._set(True)
```

#### turn_off

```
turn_off() -> None
```

Disable Wi-Fi on the device.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/wifi.py`

```
async def turn_off(self) -> None:
    """Disable Wi-Fi on the device."""
    await self._set(False)
```

#### is_on

```
is_on() -> bool
```

Return True if Wi-Fi is enabled.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/wifi.py`

```
async def is_on(self) -> bool:
    """Return True if Wi-Fi is enabled."""
    return bool(
        await (
            await self._client.symbols.WiFiManagerClientCopyProperty(
                await self._get_wifi_manager(), await self._client.cf("AllowEnable")
            )
        ).py()
    )
```

#### get_interface

```
get_interface(interface_name: str | None = None) -> WifiInterface[DarwinSymbolT_co]
```

Return a bound interface handle for scanning and associating.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/wifi.py`

```
async def get_interface(self, interface_name: str | None = None) -> WifiInterface[DarwinSymbolT_co]:
    """Return a bound interface handle for scanning and associating."""
    async with self._client.safe_malloc(8) as p_handle:
        if await self._client.symbols.Apple80211Open(p_handle):
            await self._client.raise_errno_exception("Apple80211Open() failed")
        handle = await p_handle.getindex(0)

    if interface_name is None:
        wifi_interfaces = await type(self).interfaces(self)

        if not wifi_interfaces:
            raise RpcClientException("no available wifi interfaces were found")

        interface_name = wifi_interfaces[0]

    if await self._client.symbols.Apple80211BindToInterface(handle, await self._client.cf(interface_name)):
        await self._client.raise_errno_exception("Apple80211BindToInterface failed")

    return WifiInterface(self._client, handle)
```

## Telephony

## rpcclient.clients.ios.subsystems.telephony

### Call

Bases: `ClientBound['IosClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

Represents a single ongoing call.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/telephony.py`

```
class Call(ClientBound["IosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """Represents a single ongoing call."""

    def __init__(
        self, client: "IosClient[DarwinSymbolT_co]", controller: DarwinSymbolT_co, call: DarwinSymbolT_co
    ) -> None:
        self._client = client
        self._controller: DarwinSymbolT_co = controller
        self._call: DarwinSymbolT_co = call

    async def disconnect(self) -> None:
        """Disconnect the current call."""
        await self._send_action("CXEndCallAction")

    async def answer(self) -> None:
        """Answer the current call."""
        await self._send_action("CXAnswerCallAction")

    async def _send_action(self, action_name: str) -> None:
        action_class = await self._client.symbols.objc_getClass(action_name)
        action = await (await action_class.objc_call("alloc")).objc_call("initWithCallUUID:", await self._uuid())
        await self._controller.objc_call(
            "requestTransactionWithAction:completion:", action, await self._client.get_dummy_block()
        )

    async def _uuid(self) -> Any:
        return await self._call.objc_call("UUID")
```

#### disconnect

```
disconnect() -> None
```

Disconnect the current call.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/telephony.py`

```
async def disconnect(self) -> None:
    """Disconnect the current call."""
    await self._send_action("CXEndCallAction")
```

#### answer

```
answer() -> None
```

Answer the current call.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/telephony.py`

```
async def answer(self) -> None:
    """Answer the current call."""
    await self._send_action("CXAnswerCallAction")
```

### Telephony

Bases: `ClientBound['IosClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

Telephony utilities backed by CallKit and CoreTelephony.

Accessing real telephony requires the entitlement "application-identifier" to be set to "com.apple.coretelephony".

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/telephony.py`

```
class Telephony(ClientBound["IosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """
    Telephony utilities backed by CallKit and CoreTelephony.

    Accessing real telephony requires the entitlement "application-identifier"
    to be set to "com.apple.coretelephony".
    """

    def __init__(self, client: "IosClient[DarwinSymbolT_co]") -> None:
        self._client = client
        self._client.load_framework_lazy("CallKit")

    @cached_async_method
    async def cx_call_controller(self) -> DarwinSymbolT_co:
        return await (await self._client.symbols.objc_getClass("CXCallController")).objc_call("new")

    @cached_async_method
    async def cx_call_observer(self) -> DarwinSymbolT_co:
        return await (await type(self).cx_call_controller(self)).objc_call("callObserver")

    @cached_async_method
    async def ct_message_center(self) -> DarwinSymbolT_co:
        return await (await self._client.symbols.objc_getClass("CTMessageCenter")).objc_call("sharedMessageCenter")

    async def dial(self, number: str) -> None:
        """
        Start a call to a number.

        Use `current_call` to access the created call.
        """
        await self._client.symbols.CTCallDial(await self._client.cf(number))

    async def send_sms(self, to_address: str, text: str, smsc: str = "1111") -> None:
        """
        Send an SMS message.

        :param to_address: Destination phone address.
        :param text: Message text.
        :param smsc: Originator short message service center address.
        """
        await (await type(self).ct_message_center(self)).objc_call(
            "sendSMSWithText:serviceCenter:toAddress:",
            await self._client.cf(text),
            await self._client.cf(smsc),
            await self._client.cf(to_address),
        )

    async def current_call(self) -> Call | None:
        """
        Return an object representing the current active call, if any.
        """
        calls = await (await type(self).cx_call_observer(self)).objc_call("calls")
        call_count = await calls.objc_call("count")

        call_list = [await calls.objc_call("objectAtIndex:", i) for i in range(call_count)]

        for call_id in range(call_count):
            call = call_list[call_id]
            if await call.objc_call("hasEnded"):
                continue
            return Call(self._client, await type(self).cx_call_controller(self), call)

        return None
```

#### dial

```
dial(number: str) -> None
```

Start a call to a number.

Use `current_call` to access the created call.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/telephony.py`

```
async def dial(self, number: str) -> None:
    """
    Start a call to a number.

    Use `current_call` to access the created call.
    """
    await self._client.symbols.CTCallDial(await self._client.cf(number))
```

#### send_sms

```
send_sms(to_address: str, text: str, smsc: str = '1111') -> None
```

Send an SMS message.

Parameters:

| Name         | Type  | Description                                      | Default    |
| ------------ | ----- | ------------------------------------------------ | ---------- |
| `to_address` | `str` | Destination phone address.                       | *required* |
| `text`       | `str` | Message text.                                    | *required* |
| `smsc`       | `str` | Originator short message service center address. | `'1111'`   |

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/telephony.py`

```
async def send_sms(self, to_address: str, text: str, smsc: str = "1111") -> None:
    """
    Send an SMS message.

    :param to_address: Destination phone address.
    :param text: Message text.
    :param smsc: Originator short message service center address.
    """
    await (await type(self).ct_message_center(self)).objc_call(
        "sendSMSWithText:serviceCenter:toAddress:",
        await self._client.cf(text),
        await self._client.cf(smsc),
        await self._client.cf(to_address),
    )
```

#### current_call

```
current_call() -> Call | None
```

Return an object representing the current active call, if any.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/telephony.py`

```
async def current_call(self) -> Call | None:
    """
    Return an object representing the current active call, if any.
    """
    calls = await (await type(self).cx_call_observer(self)).objc_call("calls")
    call_count = await calls.objc_call("count")

    call_list = [await calls.objc_call("objectAtIndex:", i) for i in range(call_count)]

    for call_id in range(call_count):
        call = call_list[call_id]
        if await call.objc_call("hasEnded"):
            continue
        return Call(self._client, await type(self).cx_call_controller(self), call)

    return None
```

## Accessibility

## rpcclient.clients.ios.subsystems.accessibility

### AXElement

Bases: `AbstractSymbol`, `ClientBound['IosClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

Wrapper around the device AXElement Objective-C object.

Built from reversed XADInspectorManager methods.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
class AXElement(AbstractSymbol, ClientBound["IosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """
    Wrapper around the device AXElement Objective-C object.

    Built from reversed XADInspectorManager methods.
    """

    def __init__(self, value: int, client: "IosClient[DarwinSymbolT_co]") -> None:
        self._client = client
        self._sym: DarwinSymbolT_co = client.symbol(value)

    def _symbol_from_value(self, value: int) -> DarwinSymbolT_co:
        return self._client.symbol(value)

    async def peek(self, count: int, offset: int = 0) -> bytes:
        return await self._sym.peek(count, offset)

    async def poke(self, buf: bytes, offset: int = 0) -> Any:
        return await self._sym.poke(buf, offset)

    async def peek_str(self, encoding="utf-8") -> str:
        """peek string at given address"""
        return await self._sym.peek_str(encoding=encoding)

    @property
    def arch(self) -> object:
        return self._client.arch

    @property
    def endianness(self) -> str:
        return self._client._endianness

    async def get_dl_info(self) -> Container:
        return await self._sym.get_dl_info()

    async def objc_call(
        self, selector: str, *params: RemoteCallArg, va_list_index: int | None = None
    ) -> DarwinSymbolT_co:
        """call an objc method on a given object and return a symbol"""
        return await self._sym.objc_call(selector, *params, va_list_index=va_list_index)

    async def first_element(self) -> Self:
        """Return the first element in the accessibility hierarchy."""
        result = await self._element_for_attribute(3000)
        if not result:
            raise FirstElementNotFoundError("failed to get first element in hierarchy")

        if await (await type(result).ui_element(result)).objc_call("boolWithAXAttribute:", 2046):
            result = await result._element_for_attribute(3000)
        assert result is not None
        return result

    async def last_element(self) -> Self:
        """Return the last element in the accessibility hierarchy."""
        result = await self._element_for_attribute(3016)
        if not result:
            raise LastElementNotFoundError("failed to get last element in hierarchy")

        if await (await type(result).ui_element(result)).objc_call("boolWithAXAttribute:", 2046):
            result = await result._element_for_attribute(3016)

        assert result is not None
        return result

    async def identifier(self) -> str:
        """Return the element identifier."""
        return await (await self.objc_call("identifier")).py(str)

    async def url(self) -> str:
        """Return the element URL."""
        return await (await self.objc_call("url")).py(str)

    async def path(self) -> DarwinSymbolT_co:
        """Return the element path object."""
        return await self.objc_call("path")

    async def frame(self) -> CGRect:
        """Return the element frame as a CGRect."""
        result = await self._sym.objc_call_raw("frame")
        return CGRect(origin=CGPoint(x=result.d0, y=result.d1), size=CGSize(width=result.d2, height=result.d3))

    async def label(self) -> str | None:
        """Return the visible label text."""
        return await (await self.objc_call("label")).py(str)

    async def value(self) -> str:
        """Return the element value."""
        return await (await self.objc_call("value")).py(str)

    async def bundle_identifier(self) -> str:
        """Return the owning app bundle identifier."""
        return await (await self.objc_call("bundleId")).py(str)

    async def pid(self) -> int:
        """Return the owning process ID."""
        return (await self.objc_call("pid")).c_uint16

    async def process_name(self) -> str:
        """Return the owning process name."""
        return await (await self.objc_call("processName")).py(str)

    async def screen_locked(self) -> bool:
        """Return True if the screen is locked."""
        return await self.objc_call("isScreenLocked") == 1

    async def is_accessibility_opaque_element_provider(self) -> bool:
        """Return True if the element provides its own accessibility hierarchy."""
        return await self.objc_call("isAccessibilityOpaqueElementProvider") != 0

    async def parent(self) -> Self | None:
        """Return the parent element if available."""
        tmp = await self._element_for_attribute(2066)
        if tmp:
            return tmp

        tmp = await self._element_for_attribute(2092)
        if tmp:
            return await type(tmp).parent(tmp)

        return None

    async def ui_element(self) -> DarwinSymbolT_co:
        """Return the underlying AXUIElement."""
        return await self.objc_call("uiElement")

    async def traits(self) -> AXTraits:
        """Return the element traits as AXTraits."""
        return AXTraits((await self.objc_call("traits")).c_uint64)

    async def elements(self) -> list[Self]:
        """Return the list of currently displayed elements."""
        result = []
        elements = await self.objc_call("explorerElements")
        for i in range(await elements.objc_call("count")):
            result.append(self._client.accessibility.axelement(await elements.objc_call("objectAtIndex:", i)))
        return result

    async def insert_text(self, text: str) -> None:
        """Insert text into the focused editable element."""
        await self.objc_call("insertText:", await self._client.cf(text))

    async def delete_text(self) -> None:
        """Delete a character from the focused editable element."""
        await self.objc_call("deleteText")

    async def highlight(self) -> None:
        """Draw a frame around the element, replacing any existing frame."""
        frame = await type(self).frame(self)
        await self._client.accessibility.draw_frame(frame.origin.x, frame.origin.y, frame.size.width, frame.size.height)

    async def scroll_to_visible(self) -> None:
        """Scroll until the element becomes fully visible."""
        await self.objc_call("scrollToVisible")

    async def press(self) -> None:
        """Activate/press the element."""
        await self.objc_call("press")

    async def long_press(self) -> None:
        """Long-press the element."""
        await self.objc_call("longPress")

    async def _iter(self) -> "AsyncGenerator[AXElement[DarwinSymbolT_co]]":
        current = await type(self).first_element(self)
        while current:
            yield current
            current = await current.next()

    def __aiter__(self) -> "AsyncIterator[AXElement[DarwinSymbolT_co]]":
        return self._iter()

    async def _element_for_attribute(self, axattribute: int, parameter: Any | None = None) -> Self | None:
        if parameter is None:
            result = await self.objc_call("elementForAttribute:", axattribute)
        else:
            result = await self.objc_call("elementForAttribute:parameter:", axattribute, parameter)
        return type(self)(result, self._client)

    async def _next_opaque(self, direction: AXDirection = AXDirection.Next) -> Self | None:
        element = self

        if not await type(element).is_accessibility_opaque_element_provider(element):
            element = await type(self).parent(self)

        if not element:
            return None

        element = await element._element_for_attribute(
            95225,
            await self._client.cf([
                direction,
                0,
                await (await self._client.symbols.objc_getClass("NSValue")).objc_call("valueWithRange:", 0x7FFFFFFF, 0),
                "AXAudit",
            ]),
        )

        if element:
            ui_element = await type(element).ui_element(element)
            if ui_element and await ui_element.objc_call("boolWithAXAttribute:", 2046):
                return await element._next_opaque()

        return element

    async def _next_elements_with_count(self, count: int) -> list[Self]:
        elements = await self.objc_call("nextElementsWithCount:", count)
        result = []
        for i in range(await elements.objc_call("count")):
            result.append(type(self)(await elements.objc_call("objectAtIndex:", i), self._client))
        return result

    async def _previous_elements_with_count(self, count: int) -> list[Self]:
        elements = await self.objc_call("previousElementsWithCount:", count)
        result = []
        for i in range(await elements.objc_call("count")):
            result.append(type(self)(await elements.objc_call("objectAtIndex:", i), self._client))
        return result

    async def _set_assistive_focus(self, focused: bool) -> None:
        await (await type(self).ui_element(self)).objc_call(
            "setAXAttribute:withObject:synchronous:",
            2018,
            await self._client.cf({"focused": int(focused), "assistiveTech": "AXAudit"}),
            0,
        )
        parent = await self._element_for_attribute(2092)
        if parent:
            await parent._set_assistive_focus(focused)

    async def next(
        self, direction: AXDirection = AXDirection.Next, cyclic: bool = False
    ) -> "AXElement[DarwinSymbolT_co] | None":
        """
        Return and scroll to the next element in the current view.

        This method was created by reversing [XADInspectorManager _nextElementNavigationInDirection:forElement:]
        so we don't really know much about the used consts.
        """
        next_opaque = await self._next_opaque(direction)

        if not await type(self).is_accessibility_opaque_element_provider(self) and next_opaque:
            return next_opaque

        if direction == AXDirection.Next:
            next_or_prev_list = await self._next_elements_with_count(1)
        else:
            next_or_prev_list = await self._previous_elements_with_count(1)

        if next_or_prev_list:
            result = next_or_prev_list[0]
            if await type(result).is_accessibility_opaque_element_provider(result):
                focused_element = await self._element_for_attribute(95226, self._client.cf("AXAudit"))
                if focused_element:
                    await focused_element._set_assistive_focus(False)
                await result._set_assistive_focus(False)
                result = await result._next_opaque(direction)

            if result and not await type(result).is_accessibility_opaque_element_provider(result):
                return result

        result = await self._next_opaque(direction)
        if result:
            return result

        if not await type(self).is_accessibility_opaque_element_provider(self):
            parent = await type(self).parent(self)
            if parent:
                return await parent.next(direction, cyclic=cyclic)

        if cyclic:
            app = await self._client.accessibility._get_primary_app()
            if direction == AXDirection.Next:
                return await type(app).first_element(app)
            return await type(app).last_element(app)

        return None

    async def compare_label(self, label: str, auto_scroll: bool = True, draw_frame: bool = True) -> bool:
        """
        Compare a label against this element's label.

        Optionally, scroll to the element and draw a highlight frame.
        """
        if auto_scroll:
            await self.scroll_to_visible()

        if draw_frame:
            await self.highlight()

        return await type(self).label(self) == label

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} (async)>"

    def __str__(self) -> str:
        return repr(self)
```

#### peek_str

```
peek_str(encoding='utf-8') -> str
```

peek string at given address

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def peek_str(self, encoding="utf-8") -> str:
    """peek string at given address"""
    return await self._sym.peek_str(encoding=encoding)
```

#### objc_call

```
objc_call(selector: str, *params: RemoteCallArg, va_list_index: int | None = None) -> DarwinSymbolT_co
```

call an objc method on a given object and return a symbol

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def objc_call(
    self, selector: str, *params: RemoteCallArg, va_list_index: int | None = None
) -> DarwinSymbolT_co:
    """call an objc method on a given object and return a symbol"""
    return await self._sym.objc_call(selector, *params, va_list_index=va_list_index)
```

#### first_element

```
first_element() -> Self
```

Return the first element in the accessibility hierarchy.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def first_element(self) -> Self:
    """Return the first element in the accessibility hierarchy."""
    result = await self._element_for_attribute(3000)
    if not result:
        raise FirstElementNotFoundError("failed to get first element in hierarchy")

    if await (await type(result).ui_element(result)).objc_call("boolWithAXAttribute:", 2046):
        result = await result._element_for_attribute(3000)
    assert result is not None
    return result
```

#### last_element

```
last_element() -> Self
```

Return the last element in the accessibility hierarchy.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def last_element(self) -> Self:
    """Return the last element in the accessibility hierarchy."""
    result = await self._element_for_attribute(3016)
    if not result:
        raise LastElementNotFoundError("failed to get last element in hierarchy")

    if await (await type(result).ui_element(result)).objc_call("boolWithAXAttribute:", 2046):
        result = await result._element_for_attribute(3016)

    assert result is not None
    return result
```

#### identifier

```
identifier() -> str
```

Return the element identifier.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def identifier(self) -> str:
    """Return the element identifier."""
    return await (await self.objc_call("identifier")).py(str)
```

#### url

```
url() -> str
```

Return the element URL.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def url(self) -> str:
    """Return the element URL."""
    return await (await self.objc_call("url")).py(str)
```

#### path

```
path() -> DarwinSymbolT_co
```

Return the element path object.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def path(self) -> DarwinSymbolT_co:
    """Return the element path object."""
    return await self.objc_call("path")
```

#### frame

```
frame() -> CGRect
```

Return the element frame as a CGRect.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def frame(self) -> CGRect:
    """Return the element frame as a CGRect."""
    result = await self._sym.objc_call_raw("frame")
    return CGRect(origin=CGPoint(x=result.d0, y=result.d1), size=CGSize(width=result.d2, height=result.d3))
```

#### label

```
label() -> str | None
```

Return the visible label text.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def label(self) -> str | None:
    """Return the visible label text."""
    return await (await self.objc_call("label")).py(str)
```

#### value

```
value() -> str
```

Return the element value.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def value(self) -> str:
    """Return the element value."""
    return await (await self.objc_call("value")).py(str)
```

#### bundle_identifier

```
bundle_identifier() -> str
```

Return the owning app bundle identifier.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def bundle_identifier(self) -> str:
    """Return the owning app bundle identifier."""
    return await (await self.objc_call("bundleId")).py(str)
```

#### pid

```
pid() -> int
```

Return the owning process ID.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def pid(self) -> int:
    """Return the owning process ID."""
    return (await self.objc_call("pid")).c_uint16
```

#### process_name

```
process_name() -> str
```

Return the owning process name.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def process_name(self) -> str:
    """Return the owning process name."""
    return await (await self.objc_call("processName")).py(str)
```

#### screen_locked

```
screen_locked() -> bool
```

Return True if the screen is locked.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def screen_locked(self) -> bool:
    """Return True if the screen is locked."""
    return await self.objc_call("isScreenLocked") == 1
```

#### is_accessibility_opaque_element_provider

```
is_accessibility_opaque_element_provider() -> bool
```

Return True if the element provides its own accessibility hierarchy.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def is_accessibility_opaque_element_provider(self) -> bool:
    """Return True if the element provides its own accessibility hierarchy."""
    return await self.objc_call("isAccessibilityOpaqueElementProvider") != 0
```

#### parent

```
parent() -> Self | None
```

Return the parent element if available.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def parent(self) -> Self | None:
    """Return the parent element if available."""
    tmp = await self._element_for_attribute(2066)
    if tmp:
        return tmp

    tmp = await self._element_for_attribute(2092)
    if tmp:
        return await type(tmp).parent(tmp)

    return None
```

#### ui_element

```
ui_element() -> DarwinSymbolT_co
```

Return the underlying AXUIElement.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def ui_element(self) -> DarwinSymbolT_co:
    """Return the underlying AXUIElement."""
    return await self.objc_call("uiElement")
```

#### traits

```
traits() -> AXTraits
```

Return the element traits as AXTraits.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def traits(self) -> AXTraits:
    """Return the element traits as AXTraits."""
    return AXTraits((await self.objc_call("traits")).c_uint64)
```

#### elements

```
elements() -> list[Self]
```

Return the list of currently displayed elements.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def elements(self) -> list[Self]:
    """Return the list of currently displayed elements."""
    result = []
    elements = await self.objc_call("explorerElements")
    for i in range(await elements.objc_call("count")):
        result.append(self._client.accessibility.axelement(await elements.objc_call("objectAtIndex:", i)))
    return result
```

#### insert_text

```
insert_text(text: str) -> None
```

Insert text into the focused editable element.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def insert_text(self, text: str) -> None:
    """Insert text into the focused editable element."""
    await self.objc_call("insertText:", await self._client.cf(text))
```

#### delete_text

```
delete_text() -> None
```

Delete a character from the focused editable element.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def delete_text(self) -> None:
    """Delete a character from the focused editable element."""
    await self.objc_call("deleteText")
```

#### highlight

```
highlight() -> None
```

Draw a frame around the element, replacing any existing frame.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def highlight(self) -> None:
    """Draw a frame around the element, replacing any existing frame."""
    frame = await type(self).frame(self)
    await self._client.accessibility.draw_frame(frame.origin.x, frame.origin.y, frame.size.width, frame.size.height)
```

#### scroll_to_visible

```
scroll_to_visible() -> None
```

Scroll until the element becomes fully visible.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def scroll_to_visible(self) -> None:
    """Scroll until the element becomes fully visible."""
    await self.objc_call("scrollToVisible")
```

#### press

```
press() -> None
```

Activate/press the element.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def press(self) -> None:
    """Activate/press the element."""
    await self.objc_call("press")
```

#### long_press

```
long_press() -> None
```

Long-press the element.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def long_press(self) -> None:
    """Long-press the element."""
    await self.objc_call("longPress")
```

#### next

```
next(direction: AXDirection = AXDirection.Next, cyclic: bool = False) -> AXElement[DarwinSymbolT_co] | None
```

Return and scroll to the next element in the current view.

This method was created by reversing [XADInspectorManager \_nextElementNavigationInDirection:forElement:] so we don't really know much about the used consts.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def next(
    self, direction: AXDirection = AXDirection.Next, cyclic: bool = False
) -> "AXElement[DarwinSymbolT_co] | None":
    """
    Return and scroll to the next element in the current view.

    This method was created by reversing [XADInspectorManager _nextElementNavigationInDirection:forElement:]
    so we don't really know much about the used consts.
    """
    next_opaque = await self._next_opaque(direction)

    if not await type(self).is_accessibility_opaque_element_provider(self) and next_opaque:
        return next_opaque

    if direction == AXDirection.Next:
        next_or_prev_list = await self._next_elements_with_count(1)
    else:
        next_or_prev_list = await self._previous_elements_with_count(1)

    if next_or_prev_list:
        result = next_or_prev_list[0]
        if await type(result).is_accessibility_opaque_element_provider(result):
            focused_element = await self._element_for_attribute(95226, self._client.cf("AXAudit"))
            if focused_element:
                await focused_element._set_assistive_focus(False)
            await result._set_assistive_focus(False)
            result = await result._next_opaque(direction)

        if result and not await type(result).is_accessibility_opaque_element_provider(result):
            return result

    result = await self._next_opaque(direction)
    if result:
        return result

    if not await type(self).is_accessibility_opaque_element_provider(self):
        parent = await type(self).parent(self)
        if parent:
            return await parent.next(direction, cyclic=cyclic)

    if cyclic:
        app = await self._client.accessibility._get_primary_app()
        if direction == AXDirection.Next:
            return await type(app).first_element(app)
        return await type(app).last_element(app)

    return None
```

#### compare_label

```
compare_label(label: str, auto_scroll: bool = True, draw_frame: bool = True) -> bool
```

Compare a label against this element's label.

Optionally, scroll to the element and draw a highlight frame.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def compare_label(self, label: str, auto_scroll: bool = True, draw_frame: bool = True) -> bool:
    """
    Compare a label against this element's label.

    Optionally, scroll to the element and draw a highlight frame.
    """
    if auto_scroll:
        await self.scroll_to_visible()

    if draw_frame:
        await self.highlight()

    return await type(self).label(self) == label
```

### Accessibility

Bases: `ClientBound['IosClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

Accessibility utilities and UI element discovery.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
class Accessibility(ClientBound["IosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """Accessibility utilities and UI element discovery."""

    def __init__(self, client: "IosClient[DarwinSymbolT_co]") -> None:
        """Initialize accessibility frameworks and UI client."""
        self._client = client
        self._client.load_framework_lazy("AXRuntime")
        self._client.load_framework_lazy("AccessibilityUI")

    @cached_async_method
    async def _get_ui_client(self) -> DarwinSymbolT_co:
        return await (await (await self._client.symbols.objc_getClass("AXUIClient")).objc_call("alloc")).objc_call(
            "initWithIdentifier:serviceBundleName:",
            await self._client.cf("AXAuditAXUIClientIdentifier"),
            await self._client.cf("AXAuditAXUIService"),
        )

    async def _get_primary_app(self) -> AXElement[DarwinSymbolT_co]:
        if not await type(self).get_enabled(self):
            raise RpcAccessibilityTurnedOffError()
        primary_app = await (await self._client.symbols.objc_getClass("AXElement")).objc_call("primaryApp")
        if primary_app == 0:
            raise RpcFailedToGetPrimaryAppError()
        return self.axelement(primary_app)

    async def primary_app(self) -> AXElement[DarwinSymbolT_co]:
        """Return the primary app AXElement."""
        return await self._get_primary_app()

    async def get_enabled(self) -> bool:
        """Return True if accessibility automation is enabled."""
        return bool(
            await self._client.symbols._AXSApplicationAccessibilityEnabled()
            or await self._client.symbols._AXSAutomationEnabled()
        )

    async def set_enabled(self, value: bool) -> None:
        """Enable or disable accessibility automation."""
        await self._client.symbols._AXSSetAutomationEnabled(int(value))

    async def hide_frame(self) -> None:
        """Hide the accessibility highlight frame."""
        await self.draw_frame(0, 0, 0, 0)

    async def set_frame_style(self, value: int) -> None:
        """Set the highlight frame style."""
        await (await self._get_ui_client()).objc_call(
            "sendSynchronousMessage:withIdentifier:error:", await self._client.cf({"frameStyle": value}), 2, 0
        )

    async def draw_frame(self, x: float, y: float, width: float, height: float) -> None:
        """Draw a highlight frame at the given coordinates."""
        rect = {"frame": f" {{{{{x},{y}}}, {{{width},{height}}}}}"}
        await (await self._get_ui_client()).objc_call(
            "sendSynchronousMessage:withIdentifier:error:", await self._client.cf(rect), 1, 0
        )

    async def wait_for_element_by_label(
        self,
        label: str,
        auto_scroll: bool = True,
        draw_frame: bool = True,
        timeout: float = 5,
        direction: AXDirection = AXDirection.Next,
        displayed_only: bool = False,
    ) -> AXElement:
        """Wait for an element with the given label to appear."""
        start = time.time()
        while time.time() - start < timeout:
            try:
                return await self._get_element_by_label(
                    label,
                    auto_scroll=auto_scroll,
                    draw_frame=draw_frame,
                    direction=direction,
                    displayed_only=displayed_only,
                )
            except ElementNotFoundError:
                pass
            except AttributeError:
                pass
        raise ElementNotFoundError(
            f'failed to find AXElement by label: "{label}" after waiting for {timeout} seconds for it to load'
        )

    async def _get_element_by_label(
        self,
        label: str,
        auto_scroll: bool = True,
        draw_frame: bool = True,
        direction: AXDirection = AXDirection.Next,
        displayed_only: bool = False,
    ) -> AXElement:
        """Return an AXElement with the given label."""
        app = await self._get_primary_app()
        if direction == AXDirection.Next:
            element = await type(app).first_element(app)
            elements_list = await type(app).elements(app)
        elif direction == AXDirection.Previous:
            element = await type(app).last_element(app)
            elements_list = reversed(await type(app).elements(app))
        else:
            raise TypeError(f"bad value for: {direction}")

        if displayed_only:
            for element in elements_list:
                if await element.compare_label(label, auto_scroll=False, draw_frame=draw_frame):
                    return element
        else:
            while True:
                if element is None:
                    break

                if await element.compare_label(label, auto_scroll=auto_scroll, draw_frame=draw_frame):
                    if draw_frame:
                        await self.hide_frame()
                    return element

                element = await element.next(direction=direction)

        if draw_frame:
            await self.hide_frame()

        raise ElementNotFoundError(f'failed to find AXElement by label: "{label}"')

    async def press_elements_by_labels(
        self,
        labels: list[str],
        auto_scroll: bool = True,
        draw_frame: bool = True,
        timeout: float = 5,
        direction: AXDirection = AXDirection.Next,
        displayed_only: bool = False,
    ) -> None:
        """
        Press a sequence of labels in order.

        :param labels: Label list to press.
        :param auto_scroll: Scroll to each chosen element.
        :param draw_frame: Draw a frame over the current element.
        :param timeout: Timeout to wait for each element to appear.
        :param direction: Direction to search.
        :param displayed_only: Search only displayed elements.
        """
        for label in labels:
            await (
                await self.wait_for_element_by_label(
                    label,
                    auto_scroll=auto_scroll,
                    draw_frame=draw_frame,
                    timeout=timeout,
                    direction=direction,
                    displayed_only=displayed_only,
                )
            ).press()

            if draw_frame:
                await self.hide_frame()

    def axelement(self, symbol: int) -> AXElement:
        """Wrap a DarwinSymbol as an AXElement."""
        return AXElement(symbol, self._client)
```

#### primary_app

```
primary_app() -> AXElement[DarwinSymbolT_co]
```

Return the primary app AXElement.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def primary_app(self) -> AXElement[DarwinSymbolT_co]:
    """Return the primary app AXElement."""
    return await self._get_primary_app()
```

#### get_enabled

```
get_enabled() -> bool
```

Return True if accessibility automation is enabled.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def get_enabled(self) -> bool:
    """Return True if accessibility automation is enabled."""
    return bool(
        await self._client.symbols._AXSApplicationAccessibilityEnabled()
        or await self._client.symbols._AXSAutomationEnabled()
    )
```

#### set_enabled

```
set_enabled(value: bool) -> None
```

Enable or disable accessibility automation.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def set_enabled(self, value: bool) -> None:
    """Enable or disable accessibility automation."""
    await self._client.symbols._AXSSetAutomationEnabled(int(value))
```

#### hide_frame

```
hide_frame() -> None
```

Hide the accessibility highlight frame.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def hide_frame(self) -> None:
    """Hide the accessibility highlight frame."""
    await self.draw_frame(0, 0, 0, 0)
```

#### set_frame_style

```
set_frame_style(value: int) -> None
```

Set the highlight frame style.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def set_frame_style(self, value: int) -> None:
    """Set the highlight frame style."""
    await (await self._get_ui_client()).objc_call(
        "sendSynchronousMessage:withIdentifier:error:", await self._client.cf({"frameStyle": value}), 2, 0
    )
```

#### draw_frame

```
draw_frame(x: float, y: float, width: float, height: float) -> None
```

Draw a highlight frame at the given coordinates.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def draw_frame(self, x: float, y: float, width: float, height: float) -> None:
    """Draw a highlight frame at the given coordinates."""
    rect = {"frame": f" {{{{{x},{y}}}, {{{width},{height}}}}}"}
    await (await self._get_ui_client()).objc_call(
        "sendSynchronousMessage:withIdentifier:error:", await self._client.cf(rect), 1, 0
    )
```

#### wait_for_element_by_label

```
wait_for_element_by_label(label: str, auto_scroll: bool = True, draw_frame: bool = True, timeout: float = 5, direction: AXDirection = AXDirection.Next, displayed_only: bool = False) -> AXElement
```

Wait for an element with the given label to appear.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def wait_for_element_by_label(
    self,
    label: str,
    auto_scroll: bool = True,
    draw_frame: bool = True,
    timeout: float = 5,
    direction: AXDirection = AXDirection.Next,
    displayed_only: bool = False,
) -> AXElement:
    """Wait for an element with the given label to appear."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            return await self._get_element_by_label(
                label,
                auto_scroll=auto_scroll,
                draw_frame=draw_frame,
                direction=direction,
                displayed_only=displayed_only,
            )
        except ElementNotFoundError:
            pass
        except AttributeError:
            pass
    raise ElementNotFoundError(
        f'failed to find AXElement by label: "{label}" after waiting for {timeout} seconds for it to load'
    )
```

#### press_elements_by_labels

```
press_elements_by_labels(labels: list[str], auto_scroll: bool = True, draw_frame: bool = True, timeout: float = 5, direction: AXDirection = AXDirection.Next, displayed_only: bool = False) -> None
```

Press a sequence of labels in order.

Parameters:

| Name             | Type          | Description                                 | Default    |
| ---------------- | ------------- | ------------------------------------------- | ---------- |
| `labels`         | `list[str]`   | Label list to press.                        | *required* |
| `auto_scroll`    | `bool`        | Scroll to each chosen element.              | `True`     |
| `draw_frame`     | `bool`        | Draw a frame over the current element.      | `True`     |
| `timeout`        | `float`       | Timeout to wait for each element to appear. | `5`        |
| `direction`      | `AXDirection` | Direction to search.                        | `Next`     |
| `displayed_only` | `bool`        | Search only displayed elements.             | `False`    |

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
async def press_elements_by_labels(
    self,
    labels: list[str],
    auto_scroll: bool = True,
    draw_frame: bool = True,
    timeout: float = 5,
    direction: AXDirection = AXDirection.Next,
    displayed_only: bool = False,
) -> None:
    """
    Press a sequence of labels in order.

    :param labels: Label list to press.
    :param auto_scroll: Scroll to each chosen element.
    :param draw_frame: Draw a frame over the current element.
    :param timeout: Timeout to wait for each element to appear.
    :param direction: Direction to search.
    :param displayed_only: Search only displayed elements.
    """
    for label in labels:
        await (
            await self.wait_for_element_by_label(
                label,
                auto_scroll=auto_scroll,
                draw_frame=draw_frame,
                timeout=timeout,
                direction=direction,
                displayed_only=displayed_only,
            )
        ).press()

        if draw_frame:
            await self.hide_frame()
```

#### axelement

```
axelement(symbol: int) -> AXElement
```

Wrap a DarwinSymbol as an AXElement.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/accessibility.py`

```
def axelement(self, symbol: int) -> AXElement:
    """Wrap a DarwinSymbol as an AXElement."""
    return AXElement(symbol, self._client)
```

## Screen capture

## rpcclient.clients.ios.subsystems.screen_capture

### ScreenCapture

Bases: `ClientBound['IosClient[DarwinSymbolT_co]']`, `Generic[DarwinSymbolT_co]`

Screen capture utilities.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/screen_capture.py`

```
class ScreenCapture(ClientBound["IosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """Screen capture utilities."""

    def __init__(self, client: "IosClient[DarwinSymbolT_co]") -> None:
        self._client = client

    async def main_display(self) -> DarwinSymbolT_co:
        """Return the main CADisplay instance."""
        return await (await self._client.symbols.objc_getClass("CADisplay")).objc_call("mainDisplay")

    async def bounds(self) -> CGRect:
        """Return the main display bounds."""
        result = await (await type(self).main_display(self)).objc_call_raw("bounds")
        return CGRect(x0=result.d0, y0=result.d1, x1=result.d2, y1=result.d3)

    async def screenshot(self) -> bytes:
        """Return a PNG screenshot of the current screen."""
        return await (
            await self._client.symbols.UIImagePNGRepresentation(await self._client.symbols._UICreateScreenUIImage())
        ).py(bytes)
```

#### main_display

```
main_display() -> DarwinSymbolT_co
```

Return the main CADisplay instance.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/screen_capture.py`

```
async def main_display(self) -> DarwinSymbolT_co:
    """Return the main CADisplay instance."""
    return await (await self._client.symbols.objc_getClass("CADisplay")).objc_call("mainDisplay")
```

#### bounds

```
bounds() -> CGRect
```

Return the main display bounds.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/screen_capture.py`

```
async def bounds(self) -> CGRect:
    """Return the main display bounds."""
    result = await (await type(self).main_display(self)).objc_call_raw("bounds")
    return CGRect(x0=result.d0, y0=result.d1, x1=result.d2, y1=result.d3)
```

#### screenshot

```
screenshot() -> bytes
```

Return a PNG screenshot of the current screen.

Source code in `src/rpcclient/rpcclient/clients/ios/subsystems/screen_capture.py`

```
async def screenshot(self) -> bytes:
    """Return a PNG screenshot of the current screen."""
    return await (
        await self._client.symbols.UIImagePNGRepresentation(await self._client.symbols._UICreateScreenUIImage())
    ).py(bytes)
```
