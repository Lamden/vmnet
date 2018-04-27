from sanic import Sanic
from sanic.response import raw
import os

app = Sanic()

@app.route('/')
async def test(request):
    return raw(b'ack')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.getenv('DDD_PORT', 31337))
