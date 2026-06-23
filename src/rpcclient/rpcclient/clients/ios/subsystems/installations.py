import contextlib
import os
import plistlib
import tempfile
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generic

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.core._types import ClientBound
from rpcclient.exceptions import BadReturnValueError
from rpcclient.utils import assert_cast


if TYPE_CHECKING:
    from rpcclient.clients.ios.client import IosClient


MOBILE_UID = 501
MOBILE_GID = 501


class Installations(ClientBound["IosClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """iOS application installation helpers.

    This subsystem handles install flows that are not covered by the public
    MobileInstallation APIs exposed elsewhere. The methods operate through the
    connected RPC process and use remote filesystem, Objective-C, and
    LaunchServices calls on the target device.
    """

    def __init__(self, client: "IosClient[DarwinSymbolT_co]") -> None:
        """Bind the subsystem to an iOS client instance."""
        self._client = client

    async def install_ipa(self, local_ipa: str | os.PathLike[str]) -> str:
        """Install an IPA's app bundle.

        The IPA is expanded locally, its `Payload/*.app` bundle is copied to a
        temporary directory on the device, and MobileContainerManager is used to
        create the app and data containers for the bundle identifier found in
        `Info.plist`. The staged app bundle is moved into its final app
        container, ownership and permissions are normalized for the `mobile`
        user, and LaunchServices is asked to register the app dictionary.

        This method assumes the IPA is already signed in a form the target
        device can execute. It does not modify entitlements, signatures,
        provisioning profiles, or embedded binaries.

        :param local_ipa: Local path to the IPA archive.
        :return: Final remote `.app` bundle path on the device.
        :raises RuntimeError: If the IPA has no app bundle, staging fails,
            container creation fails, or LaunchServices registration fails.
        """
        local_ipa = Path(local_ipa).expanduser().resolve()

        # Extract the IPA into a host-side temporary directory. IPA files are ZIP
        # archives and the installable bundle is expected under Payload/*.app.
        with tempfile.TemporaryDirectory(prefix="rpcipa-") as work_dir:
            work = Path(work_dir)
            with zipfile.ZipFile(local_ipa) as z:
                z.extractall(work)

            # Locate the app bundle inside the extracted payload. Only the first
            # bundle is installed, matching the behavior of the original helper.
            payload = work / "Payload"
            apps = list(payload.glob("*.app"))
            if not apps:
                raise ValueError("IPA has no Payload/*.app")

            local_app = apps[0]
            app_name = local_app.name

            # Read the app metadata locally. The bundle identifier drives both
            # MobileContainerManager container creation and LaunchServices
            # registration.
            info = plistlib.loads((local_app / "Info.plist").read_bytes())
            bundle_id = info["CFBundleIdentifier"]

            # Use a per-host-process remote staging directory under /var/tmp so
            # the app can be uploaded before it is moved into its container.
            remote_stage = f"/var/tmp/rpcinstall-{os.getpid()}"
            remote_app_stage = f"{remote_stage}/{app_name}"

            try:
                # Create the remote staging directory and recursively upload the
                # extracted .app bundle into it.
                await self._client.fs.mkdir(remote_stage, parents=True, exist_ok=True)
                await self._client.fs.push(str(local_app), remote_stage, recursive=True, force=True)
                if not await self._client.fs.accessible(remote_app_stage, 0):
                    raise RuntimeError(f"Failed to stage app bundle at {remote_app_stage}")

                # Load the private frameworks that provide container management
                # and LaunchServices registration classes.
                await self._client.load_framework("MobileContainerManager")
                await self._client.load_framework("CoreServices")

                # Resolve the Objective-C classes used for container allocation
                # and app registration.
                MCMAppContainer = await self._client.symbols.objc_getClass("MCMAppContainer")
                MCMAppDataContainer = await self._client.symbols.objc_getClass("MCMAppDataContainer")
                LSApplicationWorkspace = await self._client.symbols.objc_getClass("LSApplicationWorkspace")

                # Create or fetch the application container for this bundle ID.
                # The resulting URL is where the .app bundle should live.
                app_container = await MCMAppContainer.objc_call(
                    "containerWithIdentifier:createIfNecessary:existed:error:",
                    await self._client.cf(bundle_id),
                    True,
                    0,
                    0,
                )
                if not app_container:
                    raise BadReturnValueError("Failed to create MCMAppContainer")

                app_container_dir = assert_cast(
                    str,
                    await (await (await app_container.objc_call("url")).objc_call("path")).py(),
                )
                await self._client.fs.mkdir(app_container_dir, parents=True, exist_ok=True)
                final_app_path = f"{app_container_dir}/{app_name}"

                # Replace any existing app bundle at the target path before the
                # staged bundle is moved into its final location.
                if await self._client.fs.accessible(final_app_path, 0):
                    await self._client.fs.remove(final_app_path, recursive=True, force=True)

                # Move the staged bundle into the app container and normalize
                # ownership and mode bits for iOS user-installed apps.
                await self._client.fs.rename(remote_app_stage, final_app_path)
                await self._client.fs.chown(final_app_path, MOBILE_UID, MOBILE_GID, recursive=True)
                await self._client.fs.chmod(final_app_path, 0o755, recursive=True)

                # Create or fetch the application data container. If this works,
                # the registration dictionary will point HOME and TMPDIR into it.
                data_container = await MCMAppDataContainer.objc_call(
                    "containerWithIdentifier:createIfNecessary:existed:error:",
                    await self._client.cf(bundle_id),
                    True,
                    0,
                    0,
                )

                data_container_dir = ""
                if data_container:
                    data_container_dir = assert_cast(
                        str,
                        await (await (await data_container.objc_call("url")).objc_call("path")).py(),
                    )

                # Build the LaunchServices registration dictionary. These keys
                # describe the user app, its final path, signing metadata, and
                # install state closely enough for LS to make it launchable.
                reg: dict[str, Any] = {
                    "ApplicationType": "User",
                    "CFBundleIdentifier": bundle_id,
                    "CodeInfoIdentifier": bundle_id,
                    "CompatibilityState": 0,
                    "IsContainerized": True,
                    "IsDeletable": True,
                    "Path": final_app_path,
                    "SignerOrganization": "Apple Inc.",
                    "SignatureVersion": 132352,
                    "SignerIdentity": "Apple iPhone OS Application Signing",
                    "IsAdHocSigned": True,
                    "LSInstallType": 1,
                    "HasMIDBasedSINF": False,
                    "MissingSINF": False,
                    "FamilyID": 0,
                    "IsOnDemandInstallCapable": False,
                    "_LSBundlePlugins": {},
                }

                # Include container-specific environment variables when the data
                # container exists, matching what user apps expect at launch.
                if data_container_dir:
                    reg["Container"] = data_container_dir
                    reg["EnvironmentVariables"] = {
                        "CFFIXED_USER_HOME": data_container_dir,
                        "HOME": data_container_dir,
                        "TMPDIR": f"{data_container_dir}/tmp",
                    }

                # Ask LaunchServices to register the app. A false return means
                # the app bundle exists on disk but was not made launchable.
                workspace = await LSApplicationWorkspace.objc_call("defaultWorkspace")
                ok = await workspace.objc_call("registerApplicationDictionary:", await self._client.cf(reg))
                if not ok:
                    raise BadReturnValueError("LaunchServices registration failed")

                return final_app_path
            finally:
                # Always remove the temporary staging directory. Failures during
                # cleanup are suppressed, so the original installation error is kept.
                with contextlib.suppress(Exception):
                    if await self._client.fs.accessible(remote_stage, 0):
                        await self._client.fs.remove(remote_stage, recursive=True, force=True)
