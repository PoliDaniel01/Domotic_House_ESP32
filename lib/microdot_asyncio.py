import uasyncio as asyncio

class Request:
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.method = None
        self.path = None
        self.headers = {}
        self.form = {}
        self.args = {}

    async def read_form_data(self):
        body = await self.reader.read(-1)
        body = body.decode()
        for pair in body.split('&'):
            if '=' in pair:
                key, value = pair.split('=')
                self.form[key] = value

class Response:
    def __init__(self, body='', status_code=200, headers=None):
        self.body = body
        self.status_code = status_code
        self.headers = headers or {}

    async def start(self, writer):
        await writer.awrite(f"HTTP/1.0 {self.status_code} OK\r\n")
        for k, v in self.headers.items():
            await writer.awrite(f"{k}: {v}\r\n")
        await writer.awrite("Content-Type: text/html\r\n\r\n")
        if isinstance(self.body, str):
            await writer.awrite(self.body)
        elif hasattr(self.body, '__aiter__'):
            async for chunk in self.body:
                await writer.awrite(chunk)

def redirect(location):
    return Response('', 303, headers={'Location': location})

class Microdot:
    def __init__(self):
        self.routes = {}

    def route(self, path):
        def decorator(func):
            self.routes[path] = func
            return func
        return decorator

    async def _handle(self, reader, writer):
        try:
            request_line = await reader.readline()
            if not request_line:
                await writer.aclose()
                return

            parts = request_line.decode().strip().split()
            if len(parts) < 2:
                await writer.aclose()
                return

            req = Request(reader, writer)
            req.method = parts[0]
            full_path = parts[1]

            if '?' in full_path:
                path, query_string = full_path.split('?', 1)
                req.path = path
                req.args = {}
                for pair in query_string.split('&'):
                    if '=' in pair:
                        k, v = pair.split('=', 1)
                        req.args[k] = v
            else:
                req.path = full_path
                req.args = {}

            # Headers (skip parsing for simplicity)
            while True:
                line = await reader.readline()
                if not line or line == b"\r\n":
                    break

            handler = self.routes.get(req.path)
            if handler:
                resp = await handler(req)
                if isinstance(resp, Response):
                    await resp.start(writer)
            else:
                r = Response("404 Not Found", 404)
                await r.start(writer)

        except Exception as e:
            print("Microdot error:", e)
        finally:
            await writer.aclose()

    def run(self, host="0.0.0.0", port=80):
        loop = asyncio.get_event_loop()
        loop.create_task(asyncio.start_server(self._handle, host, port))
