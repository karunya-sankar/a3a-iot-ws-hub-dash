"""
This server application is meant to be run on the
    local home hub.  It serves as an interface
    between the edge sensor nodes and the homeowner's
    phones or computers.  Normally this hub would 
    make yet another connection to some server on the 
    cloud, but that's just yet another unnecessary 
    layer once you understand the concepts.

This server application has the following routes:

HTTP GET /ingester/discover : discover and list edge sensor nodes (normally it would be a BLE device scan)
HTTP GET /ingester/subscribe/{node_id} : subscribe to a node by node_id (which is just going to be a port)
HTTP GET /ingester/unsubscribe/{node_id} : unsubscribe from a node by node_id

WS GET /hub/dashboard : dashboard the mean values for the characteristics (sensors) of the currently-subscribed nodes

As you can imagine, this means that our server must run a few different tasks simultaneously:
    1) the Ingester HTTP service (services requests for discovery or subscription), which uses aiohttp
    2) the Ingester data aggregation task (which actually ingests data and aggregates data), which is just asyncio
    3) the dashboard WebSockets service (publishes aggregated data to user clients), which uses aiohttp

For more information: https://docs.aiohttp.org/en/stable/web_advanced.html#background-tasks
"""


import asyncio
import itertools as itt
import psutil as psu
import aiohttp.web as aioweb
import aiohttp as aioh
from contextlib import suppress
from typing import Dict, List


class IngesterAggregator(object):
    """
    This part of the ingestor subscribes to different WebSockets services
        that represent edge nodes, to provide a metaphor for what one would
        do with edge nodes that run on Bluetooth Low Energy.
    """
    def __init__(self) -> None:
        self.period_aggregate_s = 10  # aggregate every 10 s
        self.period_data_timeout_s = 0.1  # run something every 0.1 s
        self.count_aggregate_time = self.period_aggregate_s / self.period_data_timeout_s
        self.url_default_path = '/data'
        self.dict_current_ws_connections: Dict[int, aioh.ClientWebSocketResponse] = dict()
        self.dict_current_data_to_aggregate: Dict[int, List[float]] = dict()
        self.dict_current_aggregates: Dict[int, float] = dict()
        self.queue_command = asyncio.Queue(maxsize=1)  # if we keep this 1, adds/removes are synchronous

    async def node_add(self, node_id: int) -> None:
        """
        Public async method to subscribe to a new node.
            Using a command queue prevents potential race conditions.
            You should attempt to use message passing (command queues)
            over direct memory modifications as much as possible to avoid 
            race conditions.
        
        :param node_id: the TCP port of the edge node simulator
        """
        await self.queue_command.put(("add", node_id))

    async def node_remove(self, node_id: int) -> None:
        """
        Public async method to unsubscribe from a node.
            Using a command queue prevents potential race conditions.
            You should attempt to use message passing (command queues)
            over direct memory modifications as much as possible to avoid 
            race conditions.
        
        :param node_id: the TCP port of the edge node simulator
        """
        await self.queue_command.put(("remove", node_id))

    async def nodes_subscribed(self) -> list:
        """
        Public async method to return the current edge nodes subscribed.

        :returns: list of nodes currently subscribed 
        """
        return list(self.dict_current_ws_connections.keys())

    async def get_current_aggregates(self) -> dict:
        """
        Public async method to get the current aggregated data.

        :returns: dictionary with nodes as keys and mean (avg) sensor values as values
        """
        return self.dict_current_aggregates

    async def _node_add(self, node_id: int) -> bool:
        """
        The actual method that gets called by the IngesterAggregator's task.
        NOTE: you should not call this method directly from another task to
                prevent race conditions.
        
        :param node_id: the TCP port of the edge node simulator
        """
        self.dict_current_data_to_aggregate[node_id] = list()
        self.dict_current_ws_connections = await aioh.ClientSession.ws_connect(
            f'http://localhost:{node_id}{self.url_default_path}'
        )
        return node_id in self.dict_current_ws_connections

    async def _node_remove(self, node_id: int) -> bool:
        ws_connection = self.dict_current_ws_connections.pop(node_id, None)
        if ws_connection is not None:
            ws_connection.close()
        self.dict_current_data_to_aggregate.pop(node_id, None)
        self.dict_current_aggregates.pop(node_id, None)
        return node_id in self.dict_current_ws_connections

    async def _run_process_node_data_dict(self, incoming_data: dict) -> None:
        """
        Process incoming WebSocket JSON data from an edge node.

        Assumes data format is:
        {
            "node": node_id,
            "time": UNIX timestamp (seconds since the epoch),
            "sensor_value": value in float,
            "sensor_type": str indicating the sensor type
        }

        :param incoming_data: data published by the websocket
        """
        node_id = int(incoming_data["node"])
        new_val = float(incoming_data["sensor_value"])
        self.dict_current_data_to_aggregate[node_id].append(new_val)

    async def _run_poll_and_process_new_data(self) -> None:
        """
        Polls each currently subscribed edge node for new data.
        """
        for node, node_ws in self.dict_current_ws_connections.values():
            try:
                async with asyncio.timeout(self.period_data_timeout_s):
                    the_data = await node_ws.receive_json()
                await self._run_process_node_data_dict(the_data)
            except TimeoutError:
                continue

    def _aggregate_current_data(self) -> None:
        """
        Performs the mean on the list of sensor values from each edge node.
        """
        for node, node_values in self.dict_current_data_to_aggregate.values():
            self.dict_current_aggregates[node] = sum(node_values) / len(node_values)
        for node in self.dict_current_data_to_aggregate.keys():
            self.dict_current_data_to_aggregate[node].clear()

    async def _process_command_queue(self) -> None:
        """
        Process the command queue to add or remove subscriptions.        
        """
        for command in self.queue_command:
            if command[0] == "add":
                self._node_add(command[1])
            elif command[0] == "remove":
                self._node_remove(command[1])

    async def run_aggregator(self) -> None:
        for the_count in itt.count():
            await self._run_poll_and_process_new_data()
            await self._process_command_queue()
            if the_count % self.count_aggregate_time == 0:
                self._aggregate_current_data()
            else:
                await asyncio.sleep(self.period_data_timeout_s)


