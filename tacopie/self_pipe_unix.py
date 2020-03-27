
from multiprocessing import Process, Pipe, Lock
import select
import threading


class self_pipe:
    def __init__(self):
        self.__fd_read, self.__fd_send = Pipe()
        pass

    def __del__(self):
        self.__fd_read.close()
        self.__fd_send.close()

    def get_read_fd(self):
        return self.__fd_read.fileno()

    def get_write_fd(self):
        return self.__fd_send.fileno()

    def notify(self):
        self.__fd_send.send('a')
        pass

    def clr_buffer(self):
        data = self.__fd_read.recv()
        # print(data)
        pass


"""""
pipe = self_pipe()
pipe.notify()
pipe.clr_buffer()
"""""


