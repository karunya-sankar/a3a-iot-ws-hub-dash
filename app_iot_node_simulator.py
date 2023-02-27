"""
IoT Edge Node Simulator
Copyright 2023 by Y. Curtis Wang

This application simulates a set of IoT edge nodes by creating WebSockets servers that
produce randomized data.

"""

import asyncio
import time
import random
import itertools as itt
import psutil as psu
import aiohttp.web as aioweb
import aiohttp as aioh
from typing import Dict, List


class IoTNode(object):
    """
    A basic class that pretends to be an IoT edge node by acting as a WebSockets server.
    Spits out random data.
    """
    def __init__(self, node_id: int) -> None:
        self.app = None
        self.node_id = node_id
        self.period_pub_data_s = 1.0
        self.period_refresh_s = 0.01
        self.count_pub = self.period_pub_data_s / self.period_refresh_s

    async def process_ws_messages(self, ws_resp: aioweb.WebSocketResponse) -> None:
        """ Process WebSockets messages (if any) """
        msg = await ws_resp.receive()
        if msg.data == 'close':
            await ws_resp.close()
        elif msg.type == aioh.WSMsgType.ERROR:
            print(f'WebSocket connection closed with exception {ws_resp.exception()}')

    async def generate_random_data(self) -> dict:
        """Generate random data in the correct dictionary format."""
        return {
            "node": self.node_id,
            "time": time.time(),
            "sensor_value": random.uniform(12., 30.),
            "sensor_type": "temperature[degC]"
        }

    async def handle_wss_data_stream(self, request: aioweb.Request) -> aioweb.WebSocketResponse:
        """
        Handler that infinitely runs until the websocket is closed from the client.
            Will continue sending data at the rate determined by self.period_pub_s.
        """
        ws_resp = aioweb.WebSocketResponse()
        await ws_resp.prepare(request)
        for the_count in itt.count():  # infinite loop with counter
            try:
                async with asyncio.timeout(self.period_refresh_s):
                    await self.process_ws_messages(ws_resp)
            except RuntimeError:
                await ws_resp.close()
                return ws_resp
            except TimeoutError:
                pass

            if the_count % self.count_pub == 0:
                try:
                    current_data = await self.generate_random_data()
                    await ws_resp.send_json(current_data)
                except ConnectionResetError:
                    continue
            else:
                await asyncio.sleep(self.period_refresh_s)

    def create_aiohttp_app(self) -> None:
        self.app = aioweb.Application()
        self.app.add_routes(
            [
                aioweb.get('/data', self.handle_wss_data_stream),
            ]
        )
        return self.app


async def main() -> None:
    port_starting = 8090
    nodes_to_simulate = 10
    port_range = range(port_starting, port_starting + nodes_to_simulate)
    nodes = [IoTNode(node_id) for node_id in port_range]

    runners = [aioweb.AppRunner(node.create_aiohttp_app()) for node in nodes]
    for runner in runners:
        await runner.setup()

    sites = list()
    for runner, node_id in zip(runners, port_range):
        this_site = aioweb.TCPSite(runner, 'localhost', node_id)
        print(f"Starting IoT Edge Node on port {node_id} serving /data")
        sites.append(this_site)
        await this_site.start()

    print("Mash CTRL+C a few times to quit this server.")
    print("Don't worry about the errors that come up after you quit the server.")

    while True:
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            for runner in runners:
                await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