class IngesterHTTPService(object):
    def __init__(self, ref_to_aggregator: IngesterAggregator) -> None:
        self.ref_to_aggregator = ref_to_aggregator
        self.periods_to_wait = 5
        self.timeout_s = self.periods_to_wait * self.ref_to_aggregator.period_data_timeout_s

    async def handle_sub_node(self, request: aioweb.Request) -> aioweb.Response:
        node_id = request.match_info.get('node_id')
        await self.ref_to_aggregator.node_add(int(node_id))
        await asyncio.sleep(self.timeout_s)
        nodes_subbed = await self.ref_to_aggregator.nodes_subscribed()
        return aioweb.Response(
            {
                "success": node_id in nodes_subbed,
                "nodes_subscribed": nodes_subbed
            }
        )

    async def handle_unsub_node(self, request: aioweb.Request) -> aioweb.Response:
        node_id = request.match_info.get('node_id')
        await self.ref_to_aggregator.node_remove(int(node_id))
        await asyncio.sleep(self.timeout_s)
        nodes_subbed = await self.ref_to_aggregator.nodes_subscribed()
        return aioweb.Response(
            {
                "success": node_id in nodes_subbed,
                "nodes_subscribed": nodes_subbed
            }
        )

    async def handle_discover_nodes(self, request: aioweb.Request) -> aioweb.Response:
        """
        Run the edge node discovery and return dict with discovered nodes as keys  
            and values of whether the nodes are already subscribed (True) or not.

        NOTE: Assume that local ports 8090-9000 are edge nodes.
        """
        discovered_nodes = [x.laddr.port for x in psu.net_connections(kind='inet') 
                            if 8090 < x.laddr.port < 9000 and x.status=='LISTEN']
        resp_nodes = {node: node in self.nodes_subscribed for node in discovered_nodes}
        return aioweb.json_response(resp_nodes)


class DashboardWSService(object):
    def __init__(self, ref_to_ingester_agg: IngesterAggregator) -> None:
        self.period_pub_s = 5
        self.period_refresh_s = 0.5
        self.count_pub = self.period_pub_s / self.period_refresh_s
        self.ref_to_ingester_agg = ref_to_ingester_agg

    async def handle_wss_data_stream(self, request: aioweb.Request) -> aioweb.WebSocketResponse:
        """
        Handler that infinitely runs until the websocket is closed from the client.
            Will continue sending data at the 
        """
        ws_resp = aioweb.WebSocketResponse()
        await ws_resp.prepare(request)
        for the_count in itt.count():
            async for msg in ws_resp:
                if msg.data == 'close':
                    await ws_resp.close()
                elif msg.type == aioh.WSMsgType.ERROR:
                    print(f'WebSocket connection closed with exception {ws_resp.exception()}')
            if the_count % self.count_pub == 0:
                current_data = self.ref_to_ingester_agg.get_current_aggregates()
                await ws_resp.send_json(current_data)
            else:
                await asyncio.sleep(self.period_refresh_s)
        return ws_resp


class HomeHubApp(object):
    def __init__(self) -> None:
        self.the_ingester_agg = IngesterAggregator()
        self.the_ingester_http = IngesterHTTPService(self.the_ingester_agg)
        self.the_dashboard_wss = DashboardWSService()
        self.task_ingester_agg = None

    async def run_non_aiohttp_tasks(self, aiohttp_app: aioweb.Application) -> None:
        self.task_ingester_agg = asyncio.create_task(self.the_ingester_agg.run_aggregator())
        yield
        self.task_ingester_agg.cancel()
        with suppress(asyncio.CancelledError):
            await self.task_ingester_agg


if __name__ == '__main__':
    """
    Using asyncio, our Home Hub Server will be concurrently multitasked, 
        but still runs on one process.
    """
    the_app = HomeHubApp()
    app = aioweb.Application()
    app.cleanup_ctx.append(the_app.run_non_aiohttp_tasks)
    aioweb.run_app(app)
