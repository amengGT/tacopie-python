import socket


class self_pipe(object):
    def __init__(self):
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.__socket.bind(('localhost', 0))
        self.__address = self.__socket.getsockname()
        self.__socket.connect(self.__address)
        self.__socket.setblocking(False)
        pass

    def __del__(self):
        self.__socket.close()

    def get_read_fd(self):
        return self.__socket.fileno()

    def get_write_fd(self):
        return self.__socket.fileno()

    def notify(self):
        self.__socket.sendto(bytes('a', 'utf-8'), self.__address)

    def clr_buffer(self):
        self.__socket.recvfrom(1024)


"""""

import select
import time
import threading

notifier = self_pipe()

inputs = [notifier.get_read_fd()]
outputs = []

def io_service():
    while True:
        readable, writable, exceptional = select.select(inputs, outputs, inputs)
        if notifier.get_write_fd() in readable:
            notifier.clr_buffer()
            break


worker = threading.Thread(target=io_service, args=())
worker.start()

time.sleep(3)
notifier.notify()

worker.join()


"""""
