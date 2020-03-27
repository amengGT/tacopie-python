from io_service import io_service
from functools import partial
import threading
import select
import socket
import queue


class tcp_client(object):
    class read_result(object):
        def __init__(self):
            self.success = False
            self.buffer = None
        pass

    class write_result(object):
        def __init__(self):
            self.success = False
            self.size = 0
        pass

    class read_request(object):
        def __init__(self):
            self.size = 0
            self.async_read_callback = None

    class write_request(object):
        def __init__(self):
            self.buffer = None
            self.async_write_callback = None
        pass

    def __init__(self, _io, _socket=None):
        assert isinstance(_io, io_service)

        if _socket is None:
            _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            self.__is_connected = False
        else:
            self.__is_connected = True

        self.__io_service = _io
        self.__socket = _socket
        self.__is_shuting = False
        self.__is_sending = False
        self.__is_recving = False
        self.__read_requests = queue.Queue()
        self.__write_requests = queue.Queue()
        self.__requests_mtx = threading.Lock()
        self.__disconnection_handler = None

        self.__io_service.track(self.__socket.fileno())

    def __del__(self):
        pass

    def get_host(self):
        address = self.__socket.getsockname()
        return address[0]

    def get_port(self):
        address = self.__socket.getsockname()
        return address[1]

    def connect(self, host, port, timeout=0):
        if self.__is_connected: raise Exception('tcp_client is already connected')

        try:
            self.__socket.settimeout(timeout)
            self.__socket.connect((host, port))
        except Exception as err:
            self.__socket.close()
            raise err
        self.__is_connected = True

    def disconnect(self, force=False):
        notify = False
        with self.__requests_mtx:
            if force:
                notify = self.__force_close()
            else:
                notify = self.__grace_close()

        if notify:
            self.__call_disconnection_handler(0)

    def is_connected(self):
        with self.__requests_mtx:
            return self.__socket.fileno() != -1

    def __grace_close(self):
        if self.__is_connected == False or self.__is_shuting == True:
            return False

        self.__is_shuting = True

        if self.__is_sending == False and self.__is_recving == True:
            self.__is_connected = False
            self.__io_service.untrack(self.__socket.fileno())
            return False

        if self.__is_sending == False and self.__is_recving == False:
            self.__is_connected = False
            self.__clear_read_requests()
            self.__clear_write_requests()

            self.__io_service.untrack(self.__socket.fileno())
            self.__io_service.wait_for_removal(self.__socket.fileno())
            self.__socket.close()
        return True

    # 强制关闭，不等缓冲区数据发送完成
    def __force_close(self):
        if self.__is_connected:
            self.__is_connected = False
            self.__io_service.untrack(self.__socket.fileno())

        if self.__is_sending == False and self.__is_recving == False:
            self.__is_connected = False
            self.__clear_read_requests()
            self.__clear_write_requests()

            self.__io_service.untrack(self.__socket.fileno())
            self.__io_service.wait_for_removal(self.__socket.fileno())
            self.__socket.close()
            return True
        return False

    def __call_disconnection_handler(self, err):
        if self.__disconnection_handler:
            self.__disconnection_handler(err)

    def async_read(self, request):
        with self.__requests_mtx:
            if self.__is_connected is False or self.__is_shuting is True:
                return
            self.__read_requests.put(request)

            if self.__is_recving:
                return

            self.__io_service.set_rd_callback(self.__socket.fileno(), partial(self.__on_read_available))
            self.__is_recving = True

    def async_write(self, request):
        with self.__requests_mtx:
            if self.__is_connected is False or self.__is_shuting is True:
                return
            self.__write_requests.put(request)

            if self.__is_sending:
                return

            self.__io_service.set_wr_callback(self.__socket.fileno(), partial(self.__on_write_available))
            self.__is_sending = True

    def get_socket(self):
        pass

    def get_io_service(self):
        return self.__io_service

    def set_on_disconnection_handler(self, disconnection_handler):
        self.__disconnection_handler = disconnection_handler

    def __on_read_available(self, fd):
        error = 0
        notify = False
        result = self.read_result()
        callback = None

        with self.__requests_mtx:
            assert self.__is_recving is True
            assert self.__read_requests.empty() is False

            self.__is_recving = False

            if self.__is_connected is False:
                error += 1
                notify = self.__force_close()
            else:
                try:
                    request = self.__read_requests.get()
                    callback = request.async_read_callback

                    data = self.__socket.recv(request.size)
                    if len(data) == 0:
                        raise Exception('nothing to read, socket has been closed by remote host')
                    result.buffer = data
                    result.success = True

                    if self.__is_shuting is True:
                        error += 3
                        notify = self.__force_close()
                    elif self.__read_requests.empty() is False:
                        self.__io_service.set_rd_callback(self.__socket.fileno(), partial(self.__on_read_available))
                        self.__is_recving = True
                except Exception as err:
                    error += 2
                    notify = self.__force_close();
                    result.sucess = False
                    print(err)
        if notify:
            self.__call_disconnection_handler(error)
            return

        if callback:
            callback(result)

    def __on_write_available(self, fd):
        error = 10
        notify = False
        result = self.write_result()
        callback = None

        with self.__requests_mtx:
            assert self.__is_sending is True
            assert self.__write_requests.empty() is False

            self.__is_sending = False

            if self.__is_connected is False:
                error += 1
                notify = self.__force_close()
            else:
                try:
                    request = self.__write_requests.get()
                    callback = request.async_write_callback

                    result.size = self.__socket.send(bytes(request.buffer))
                    result.success = True

                    if self.__write_requests.empty() is False:
                        self.__io_service.set_wr_callback(self.__socket.fileno(), partial(self.__on_write_available))
                        self.__is_sending = True
                    elif self.__is_shuting is True:
                        error += 3
                        notify = self.__force_close()
                except Exception as err:
                    error += 2
                    notify = self.__force_close();
                    result.sucess = False
                    print(err)

        if notify:
            self.__call_disconnection_handler(error)
            return

        if callback:
            callback(result)

    def __clear_read_requests(self):
        self.__read_requests.queue.clear()

    def __clear_write_requests(self):
        self.__write_requests.queue.clear()

    def __process_read(self):
        pass

    def __process_write(self):
        pass



