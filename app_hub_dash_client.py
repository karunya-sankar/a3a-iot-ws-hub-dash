
import asyncio
import aioconsole
import aiohttp as ah

async def async_input(prompt: str) -> str:
    """
    Async version of the built-in input() function.

    NOTE: if you print while this function is being run, 
            whatever you print will still be displayed on 
            the screen, which can be disturbing to the user.

    :param prompt: the prompt to present
    :returns: the string from the user
    """
    return await aioconsole.ainput(prompt)


class AppHubDashClient(object):
    """
    This class implements an example client for the HVAC Simulator 
        Home Hub.  There are two tasks that should be scheduled to
        run: one is the WebSockets data processor, and the other
        is the actual command processorfor the user.
    """
    def __init__(self) -> None:
        self.server = "http://localhost:8080"
        self.dict_routes = {
            "discover": "/ingester/discover",
            "list_subbed": "/ingester/subscribed",
            "prefix_sub": "/ingester/subscribe/",
            "prefix_unsub": "/ingester/unsubscribe/",
            "ws_dash": "/hub/dashboard"
        }
        self.period_data_timeout_s = 0.25  # 250 ms refresh time

    async def task_websockets(self) -> None:
        """
        Task coroutine to process websockets data from dashboard server.
        """
        ws_url = self.server + self.dict_routes["ws_dash"]
        async with ah.ClientSession() as session:
            async with session.ws_connect(ws_url) as ws_serv:
                while ws_serv.closed is False:
                    try:
                        async with asyncio.timeout(self.period_data_timeout_s):
                            serv_response = await ws_serv.receive()
                            print(serv_response.data)
                    except TimeoutError:
                        continue

    async def process_user_cmd_discover(self, user_input: str) -> None:
        """
        Coroutine to process discovery command from user.

        :param user_input: the command input by the user.
        """
        if user_input != "discover":
            return
        cmd_url = self.server + self.dict_routes["discover"]
        async with ah.ClientSession() as session:
            async with session.get(cmd_url) as resp:
                print("Nodes discovered are:")
                nodes_discovered = await resp.json()
                for node_id, subbed in nodes_discovered["nodes_found"].items():
                    print(f"Node {node_id}, {'subscribed' if subbed else 'not subscribed'}")

    async def process_user_cmd_list(self, user_input: str) -> None:
        """
        Coroutine to process list command from user.

        :param user_input: the command input by the user.
        """
        if user_input != "list":
            return
        cmd_url = self.server + self.dict_routes["list_subbed"]
        async with ah.ClientSession() as session:
            async with session.get(cmd_url) as resp:
                print("Nodes subscribed are:")
                serv_resp_body = await resp.json()
                print(serv_resp_body["nodes_subscribed"])

    async def process_user_cmd_sub(self, user_input: str) -> None:
        """
        Coroutine to process node subscription command from user.

        :param user_input: the command input by the user.
        """
        if user_input != "sub":
            return
        desired_node = await async_input("Please enter the ID of the node to subscribe to: >> ")
        cmd_url = self.server + self.dict_routes["prefix_sub"] + desired_node
        async with ah.ClientSession() as session:
            async with session.get(cmd_url) as resp:
                serv_resp_body = await resp.json()
                if serv_resp_body["success"]:
                    print(f"Subscription to {desired_node} successful!")
                    print(f"Subscribed to nodes: {serv_resp_body['nodes_subscribed']}")

    async def process_user_cmd_unsub(self, user_input: str) -> None:
        """
        Coroutine to process node unsubscription command from user.

        :param user_input: the command input by the user.
        """
        if user_input != "unsub":
            return
        desired_node = await async_input("Please enter the ID of the node to unsubscribe from: >> ")
        cmd_url = self.server + self.dict_routes["prefix_unsub"] + desired_node
        async with ah.ClientSession() as session:
            async with session.get(cmd_url) as resp:
                serv_resp_body = await resp.json()
                if serv_resp_body["success"]:
                    print(f"Removal of subscription to {desired_node} successful!")
                    print(f"Subscribed to nodes: {serv_resp_body['nodes_subscribed']}")

    async def task_user_interface(self) -> None:
        """
        Task coroutine to process commands from the user.
        """
        print("Welcome to the HVAC IoT System Simulator!")
        print("Available commands are:")
        print("    discover : Look for HVAC sensor nodes")
        print("    list : List currently aggregated HVAC sensor nodes")
        print("    sub : Subscribe to a HVAC sensor node")
        print("    unsub : Unsubscribe from a HVAC sensor node")
        while True:
            user_input = await async_input("Enter a command: >> ")
            await self.process_user_cmd_discover(user_input)
            await self.process_user_cmd_list(user_input)
            await self.process_user_cmd_sub(user_input)
            await self.process_user_cmd_unsub(user_input)


async def main():
    the_client = AppHubDashClient()
    async with asyncio.TaskGroup() as tg:
        task_sockets = tg.create_task(the_client.task_websockets())
        task_commands = tg.create_task(the_client.task_user_interface())
    print("Exiting...")


if __name__ == '__main__':
    asyncio.run(main())
