import sys
sys.path.append('../tacopie/')

from io_service import io_service
from tcp_client import tcp_client
from functools import partial
import time


def on_read_result(client, result):
    # 读取结果
    print('on_read_result', client, result.success, result.buffer)

    # 关闭连接
    client.disconnect(True)
    pass


def on_write_result(client, result):
    # 写入结果
    print('on_write_result', client, result.success, result.size)

    # 请求读取
    request = tcp_client.read_request()
    request.size = 1024
    request.async_read_callback = partial(on_read_result, client)
    client.async_read(request)
    pass


def on_disconnect(client, err):
    # 关闭结果
    print('on_disconnect', client, err)
    pass


if __name__ == '__main__':
    g_io = io_service()
    g_io.set_nb_workers(3)
    counter = 100
    while counter:
        counter -= 1
        message = str('hello world %d' % counter)

        client = tcp_client(g_io)
        client.set_on_disconnection_handler(partial(on_disconnect, client))
        client.connect('127.0.0.1', 9527, 10)

        request = tcp_client.write_request()
        request.buffer = bytes(message, 'utf-8')
        request.async_write_callback = partial(on_write_result, client)
        client.async_write(request)

    # 休眠一下
    time.sleep(2)

    # 停止服务
    g_io.stop()
