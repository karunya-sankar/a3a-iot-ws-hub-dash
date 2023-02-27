import asyncio
import aioconsole

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


async def print_dings():
    while True:
        print("ding!")
        await asyncio.sleep(2)


async def reflect_text():
    while True:
        user_input = await async_input("Enter something: >> ")
        print(f">> You entered: {user_input}")


async def main():
    async with asyncio.TaskGroup() as tg:
        task_dings = tg.create_task(print_dings())
        task_reflect = tg.create_task(reflect_text())
    print("Exiting...")


if __name__ == '__main__':
    asyncio.run(main())
