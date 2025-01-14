from quart import Quart
from quart_db import QuartDB

app = Quart(__name__)
QuartDB(app, url="sqlite:///bs.db")


@app.get("/")
async def hello():
    return "Hello World"
