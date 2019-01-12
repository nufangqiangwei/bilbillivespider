# -*- coding: utf-8 -*-

import json
import struct
import sys
from _ssl import SSLError
from asyncio import gather, sleep, CancelledError, _get_running_loop
from collections import namedtuple
from enum import IntEnum
# noinspection PyProtectedMember
from ssl import _create_unverified_context

import aiohttp
import pymongo
import time
import websockets
from websockets.exceptions import ConnectionClosed
from setting import online, ROOM_INIT_URL, WEBSOCKET_URL


class Operation(IntEnum):
    SEND_HEARTBEAT = 2
    POPULARITY = 3
    COMMAND = 5
    AUTH = 7
    RECV_HEARTBEAT = 8


class BLiveClient:
    ROOM_INIT_URL = ROOM_INIT_URL
    WEBSOCKET_URL = WEBSOCKET_URL
    HEADER_STRUCT = struct.Struct('>I2H2I')
    HeaderTuple = namedtuple('HeaderTuple', ('total_len', 'header_len', 'proto_ver', 'operation', 'sequence'))

    def __init__(self, room_id, up_name, ssl=True):
        """
        :param room_id: URL中的房间ID
        :param ssl: True表示用默认的SSLContext验证，False表示不验证，也可以传入SSLContext
        :param loop: 协程事件循环
        """
        self._short_id = room_id
        self.up_name = up_name
        self._room_id = None
        # 未登录
        self._uid = 0

        self._ssl = ssl if ssl else _create_unverified_context()
        self._websocket = None

        self._loop = _get_running_loop()
        self._future = None
        # self.mongo_db = pymongo.MongoClient('locahost')
        self.cli = pymongo.MongoClient().bilbil
        self.coll_name = "{}-{}".format(time.strftime("%Y-%m-%d"), self.up_name)

    def start(self):
        """
        创建相关的协程，不会执行事件循环
        :return: True表示成功创建协程，False表示之前创建的协程未结束
        """
        if self._future is not None:
            return False
        self._future = gather(
            self._message_loop(),
            self._heartbeat_loop(),
            loop=self._loop
        )
        self._future.add_done_callback(self.__on_done)
        try:
            self._loop.run_forever()
        finally:
            self._loop.run_until_complete(self._loop.shutdown_asyncgens())
            self._loop.close()
        return True

    def stop(self):
        """
        取消相关的协程，不会停止事件循环
        """
        if self._future is not None:
            self._future.cancel()

    def __on_done(self, future):
        self._future = None
        self._on_stop(future.exception())

    async def _get_room_id(self):
        try:
            async with aiohttp.ClientSession(loop=self._loop) as session:
                async with session.get(self.ROOM_INIT_URL,
                                       params={'id': self._short_id},
                                       ssl=self._ssl) as res:
                    if res.status == 200:
                        data = await res.json()
                        if data['code'] == 0:
                            self._room_id = data['data']['room_id']
                        else:
                            raise ConnectionAbortedError('获取房间ID失败：' + data['msg'])
                    else:
                        raise ConnectionAbortedError('获取房间ID失败：' + res.reason)
        except Exception as e:
            if not self._handle_error(e):
                self._future.cancel()
                raise

    def _make_packet(self, data, operation):
        body = json.dumps(data).encode('utf-8')
        header = self.HEADER_STRUCT.pack(
            self.HEADER_STRUCT.size + len(body),
            self.HEADER_STRUCT.size,
            1,
            operation,
            1
        )
        return header + body

    async def _send_auth(self):
        auth_params = {
            'uid': self._uid,
            'roomid': self._room_id,
            'protover': 1,
            'platform': 'web',
            'clientver': '1.4.0'
        }
        await self._websocket.send(self._make_packet(auth_params, Operation.AUTH))

    async def _message_loop(self):
        # 获取房间ID
        if self._room_id is None:
            await self._get_room_id()

        while True:
            try:
                # 连接
                async with websockets.connect(self.WEBSOCKET_URL,
                                              ssl=self._ssl,
                                              loop=self._loop) as websocket:
                    self._websocket = websocket
                    await self._send_auth()
                    # print("{}链接成功".format(self.up_name))
                    # 处理消息
                    async for message in websocket:
                        # 可以在这加上一个查看是否退出
                        if online[self.up_name]:
                            await self._handle_message(message)
                        else:
                            break

                    if not online[self.up_name]:
                        del online[self.up_name]
                        break
            except CancelledError:
                break
            except ConnectionClosed:
                self._websocket = None
                # 重连
                # print('{}掉线重连中'.format(self.up_name), file=sys.stderr)
                try:
                    await sleep(5)
                except CancelledError:
                    break
                continue
            except Exception as e:
                if not self._handle_error(e):
                    self._future.cancel()
                    raise
                continue
            finally:
                self._websocket = None

    async def _heartbeat_loop(self):
        while True:
            try:
                if self._websocket is None:
                    await sleep(0.5)
                else:
                    await self._websocket.send(self._make_packet({}, Operation.SEND_HEARTBEAT))
                    await sleep(30)
                if not online.get(self.up_name, None):
                    break
            except CancelledError:
                break
            except ConnectionClosed:
                # 等待重连
                continue
            except Exception as e:
                if not self._handle_error(e):
                    self._future.cancel()
                    raise
                continue

    async def _handle_message(self, message):
        offset = 0
        while offset < len(message):
            try:
                header = self.HeaderTuple(*self.HEADER_STRUCT.unpack_from(message, offset))
            except struct.error:
                break

            if header.operation == Operation.POPULARITY:
                # 收到的人气值
                pass
            elif header.operation == Operation.COMMAND:
                body = message[offset + self.HEADER_STRUCT.size: offset + header.total_len]
                body = json.loads(body.decode('utf-8'))
                await self._handle_command(body)

            elif header.operation == Operation.RECV_HEARTBEAT:
                await self._websocket.send(self._make_packet({}, Operation.SEND_HEARTBEAT))

            else:
                body = message[offset + self.HEADER_STRUCT.size: offset + header.total_len]
                print('{}未知包类型：'.format(self.up_name), header, body, file=sys.stderr)

            offset += header.total_len

    async def _handle_command(self, command):
        if isinstance(command, list):
            for one_command in command:
                await self._handle_command(one_command)
            return

        self.cli['{}'.format(self.coll_name)].insert_one(command)

    def _on_stop(self, exc):
        """
        协程结束后被调用
        :param exc: 如果是异常结束则为异常，否则为None
        """
        self._loop.stop()
        pass

    def _handle_error(self, exc):
        """
        处理异常时被调用
        :param exc: 异常
        :return: True表示异常被处理，False表示异常没被处理
        """
        print(exc, file=sys.stderr)
        if isinstance(exc, SSLError):
            print('SSL验证失败！', file=sys.stderr)
        return False

# clion = BLiveClient(1206, ssl=False)
# clion.start()
