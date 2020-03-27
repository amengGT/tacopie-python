from thread_pool import thread_pool
from self_pipe import self_pipe
from functools import partial
import threading
import select
import socket
import queue
import time


class io_service(object):
    class tracked_socket(object):
        def __init__(self):
            self.rd_callback = None
            self.wr_callback = None
            self.marked_for_untrack = False
            pass

    def __init__(self):
        self.__tracked_sockets = {}
        self.__should_stop = False
        self.__poll_worker = threading.Thread(target=partial(self.__poll), args=())
        self.__callback_workers = thread_pool(1)
        self.__tracked_sockets_mtx = threading.Lock()
        self.__polled_fds = []
        self.__rd_set = []
        self.__wr_set = []
        self.__notifier = self_pipe()
        self.__wait_for_removal_condvar = threading.Condition(self.__tracked_sockets_mtx)

        self.__poll_worker.start()
        pass

    def __del__(self):
        # self.__stop()
        pass

    def set_nb_workers(self, nb_threads):
        self.__callback_workers.set_nb_threads(nb_threads)
        pass

    def track(self, fd, rd_callback=None, wr_callback=None):
        self.__tracked_sockets_mtx.acquire()

        assert self.__tracked_sockets.get(fd) is None
        track_info = self.tracked_socket()
        track_info.rd_callback = rd_callback
        track_info.wr_callback = wr_callback
        track_info.marked_for_untrack = False
        self.__tracked_sockets[fd] = track_info
        self.__notifier.notify()

        self.__tracked_sockets_mtx.release()
        pass

    def set_rd_callback(self, fd, event_callback):
        self.__tracked_sockets_mtx.acquire()

        assert self.__tracked_sockets.get(fd) is not None
        assert event_callback is not None
        track_info = self.__tracked_sockets[fd]
        track_info.rd_callback = event_callback
        self.__notifier.notify();

        self.__tracked_sockets_mtx.release()
        pass

    def set_wr_callback(self, fd, event_callback):
        self.__tracked_sockets_mtx.acquire()

        assert self.__tracked_sockets.get(fd) is not None
        assert event_callback is not None
        track_info = self.__tracked_sockets[fd]
        track_info.wr_callback = event_callback
        self.__notifier.notify()

        self.__tracked_sockets_mtx.release()
        pass

    def untrack(self, fd):
        with self.__tracked_sockets_mtx:
            track_info = self.__tracked_sockets.get(fd)
            if track_info is None: return
            if track_info.rd_callback or track_info.rd_callback:
                track_info.marked_for_untrack = True
            else:
                self.__tracked_sockets.pop(fd)
                self.__wait_for_removal_condvar.notify_all()
            self.__notifier.notify();
        pass

    def wait_for_removal(self, fd):
        self.__tracked_sockets_mtx.acquire()
        self.__wait_for_removal_condvar.wait_for(lambda : self.__tracked_sockets.get(fd) is None)
        self.__tracked_sockets_mtx.release()
        pass

    def stop(self):
        if self.__should_stop:
            return
        self.__should_stop = True
        self.__notifier.notify()
        self.__poll_worker.join()
        self.__callback_workers.stop()
        pass

    def __poll(self):
        print('start poll() worker')
        while not self.__should_stop:
            try:
                self.__init_poll_fds_info()
                readable, writable, exceptional = select.select(self.__rd_set, self.__wr_set, self.__rd_set)
                self.__process_events(readable, writable, exceptional)
            except Exception as err:
                print('__poll exception:', err)
        print('stop poll() worker')
        pass

    def __init_poll_fds_info(self):
        self.__tracked_sockets_mtx.acquire()
        self.__polled_fds.clear()
        self.__rd_set.clear()
        self.__wr_set.clear()

        fd_notify = self.__notifier.get_read_fd()
        self.__rd_set.append(fd_notify)
        self.__polled_fds.append(fd_notify)

        for fd, tracked in self.__tracked_sockets.items():
            should_rd = tracked.rd_callback is not None
            should_wr = tracked.wr_callback is not None
            if should_rd: self.__rd_set.append(fd)
            if should_wr: self.__wr_set.append(fd)

            if should_rd or should_wr or tracked.marked_for_untrack:
                self.__polled_fds.append(fd)

        self.__tracked_sockets_mtx.release()
        pass

    def __process_events(self, readable, writable, exceptional):
        self.__tracked_sockets_mtx.acquire()
        for fd in self.__polled_fds:
            if (fd == self.__notifier.get_read_fd()) and (fd in readable):
                self.__notifier.clr_buffer()
                continue
            tracked_info = self.__tracked_sockets.get(fd)
            if tracked_info is None:
                continue

            if (fd in readable or tracked_info.marked_for_untrack) and tracked_info.rd_callback:
                self.__process_rd_event(fd, tracked_info)

            if (fd in writable or tracked_info.marked_for_untrack) and tracked_info.wr_callback:
                self.__process_wr_event(fd, tracked_info)

            if tracked_info.marked_for_untrack:
                self.__tracked_sockets.pop(fd)
                self.__wait_for_removal_condvar.notify_all()
        self.__tracked_sockets_mtx.release()
        pass

    def __process_rd_event(self, fd, tracked_info):
        rd_callback = tracked_info.rd_callback
        tracked_info.rd_callback = None
        self.__callback_workers.add_task(partial(rd_callback, fd))
        pass

    def __process_wr_event(self, fd, tracked_info):
        wr_callback = tracked_info.wr_callback
        tracked_info.wr_callback = None
        self.__callback_workers.add_task(partial(wr_callback, fd))
        pass



