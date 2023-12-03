from rpcclient.darwin.consts import IOHIDDigitizerTransducerType
from rpcclient.client_factory import create_tcp_client

client = create_tcp_client('127.0.0.1', 5910)
args = [1, 2, 3, 4, 5, 6, 7,
        11.5, 12.5, 13.5,14.4, 15.5, 16.5, 17.5,
        8, 9, 10, 11, 12,
        18.5, 19.5, 20.5, 21.5, 22.5]
client.call(0x1234, argv=args, va_list_index=8)
