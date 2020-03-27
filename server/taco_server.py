import sys
sys.path.append('../tacopie/')

from io_service import io_service
from tcp_server import tcp_server
from tcp_client import tcp_client
from functools import partial
import threading
import socket
import time


def on_read_result(client, result):
    # 读取结果
    print('on_read_result', client, result.success, result.buffer)

    # 投递写请求
    request = tcp_client.write_request()
    request.buffer = result.buffer
    request.async_write_callback = partial(on_write_result, client)
    client.async_write(request)
    client.async_write(request)


def on_write_result(client, result):
    # 写入结果
    print('on_write_result', client, result.success, result.size)

    # 关闭连接
    client.disconnect(True)
    pass


def on_new_client(client):
    # print('new client', client)
    client.set_on_disconnection_handler(partial(on_disconnect, client))

    # 投递读请求
    request = tcp_client.read_request()
    request.size = 1024
    request.async_read_callback = partial(on_read_result, client)
    client.async_read(request)
    return True


def on_disconnect(client, err):
    # 关闭结果
    print('on_disconnect', client, err)
    pass


if __name__ == '__main__':
    g_io = io_service()
    g_io.set_nb_workers(3)
    mascot = tcp_server(g_io)
    mascot.start('127.0.0.1', 9527, partial(on_new_client))

    while 'quit' != input():
        pass

    # 停止服务
    mascot.stop()
    g_io.stop()