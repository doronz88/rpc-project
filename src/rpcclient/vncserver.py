import logging
import threading
import time
from io import BytesIO
from socket import socket, SOL_SOCKET, SO_REUSEADDR

from PIL import Image
from construct import Int32ub, Bytes, Struct, Int8ub, Int16ub, Enum, this, Padding, Switch, Array, GreedyBytes

from rpcclient.darwin.hid import TouchEventType

VERSION = b'RFB 003.003\n'
NO_AUTH = 1

ProtocolVersion = Bytes(12)
Authentication = Int32ub
ClientInitialisation = Struct(
    'shared_flag' / Int8ub,
)
PIXEL_FORMAT = Struct(
    'bits_per_pixel' / Int8ub,
    'depth' / Int8ub,
    'big_endian_flag' / Int8ub,
    'true_colour_flag' / Int8ub,
    'red_max' / Int16ub,
    'green_max' / Int16ub,
    'blue_max' / Int16ub,
    'red_shift' / Int8ub,
    'green_shift' / Int8ub,
    'blue_shift' / Int8ub,
    Padding(3),
)
ServerInitialisation = Struct(
    'framebuffer_width' / Int16ub,
    'framebuffer_height' / Int16ub,
    'server_pixel_format' / PIXEL_FORMAT,
    'name_length' / Int32ub,
    'name_string' / Bytes(this.name_length),
)

EncodingType = Enum(Int32ub,
                    Raw=0,
                    CopyRectangle=1,
                    RRE=2,
                    CoRRE=3,
                    hextile=4,
                    )

ClientMessageType = Enum(Int8ub,
                         SetPixelFormat=0,
                         FixColourMapEntries=1,
                         SetEncodings=2,
                         FramebufferUpdateRequest=3,
                         KeyEvent=4,
                         PointerEvent=5,
                         )

FixColourMapEntries = Struct(
    Padding(1),
    'first_colour' / Int16ub,
    'number_of_colours' / Int16ub,
    'colours' / Array(this.number_of_colours, Bytes(6)),
)

KeyEvent = Struct(
    'down_flag' / Int8ub,
    Padding(2),
    'key' / Int32ub,
)

PointerEvent = Struct(
    'button_mask' / Int8ub,
    'x_position' / Int16ub,
    'y_position' / Int16ub,
)

SetEncodings = Struct(
    Padding(1),
    'number_of_encodings' / Int16ub,
    'encodings' / Array(this.number_of_encodings, EncodingType)
)

SetPixelFormat = Struct(
    Padding(3),
    'pixel_format' / PIXEL_FORMAT,
)

FramebufferUpdateRequest = Struct(
    'incremental' / Int8ub,
    'x_position' / Int16ub,
    'y_position' / Int16ub,
    'width' / Int16ub,
    'height' / Int16ub,
)

ClientMessage = Struct(
    'message_type' / ClientMessageType,
    'body' / Switch(this.message_type, {
        ClientMessageType.SetPixelFormat: SetPixelFormat,
        ClientMessageType.FixColourMapEntries: FixColourMapEntries,
        ClientMessageType.SetEncodings: SetEncodings,
        ClientMessageType.FramebufferUpdateRequest: FramebufferUpdateRequest,
        ClientMessageType.KeyEvent: KeyEvent,
        ClientMessageType.PointerEvent: PointerEvent,
    })
)

ServerMessageType = Enum(Int8ub,
                         FramebufferUpdate=0,
                         )

FramebufferUpdate = Struct(
    Padding(1),
    'number_of_rectangles' / Int16ub,
    'rectangles' / Array(this.number_of_rectangles, Struct(
        'x_position' / Int16ub,
        'y_position' / Int16ub,
        'width' / Int16ub,
        'height' / Int16ub,
        'encoding_type' / EncodingType,
        'data' / Switch(this.encoding_type, {
            EncodingType.Raw: GreedyBytes,
        })
    ))
)

