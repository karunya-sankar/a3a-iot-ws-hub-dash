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
import psutil as psu
import aiohttp.web as aioweb
from contextlib import suppress


class IngesterAggregator(object):
    """
    This part of the ingestor subscribes to different WebSockets services
        that represent edge nodes, to provide a metaphor for what one would
        do with edge nodes that run on Bluetooth Low Energy.
    """
    def __init__(self) -> None:
        self.period_aggregate_s = 10  # aggregate every 10 s
        pass

    async def node_add(self, node_id: int) -> bool:
        pass

    async def node_remove(self, node_id: int) -> bool:
        pass

    async def get_current_aggregates(self) -> dict:
        pass

    async def run_aggregator(self) -> None:
        pass


class IngesterHTTPService(object):
    def __init__(self, ref_to_aggregator: IngesterAggregator) -> None:
        self.nodes_subscribed = {}
        self.ref_to_aggregator = ref_to_aggregator

    def handle_sub_node(self, request: aioweb.Request) -> aioweb.Response:
        pass

    def handle_unsub_node(self, request: aioweb.Request) -> aioweb.Response:
        pass

    def handle_discover_nodes(self, request: aioweb.Request) -> aioweb.Response:
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
        pass

    async def 


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
