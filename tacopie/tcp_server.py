from io_service import io_service
from tcp_client import tcp_client
from functools import partial
import threading
import socket


class tcp_server(object):

    __TACOPIE_CONNECTION_QUEUE_SIZE = 1024

    def __init__(self, _io):
        assert isinstance(_io, io_service)
        self.__io_service = _io
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.__is_running = False
        self.__clients = []
        self.__clients_mtx = threading.Lock()
        self.__on_new_connection_callback = None
        pass

    def __del__(self):
        # self.stop()
        pass

    def start(self, host, port, callback=None):
        self.__socket.bind((host, port))
        self.__socket.listen(self.__TACOPIE_CONNECTION_QUEUE_SIZE)
        self.__io_service.track(self.__socket.fileno())
        self.__io_service.set_rd_callback(self.__socket.fileno(), partial(self.__on_read_available))
        self.__on_new_connection_callback = callback
        pass

    def stop(self, wait_for_removal=False, recursive_wait_for_removal=True):
        if not self.is_running(): return

        self.__is_running = True
        self.__io_service.untrack(self.__socket.fileno())
        if wait_for_removal:
            self.__io_service.wait_for_removal(self.__socket.fileno())

        self.__clients_mtx.acquire()
        ##
        for client in self.__clients:
            client.disconnect(recursive_wait_for_removal and wait_for_removal)
        self.__clients.clear()
        self.__clients_mtx.release()
        pass

    def is_running(self):
        return self.__is_running
        pass

    def get_socket(self):
        pass

    def get_io_service(self):
        return self.__io_service

    def get_clients(self):
        pass

    def __on_read_available(self, fd):
        try:
            sk_info = self.__socket.accept()
            client = tcp_client(self.__io_service, sk_info[0])
            assert client is not None
            if self.__on_new_connection_callback is None or self.__on_new_connection_callback(client) is False:
                client.set_on_disconnection_handler(partial(self.__on_client_disconnected, client))
                with self.__clients_mtx:
                    self.__clients.append(client)
            else:
                # print('connection handled by tcp_server wrapper')
                pass

            self.__io_service.set_rd_callback(self.__socket.fileno(), partial(self.__on_read_available))
        except Exception as err:
            print('__on_read_available err:', err)
            self.stop()
        pass

    def __on_client_disconnected(self, client):
        if self.is_running() is False:
            return
        with self.__clients_mtx:
            if client in self.__clients:
                self.__clients.remove(client)
        pass




