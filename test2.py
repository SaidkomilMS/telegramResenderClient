import asyncio

async def main():
    st = int(input("Input the time (in seconds): "))
    await asyncio.sleep(st-1)
    print("I has slept {0} seconds".format(st-1))
    await asyncio.sleep(1)
    print(f"And one more second")


asyncio.run(main())
print("New line")
