import struct
from enum import Enum
from pathlib import PurePath
from typing import TYPE_CHECKING, Generic
from typing_extensions import Self

import zyncio

from rpcclient.clients.darwin._types import DarwinSymbolT_co
from rpcclient.clients.darwin.consts import AVAudioSessionCategoryOptions, AVAudioSessionRouteSharingPolicy
from rpcclient.core._types import ClientBound
from rpcclient.core.allocated import Allocated
from rpcclient.exceptions import BadReturnValueError, RpcFailedToPlayError, RpcFailedToRecordError
from rpcclient.utils import cached_async_method


if TYPE_CHECKING:
    from rpcclient.clients.darwin.client import BaseDarwinClient


class AVAudioSessionCategory(Enum):
    """https://developer.apple.com/documentation/avfaudio/AVAudioSessionCategory?language=objc"""

    PlayAndRecord = "AVAudioSessionCategoryPlayAndRecord"
    Ambient = "AVAudioSessionCategoryAmbient"
    MultiRoute = "AVAudioSessionCategoryMultiRoute"
    Playback = "AVAudioSessionCategoryPlayback"
    Record = "AVAudioSessionCategoryRecord"
    SoloAmbient = "AVAudioSessionCategorySoloAmbient"
    AudioProcessing = "AVAudioSessionCategoryAudioProcessing"


class AVAudioSessionMode(Enum):
    """https://developer.apple.com/documentation/avfaudio/avaudiosessionmode?language=objc"""

    Default = "AVAudioSessionModeDefault"
    GameChat = "AVAudioSessionModeGameChat"
    Measurement = "AVAudioSessionModeMeasurement"
    MoviePlayback = "AVAudioSessionModeMoviePlayback"
    SpokenAudio = "AVAudioSessionModeSpokenAudio"
    VideoChat = "AVAudioSessionModeVideoChat"
    VideoRecording = "AVAudioSessionModeVideoRecording"
    VoiceChat = "AVAudioSessionModeVoiceChat"
    VoicePrompt = "AVAudioSessionModeVoicePrompt"


class InterruptionPriority(Enum):
    Default = 0
    PhoneCall = 10
    EmergencyAlert = 20


