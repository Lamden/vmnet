from sanic import Sanic
from sanic.response import file
import os

STATIC_ROOT = './nota'

app = Sanic(__name__)
app.static('/', STATIC_ROOT)
app.static('/favicon.ico', os.path.join('{}/asserts/img/icons/favicon.ico'.format(STATIC_ROOT)))

@app.websocket('/stream')
async def stream(request, ws):
    while True:
        data = await ws.recv()
        print('receiving...', data)
        await ws.send(data)

@app.route('/')
async def index(request):
    return await file('./nota/index.html')

if __name__ == '__main__':

    app.run(host="0.0.0.0", port=4321, debug=True)
