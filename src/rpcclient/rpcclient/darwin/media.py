import struct
from enum import Enum
from typing import List

from parameter_decorators import path_to_str

from rpcclient.allocated import Allocated
from rpcclient.darwin.consts import AVAudioSessionCategoryOptions, AVAudioSessionRouteSharingPolicy
from rpcclient.darwin.symbol import DarwinSymbol
from rpcclient.exceptions import BadReturnValueError, MissingLibraryError, RpcFailedToPlayError, RpcFailedToRecordError
from rpcclient.structs.consts import RTLD_NOW


class AVAudioSessionCategory(Enum):
    """ https://developer.apple.com/documentation/avfaudio/AVAudioSessionCategory?language=objc """
    PlayAndRecord = 'AVAudioSessionCategoryPlayAndRecord'
    Ambient = 'AVAudioSessionCategoryAmbient'
    MultiRoute = 'AVAudioSessionCategoryMultiRoute'
    Playback = 'AVAudioSessionCategoryPlayback'
    Record = 'AVAudioSessionCategoryRecord'
    SoloAmbient = 'AVAudioSessionCategorySoloAmbient'
    AudioProcessing = 'AVAudioSessionCategoryAudioProcessing'


class AVAudioSessionMode(Enum):
    """ https://developer.apple.com/documentation/avfaudio/avaudiosessionmode?language=objc """
    Default = 'AVAudioSessionModeDefault'
    GameChat = 'AVAudioSessionModeGameChat'
    Measurement = 'AVAudioSessionModeMeasurement'
    MoviePlayback = 'AVAudioSessionModeMoviePlayback'
    SpokenAudio = 'AVAudioSessionModeSpokenAudio'
    VideoChat = 'AVAudioSessionModeVideoChat'
    VideoRecording = 'AVAudioSessionModeVideoRecording'
    VoiceChat = 'AVAudioSessionModeVoiceChat'
    VoicePrompt = 'AVAudioSessionModeVoicePrompt'


class Recorder(Allocated):
    """
    Wrapper for AVAudioRecorder
    https://developer.apple.com/documentation/avfaudio/avaudiorecorder?language=objc
    """

    def __init__(self, client, session: 'AudioSession', recorder: DarwinSymbol):
        super().__init__()
        self._client = client
        self._session = session
        self._recorder = recorder

    def _deallocate(self):
        self._recorder.objc_call('release')

    def record(self):
        self._session.set_category(AVAudioSessionCategory.PlayAndRecord)
        self._session.set_active(True)
        self._recorder.objc_call('record')
        if not self.recording:
            raise RpcFailedToRecordError()

    def pause(self):
        self._recorder.objc_call('pause')
        self._session.set_active(False)

    def stop(self):
        self._recorder.objc_call('stop')
        self._session.set_active(False)

    def delete_recording(self):
        if not self._recorder.objc_call('deleteRecording'):
            raise BadReturnValueError('deleteRecording failed')

    @property
    def recording(self) -> bool:
        return bool(self._recorder.objc_call('isRecording'))


class Player(Allocated):
    """
    Wrapper for AVAudioPlayer
    https://developer.apple.com/documentation/avfaudio/avaudioplayer?language=objc
    """

    def __init__(self, client, session: 'AudioSession', player: DarwinSymbol):
        super().__init__()
        self._client = client
        self._session = session
        self._player = player

    def _deallocate(self):
        self._player.objc_call('release')

    def play(self):
        self._session.set_category(AVAudioSessionCategory.PlayAndRecord)
        self._session.set_active(True)
        self._player.objc_call('play')
        if not self.playing:
            raise RpcFailedToPlayError()

    def pause(self):
        self._player.objc_call('pause')

    def stop(self):
        self._player.objc_call('stop')
        self._session.set_active(False)

    def set_volume(self, value: float):
        self._player.objc_call('setVolume:', struct.pack('<f', value))

    @property
    def playing(self) -> bool:
        return bool(self._player.objc_call('isPlaying'))

    @property
    def loops(self) -> int:
        return self._player.objc_call('numberOfLoops')

    @loops.setter
    def loops(self, value: int):
        self._player.objc_call('setNumberOfLoops:', value)