class Recorder(Allocated["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """
    Wrapper for AVAudioRecorder
    https://developer.apple.com/documentation/avfaudio/avaudiorecorder?language=objc
    """

    def __init__(
        self, client: "BaseDarwinClient[DarwinSymbolT_co]", session: "AudioSession", recorder: DarwinSymbolT_co
    ) -> None:
        super().__init__()
        self._client = client
        self._session = session
        self._recorder = recorder

    async def _deallocate(self) -> None:
        await self._recorder.objc_call.z("release")

    @zyncio.zmethod
    async def record(self) -> None:
        await self._session.set_category.z(AVAudioSessionCategory.PlayAndRecord)
        await self._session.set_active.z(True)
        await self._recorder.objc_call.z("record")
        if not await type(self).recording(self):
            raise RpcFailedToRecordError()

    @zyncio.zmethod
    async def pause(self) -> None:
        await self._recorder.objc_call.z("pause")
        await self._session.set_active.z(False)

    @zyncio.zmethod
    async def stop(self) -> None:
        await self._recorder.objc_call.z("stop")
        await self._session.set_active.z(False)

    @zyncio.zmethod
    async def delete_recording(self) -> None:
        if not await self._recorder.objc_call.z("deleteRecording"):
            raise BadReturnValueError("deleteRecording failed")

    @zyncio.zproperty
    async def recording(self) -> bool:
        return bool(await self._recorder.objc_call.z("isRecording"))


class Player(Allocated["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """
    Wrapper for AVAudioPlayer
    https://developer.apple.com/documentation/avfaudio/avaudioplayer?language=objc
    """

    def __init__(
        self,
        client: "BaseDarwinClient[DarwinSymbolT_co]",
        session: "AudioSession[DarwinSymbolT_co]",
        player: DarwinSymbolT_co,
    ) -> None:
        self._client = client
        self._session: AudioSession[DarwinSymbolT_co] = session
        self._player: DarwinSymbolT_co = player

    async def _deallocate(self) -> None:
        await self._player.objc_call.z("release")

    @zyncio.zmethod
    async def play(self) -> None:
        await self._session.set_category.z(AVAudioSessionCategory.PlayAndRecord)
        await self._session.set_active.z(True)
        await self._player.objc_call.z("play")
        if not await type(self).playing(self):
            raise RpcFailedToPlayError()

    @zyncio.zmethod
    async def pause(self) -> None:
        await self._player.objc_call.z("pause")

    @zyncio.zmethod
    async def stop(self) -> None:
        await self._player.objc_call.z("stop")
        await self._session.set_active.z(False)

    @zyncio.zmethod
    async def set_volume(self, value: float) -> None:
        await self._player.objc_call.z("setVolume:", struct.pack("<f", value))

    @zyncio.zproperty
    async def playing(self) -> bool:
        return bool(await self._player.objc_call.z("isPlaying"))

    @zyncio.zproperty
    async def _loops(self) -> int:
        return await self._player.objc_call.z("numberOfLoops")

    @_loops.setter
    async def loops(self, value: int) -> None:
        await self._player.objc_call.z("setNumberOfLoops:", value)


class AudioSession(ClientBound["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """
    wrapper for AVAudioSession
    https://developer.apple.com/documentation/avfaudio/avaudiosession?language=objc
    """

    def __init__(self, client: "BaseDarwinClient[DarwinSymbolT_co]", session: DarwinSymbolT_co) -> None:
        self._client = client
        self._session: DarwinSymbolT_co = session

    @classmethod
    async def create(cls, client: "BaseDarwinClient[DarwinSymbolT_co]") -> Self:
        session = await (await client.symbols.objc_getClass.z("AVAudioSession")).objc_call.z("sharedInstance")
        return cls(client, session)

    @zyncio.zmethod
    async def set_active(self, is_active: bool) -> None:
        await self._session.objc_call.z("setActive:error:", is_active, 0)

    @zyncio.zmethod
    async def set_mode(self, mode: AVAudioSessionMode) -> None:
        await self._session.objc_call.z(
            "setMode:error:",
            await self._client.symbols[mode.value].getindex(0),
            0,
        )

    @zyncio.zmethod
    async def set_category(
        self,
        category: AVAudioSessionCategory,
        mode: AVAudioSessionMode = AVAudioSessionMode.Default,
        route_sharing_policy: AVAudioSessionRouteSharingPolicy = AVAudioSessionRouteSharingPolicy.Default,
        options: AVAudioSessionCategoryOptions = AVAudioSessionCategoryOptions.DefaultToSpeaker,
    ) -> None:
        await self._session.objc_call.z(
            "setCategory:mode:routeSharingPolicy:options:error:",
            await self._client.symbols[category.value].getindex(0),
            await self._client.symbols[mode.value].getindex(0),
            route_sharing_policy,
            options,
            0,
        )

    @zyncio.zmethod
    async def set_interruption_priority(self, priority: InterruptionPriority) -> None:
        await self._session.objc_call.z("setInterruptionPriority:error:", priority, 0)

    @zyncio.zmethod
    async def override_output_audio_port(self, port: int) -> None:
        await self._session.objc_call.z("overrideOutputAudioPort:error:", port, 0)

    @zyncio.zproperty
    async def other_audio_playing(self) -> bool:
        return bool(await self._session.objc_call.z("isOtherAudioPlaying"))

    @zyncio.zproperty
    async def record_permission(self) -> str:
        return struct.pack("<I", await self._session.objc_call.z("recordPermission"))[::-1].decode()

    @zyncio.zproperty
    async def available_categories(self) -> list[str]:
        return await (await self._session.objc_call.z("availableCategories")).py.z(list)

    @zyncio.zproperty
    async def available_modes(self) -> list[str]:
        return await (await self._session.objc_call.z("availableModes")).py.z(list)

    @zyncio.zproperty
    async def is_active(self) -> bool:
        return bool(await self._session.objc_call.z("isActive"))


class DarwinMedia(ClientBound["BaseDarwinClient[DarwinSymbolT_co]"], Generic[DarwinSymbolT_co]):
    """Media utils"""

    def __init__(self, client: "BaseDarwinClient[DarwinSymbolT_co]") -> None:
        """
        :param rpcclient.darwin.client.DarwinClient client:
        """
        self._client = client
        client.load_framework_lazy("AVFoundation")

    @zyncio.zproperty
    @cached_async_method
    async def session(self) -> AudioSession[DarwinSymbolT_co]:
        return await AudioSession.create(self._client)

    @zyncio.zmethod
    async def get_recorder(self, filename: str | PurePath) -> Recorder[DarwinSymbolT_co]:
        url = await (await self._client.symbols.objc_getClass.z("NSURL")).objc_call.z(
            "fileURLWithPath:", await self._client.cf.z(str(filename))
        )
        settings = await self._client.cf.z({
            "AVEncoderQualityKey": 100,
            "AVEncoderBitRateKey": 16,
            "AVNumberOfChannelsKey": 1,
            "AVSampleRateKey": 8000.0,
        })
        AVAudioRecorder = await self._client.symbols.objc_getClass.z("AVAudioRecorder")
        recorder = await (await AVAudioRecorder.objc_call.z("alloc")).objc_call.z(
            "initWithURL:settings:error:", url, settings, 0
        )

        return Recorder(self._client, await type(self).session(self), recorder)

    @zyncio.zmethod
    async def get_player(self, filename: str | PurePath) -> Player[DarwinSymbolT_co]:
        NSURL = await self._client.symbols.objc_getClass.z("NSURL")
        url = await NSURL.objc_call.z("fileURLWithPath:", await self._client.cf.z(str(filename)))

        AVAudioPlayer = await self._client.symbols.objc_getClass.z("AVAudioPlayer")
        player = await (await AVAudioPlayer.objc_call.z("alloc")).objc_call.z("initWithContentsOfURL:error:", url, 0)

        return Player(self._client, await type(self).session(self), player)
