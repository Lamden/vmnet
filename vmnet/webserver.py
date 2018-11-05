from websocket_server import WebsocketServer
from multiprocessing import Process
from sanic import Sanic
from sanic.response import file
from coloredlogs.converter import convert
from os.path import dirname, abspath, join, splitext, expandvars, realpath, exists
import os, webbrowser, sys, time, json

WEBUI_PORT = 4320
WS_PORT = 4321
STATIC_ROOT = join(dirname(__file__), 'static')

def _start_webserver():
    app = Sanic(__name__)
    app.static('/', STATIC_ROOT)
    app.static('/favicon.ico', join(STATIC_ROOT, 'assets/img/icons/favicon.ico'))
    @app.route('/')
    async def index(request):
        return await file('{}/index.html'.format(STATIC_ROOT))
    app.run(host="0.0.0.0", port=WEBUI_PORT, debug=False, access_log=False)

def _track_logs(test_name, project_path):
    server = WebsocketServer(WS_PORT, host='0.0.0.0')
    def new_client(cli, svr):
        opened_files = {}
        while True:
            for root, dirs, files in os.walk(project_path):
                for f in files:
                    if f.endswith('_color') and test_name in root:
                        if not opened_files.get(f):
                            opened_files[f] = open(join(root, f))
                        log_lines = [convert(l) for l in opened_files[f].readlines()]
                        if log_lines != []:
                            node = splitext(f)[0].split('_')
                            node_num = node[-1] if node[-1].isdigit() else None
                            node_type = node[:-1] if node[-1].isdigit() else node
                            svr.send_message_to_all(json.dumps({
                                'node_type': '_'.join(node_type),
                                'node_num': node_num,
                                'log_lines': log_lines
                            }))
            time.sleep(0.01)
    server.set_fn_new_client(new_client)
    server.run_forever()

def start_ui(test_name, project_path):
    webserver_proc = Process(
        target=_start_webserver)
    webserver_proc.start()
    websocket_proc = Process(
        target=_track_logs,
        args=(test_name, project_path))
    websocket_proc.start()
    webbrowser.open('http://localhost:{}'.format(WEBUI_PORT), new=2, autoraise=True)
    sys.stdout.flush()
    return webserver_proc, websocket_proc
