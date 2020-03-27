import select
import socket
from socket import socket as SOCKET


class tcp_socket(SOCKET):

    def __create_socket_if_necessary(self):
        if self.fileno() != -1: return
        SOCKET.__init__(self, self.family, self.type, self.proto)

    def connect(self, address, timeout=0.0):
        self.__create_socket_if_necessary()

        if timeout > 0:
            self.setblocking(False)
            fd_set = [self.fileno()]

            try:
                SOCKET.connect(self, address)
                return
            except BlockingIOError as ex:
                print('BlockingIOError:', ex.errno)
                readable, writable, exceptional = select.select([], fd_set, [], timeout)
                if self.fileno() != writable:
                    raise TimeoutError('connect() failure')
            except TimeoutError as ex:
                print('TimeoutError:', ex.errno)
                raise ex
            except Exception as ex:
                raise ex
        else:
            SOCKET.connect(self, address)
        pass

"""""
sk = tcp_socket(socket.AF_INET, socket.SOCK_STREAM, 0)
sk.close()

try:
    sk.connect(('192.168.0.100', 100), 1)
    print('')
except Exception as err:
    print(err)

print(sk)

"""""
