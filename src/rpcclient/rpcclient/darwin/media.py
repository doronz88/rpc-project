import struct

from rpcclient.common import path_to_str
from rpcclient.exceptions import RpcClientException, BadReturnValueError
from rpcclient.darwin.symbol import DarwinSymbol


class Recorder:
    def __init__(self, client, recorder: DarwinSymbol):
        self._client = client
        self._recorder = recorder

    def release(self):
        self._recorder.objc_call('release')

    def record(self):
        self._recorder.objc_call('record')

    def pause(self):
        self._recorder.objc_call('pause')

    def stop(self):
        self._recorder.objc_call('stop')

    def delete_recording(self):
        if not self._recorder.objc_call('deleteRecording'):
            raise BadReturnValueError('deleteRecording failed')

    @property
    def recording(self) -> bool:
        return bool(self._recorder.objc_call('isRecording'))

    def __del__(self):
        try:
            self.release()
        except Exception:  # noqa: E722
            # Best effort.
            pass


class Player:
    def __init__(self, client, player):
        self._client = client
        self._player = player

    def release(self):
        self._player.objc_call('release')

    def play(self):
        self._player.objc_call('play')

    def pause(self):
        self._player.objc_call('pause')

    def stop(self):
        self._player.objc_call('stop')

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

    def __del__(self):
        try:
            self.release()
        except Exception:  # noqa: E722
            # Best effort.
            pass


class DarwinMedia:
    def __init__(self, client):
        """
        :param rpcclient.client.darwin_client.DarwinClient client:
        """
        self._client = client
        self._load_av_foundation()

    def _load_av_foundation(self):
        options = [
            # macOS
            '/System/Library/Frameworks/AVFoundation.framework/Versions/A/AVFoundation',
            '/System/Library/Frameworks/AVFAudio.framework/Versions/A/AVFAudio',
            # iOS
            '/System/Library/Frameworks/AVFoundation.framework/AVFoundation'
        ]
        for option in options:
            if self._client.dlopen(option, 2):
                return
        raise RpcClientException('failed to load AVFAudio')

    def set_audio_session(self):
        AVAudioSession = self._client.symbols.objc_getClass('AVAudioSession')
        audio_session = AVAudioSession.objc_call('sharedInstance')
        audio_session.objc_call('setCategory:error:', self._client.symbols.AVAudioSessionCategoryPlayAndRecord[0], 0)

    @path_to_str('filename')
    def get_recorder(self, filename: str) -> Recorder:
        NSURL = self._client.symbols.objc_getClass('NSURL')
        url = NSURL.objc_call('fileURLWithPath:', self._client.cf(filename))
        settings = self._client.cf({
            self._client.symbols.AVEncoderAudioQualityKey: 100,
            self._client.symbols.AVEncoderBitRateKey: 16,
            self._client.symbols.AVNumberOfChannelsKey: 1,
            self._client.symbols.AVSampleRateKey: 8000.0,
        })

        self.set_audio_session()

        AVAudioRecorder = self._client.symbols.objc_getClass('AVAudioRecorder')
        recorder = AVAudioRecorder.objc_call('alloc').objc_call('initWithURL:settings:error:', url, settings, 0)

        return Recorder(self._client, recorder)

    @path_to_str('filename')
    def get_player(self, filename: str) -> Player:
        NSURL = self._client.symbols.objc_getClass('NSURL')
        url = NSURL.objc_call('fileURLWithPath:', self._client.cf(filename))

        self.set_audio_session()

        AVAudioPlayer = self._client.symbols.objc_getClass('AVAudioPlayer')
        player = AVAudioPlayer.objc_call('alloc').objc_call('initWithContentsOfURL:error:', url, 0)

        return Player(self._client, player)
