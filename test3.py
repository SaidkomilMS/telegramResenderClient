from pyrogram import Client, filters


API_ID = 2096979
API_HASH = '2bb5d66a4618e7325a91aab04d22c071'

session = "mynewversion"


app = Client(session, API_ID, API_HASH)


@app.on_message(filters.me)
async def send_my_message(client, message):
    await client.send_message("me", f"{message}")

app.run()
