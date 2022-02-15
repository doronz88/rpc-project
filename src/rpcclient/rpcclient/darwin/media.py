import struct

from rpcclient.common import path_to_str
from rpcclient.darwin.consts import AVAudioSessionCategoryOptionDefaultToSpeaker
from rpcclient.exceptions import RpcClientException, BadReturnValueError
from rpcclient.darwin.symbol import DarwinSymbol


class Recorder:
    def __init__(self, client, session, recorder: DarwinSymbol):
        self._client = client
        self._session = session
        self._recorder = recorder

    def release(self):
        self._recorder.objc_call('release')

    def record(self):
        self._session.set_category_play_and_record()
        self._session.set_active(True)
        self._recorder.objc_call('record')

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


class Player:
    def __init__(self, client, session, player):
        self._client = client
        self._session = session
        self._player = player

    def release(self):
        self._player.objc_call('release')

    def play(self):
        self._session.set_category_play_and_record(AVAudioSessionCategoryOptionDefaultToSpeaker)
        self._session.set_active(True)
        self._player.objc_call('play')

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
    def __init__(self, client):
        self._client = client

        AVAudioSession = self._client.symbols.objc_getClass('AVAudioSession')
        self._session = AVAudioSession.objc_call('sharedInstance')

    def set_active(self, is_active: bool):
        self._session.objc_call('setActive:error:', is_active, 0)

    def set_category_play_and_record(self, options=0):
        self._session.objc_call('setCategory:withOptions:error:',
                                self._client.symbols.AVAudioSessionCategoryPlayAndRecord[0], options, 0)
        self._session.objc_call('requestRecordPermission:', self._client.get_dummy_block())

    def override_output_audio_port(self, port: int):
        self._session.objc_call('overrideOutputAudioPort:error:', port, 0)

    @property
    def other_audio_playing(self) -> bool:
        return bool(self._session.objc_call('isOtherAudioPlaying'))

    @property
    def record_permission(self):
        return struct.pack('<I', self._session.objc_call('recordPermission'))[::-1].decode()


class DarwinMedia:
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
            if self._client.dlopen(option, 2):
                return
        raise RpcClientException('failed to load AVFAudio')

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
