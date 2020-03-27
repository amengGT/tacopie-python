import queue
import threading
import time
import datetime
from functools import partial

from pip._vendor.msgpack.fallback import xrange


class thread_pool:
    def __init__(self, nb_threads):
        self.__workers = []
        self.__max_nb_threads = 0
        self.__nb_running_threads = 0
        self.__should_stop = False
        self.__tasks = queue.Queue()
        self.__tasks_condvar = threading.Condition(threading.Lock())

        self.set_nb_threads(nb_threads)

    def __del__(self):
        # self.stop()
        pass

    def __copy__(self):
        pass

    def __deepcopy__(self, memodict={}):
        pass

    def add_task(self, work):
        self.__tasks_condvar.acquire()
        self.__tasks.put(work, True)
        self.__tasks_condvar.notify()
        self.__tasks_condvar.release()

    def stop(self):
        self.__tasks_condvar.acquire()
        if not self.is_running():
            self.__tasks_condvar.release()
            return
        self.__should_stop = True
        self.__tasks_condvar.notify_all()
        self.__tasks_condvar.release()

        for worker in self.__workers:
            self.add_task(None)
            worker.join()

        self.__workers.clear()

    def is_running(self):
        return not self.__should_stop

    def set_nb_threads(self, nb_threads):
        self.__max_nb_threads = nb_threads

        while self.__nb_running_threads < self.__max_nb_threads:
            self.__nb_running_threads += 1
            worker = threading.Thread(target=self.__run, args=())
            worker.start()
            self.__workers.append(worker)

        if self.__nb_running_threads > self.__max_nb_threads:
            self.__tasks_condvar.acquire()
            self.__tasks_condvar.notify_all()
            self.__tasks_condvar.release()

    def __run(self):
        while True:
            stopped, task = self.__fetch_task_or_stop()
            if stopped:
                return
            try:
                if task:
                    task()
            except Exception as err:
                print("thread_pool::__run exception", err)

    def __fetch_task_or_stop(self):
        with self.__tasks_condvar:
            self.__tasks_condvar.wait_for(lambda: self.__should_stop_f() is True or self.__tasks.empty() is False)

            if self.__should_stop_f():
                self.__nb_running_threads -= 1
                # 修复: 判断是否移除
                if not self.__should_stop: self.__workers.remove(threading.current_thread())
                return [True, None]

            task = self.__tasks.get()
            return [False, task]

    def __should_stop_f(self):
        return self.__should_stop or (self.__nb_running_threads > self.__max_nb_threads)


if __name__ == '__main__':
    # 初始1个线程
    pool = thread_pool(1)

    # 100个任务
    index = 100
    while index:
        index -= 1
        # time.sleep(0.1)
        pool.add_task(partial(print, "hello %d" % index))

    # 设置6个线程
    pool.set_nb_threads(6)

    # 100个任务
    index = 100
    while index:
        index -= 1
        # time.sleep(0.1)
        pool.add_task(partial(print, "hello %d" % index))

    # 设置2个线程
    pool.set_nb_threads(2)

    # 休眠一下
    time.sleep(1)
    pool.stop()