class AudioSession:
    """
    wrapper for AVAudioSession
    https://developer.apple.com/documentation/avfaudio/avaudiosession?language=objc
    """

    def __init__(self, client):
        self._client = client
        self._session = self._client.symbols.objc_getClass('AVAudioSession').objc_call('sharedInstance')

    def set_active(self, is_active: bool):
        self._session.objc_call('setActive:error:', is_active, 0)

    def set_mode(self, mode: AVAudioSessionMode):
        mode = self._client.symbols[mode.value][0]
        self._session.objc_call('setMode:error:', mode, 0)

    def set_category(self, category: AVAudioSessionCategory,
                     mode: AVAudioSessionMode = AVAudioSessionMode.Default,
                     route_sharing_policy: AVAudioSessionRouteSharingPolicy = AVAudioSessionRouteSharingPolicy.Default,
                     options: AVAudioSessionCategoryOptions = 0):
        category = self._client.symbols[category.value][0]
        mode = self._client.symbols[mode.value][0]
        self._session.objc_call('setCategory:mode:routeSharingPolicy:options:error:', category, mode,
                                route_sharing_policy, options, 0)
        self._session.objc_call('requestRecordPermission:', self._client.get_dummy_block())

    def override_output_audio_port(self, port: int):
        self._session.objc_call('overrideOutputAudioPort:error:', port, 0)

    @property
    def other_audio_playing(self) -> bool:
        return bool(self._session.objc_call('isOtherAudioPlaying'))

    @property
    def record_permission(self):
        return struct.pack('<I', self._session.objc_call('recordPermission'))[::-1].decode()

    @property
    def available_categories(self) -> List[str]:
        return self._session.objc_call('availableCategories').py()


class DarwinMedia:
    """ Media utils """

    def __init__(self, client):
        """
        :param rpcclient.darwin.client.DarwinClient client:
        """
        self._client = client
        self._load_av_foundation()
        self.session = AudioSession(self._client)

    def _load_av_foundation(self):
        options = [
            # macOS
            '/System/Library/Frameworks/AVFoundation.framework/Versions/A/AVFoundation',
            '/System/Library/Frameworks/AVFAudio.framework/Versions/A/AVFAudio',
            # iOS
            '/System/Library/Frameworks/AVFoundation.framework/AVFoundation'
        ]
        for option in options:
            if self._client.dlopen(option, RTLD_NOW):
                return
        raise MissingLibraryError('failed to load AVFAudio')

    @path_to_str('filename')
    def get_recorder(self, filename: str) -> Recorder:
        url = self._client.symbols.objc_getClass('NSURL').objc_call('fileURLWithPath:', self._client.cf(filename))
        settings = self._client.cf({
            'AVEncoderQualityKey': 100,
            'AVEncoderBitRateKey': 16,
            'AVNumberOfChannelsKey': 1,
            'AVSampleRateKey': 8000.0,
        })
        AVAudioRecorder = self._client.symbols.objc_getClass('AVAudioRecorder')
        recorder = AVAudioRecorder.objc_call('alloc').objc_call('initWithURL:settings:error:', url, settings, 0)

        return Recorder(self._client, self.session, recorder)

    @path_to_str('filename')
    def get_player(self, filename: str) -> Player:
        NSURL = self._client.symbols.objc_getClass('NSURL')
        url = NSURL.objc_call('fileURLWithPath:', self._client.cf(filename))

        AVAudioPlayer = self._client.symbols.objc_getClass('AVAudioPlayer')
        player = AVAudioPlayer.objc_call('alloc').objc_call('initWithContentsOfURL:error:', url, 0)

        return Player(self._client, self.session, player)