ServerMessage = Struct(
    'message_type' / ServerMessageType,
    'body' / Switch(this.message_type, {
        ServerMessageType.FramebufferUpdate: FramebufferUpdate,
    })
)


class ClientThread(threading.Thread):
    def __init__(self, rpc_client, client, width, height, refresh_rate=.1):
        super().__init__()
        self._rpc_client = rpc_client
        self._client = client
        self._width = width
        self._height = height
        self._refresh_rate = refresh_rate
        self._last_screenshot = 0

    def recvall(self, size: int):
        buf = b''
        while len(buf) < size:
            chunk = size - len(buf)
            if not chunk:
                raise Exception('disconnect')
            buf += self._client.recv(chunk)
        return buf

    @property
    def screenshot(self):
        image_bytes = BytesIO(self._rpc_client.screen_capture.get_screenshot(size=(self._width, self._height)))
        image = Image.open(image_bytes)
        return image.convert('RGBA')

    def _handle_frame_buffer_update_request(self):
        if time.time() - self._last_screenshot < self._refresh_rate:
            return

        image = self.screenshot
        self._client.sendall(ServerMessage.build({
            'message_type': ServerMessageType.FramebufferUpdate,
            'body': {
                'number_of_rectangles': 1,
                'rectangles': [{
                    'x_position': 0,
                    'y_position': 0,
                    'width': image.width,
                    'height': image.height,
                    'encoding_type': EncodingType.Raw,
                    'data': image.tobytes(),
                }],
            }
        }))
        self._last_screenshot = time.time()

    def run(self):
        self._client.sendall(ProtocolVersion.build(VERSION))
        client_protocol_version = self.recvall(ProtocolVersion.sizeof())
        logging.debug(f'ProtocolVersion {client_protocol_version}')

        self._client.sendall(Authentication.build(NO_AUTH))

        client_initialisation = ClientInitialisation.parse(self.recvall(ClientInitialisation.sizeof()))
        logging.debug(f'ClientInitialisation {client_initialisation}')

        self._client.sendall(ServerInitialisation.build({
            'framebuffer_width': int(self._width),
            'framebuffer_height': int(self._height),
            'server_pixel_format': {
                'bits_per_pixel': 32,
                'depth': 24,
                'big_endian_flag': True,
                'true_colour_flag': True,
                'red_max': 255,
                'green_max': 255,
                'blue_max': 255,
                'red_shift': 16,
                'green_shift': 8,
                'blue_shift': 0,
            },
            'name_length': 4,
            'name_string': b'full',
        }))

        while True:
            message = ClientMessage.parse(self._client.recv(1024))
            print(message)
            message_type = message.message_type

            if message_type == ClientMessageType.FramebufferUpdateRequest:
                self._handle_frame_buffer_update_request()

            elif message_type == ClientMessageType.KeyEvent:
                pass

            elif message_type == ClientMessageType.PointerEvent:
                if message.body.button_mask:
                    event = TouchEventType.TOUCH_DOWN
                else:
                    event = TouchEventType.TOUCH_UP
                self._rpc_client.hid.send_touch_event(event, message.body.x_position / self._width,
                                                      message.body.y_position / self._height)

            elif message_type == ClientMessageType.SetEncodings:
                pass

            elif message_type == ClientMessageType.SetPixelFormat:
                pass

            elif message_type == ClientMessageType.FixColourMapEntries:
                pass

            else:
                raise NotImplementedError()


class VNCServer:
    def __init__(self, rpc_client, address='0.0.0.0', port=6767, width: float = 240.0, height: float = 426.0):
        self._rpc_client = rpc_client
        self._address = address
        self._port = port

        self._width = width
        self._height = height

    def start(self):
        server = socket()
        server.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        server.bind((self._address, self._port))
        server.listen(5)
        while True:
            client, _ = server.accept()
            ClientThread(self._rpc_client, client, self._width, self._height).start()
