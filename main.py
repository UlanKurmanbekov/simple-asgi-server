import asyncio
from collections import deque
from http import HTTPStatus

from app import app as fastapi_app


class HTTPConnection:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, app):
        self.reader = reader
        self.writer = writer
        self.app = app
        self.buffer = bytearray()

        self.headers_sent = False
        self.response_status = 200
        self.response_headers = []

        self.content_length = 0
        self.body_bytes_read = 0
        self.request_body_queue = deque()
        self._MAX_HEADER_SIZE = 65536

        self.should_close = False

    def get_scope(self, method: str, path: str, query_string: bytes, headers: dict[bytes, bytes]):
        return {
            'type': 'http',
            'asgi': {'version': '3.0'},
            'method': method,
            'path': path,
            'query_string': query_string,
            'headers': [[k.lower(), v] for k, v in headers.items()],
            'server': self.writer.get_extra_info('sockname'),
            'client': self.writer.get_extra_info('peername'),
            'scheme': 'http',
        }

    def parse_headers(self, headers: bytes) -> tuple[str, str, bytes, dict[bytes, bytes]]:
        parsed_headers = {}
        lines = [line for line in headers.split(b'\r\n') if line]
        if not lines:
            return '', '', b'', {}

        request_line_parts = lines[0].decode().split(' ')

        if len(request_line_parts) >= 2:
            method = request_line_parts[0]
            path = request_line_parts[1]
        else:
            return '', '', b'', {}

        query_string = b''
        if '?' in path:
            path, query_string = path.split('?', 1)
            query_string.encode()

        for line in lines[1:]:
            if b':' in line:
                key, val = line.split(b':', 1)

                parsed_headers[key.strip().lower()] = val.strip()

        return method, path, query_string, parsed_headers

    async def run(self):
        try:
            while True:
                self.headers_sent = False
                self.body_bytes_read = 0
                self.content_length = 0

                while b'\r\n\r\n' not in self.buffer:
                    try:
                        data = await asyncio.wait_for(self.reader.read(4096), timeout=60.0)
                    except asyncio.TimeoutError:
                        self.writer.close()
                        return

                    if not data:
                        return

                    self.buffer.extend(data)

                    if len(self.buffer) > self._MAX_HEADER_SIZE:
                        self.writer.write(b'HTTP/1.1 431 Request Header Fields Too Large\r\n\r\n')
                        await self.writer.drain()
                        return

                index = self.buffer.find(b'\r\n\r\n')
                header_data = bytes(self.buffer[:index])
                self.buffer = self.buffer[index + 4:]

                try:
                    method, path, query_string, headers = self.parse_headers(header_data)
                    cl = headers.get(b'content-length')
                    self.content_length = int(cl.decode()) if cl else 0
                except UnicodeDecodeError:
                    self.writer.write(b'HTTP/1.1 400 Bad Request\r\n\r\n')
                    await self.writer.drain()
                    return

                if headers.get(b'transfer-encoding') == b'chunked':
                    self.writer.write(b'HTTP/1.1 501 Not Implemented\r\n\r\n')
                    await self.writer.drain()
                    self.writer.close()
                    return

                if headers.get(b'connection') == b'close':
                    self.should_close = True
                else:
                    self.should_close = False

                scope = self.get_scope(method, path, query_string, headers)
                await self.app(scope, self.receive, self.send)

                if self.should_close:
                    return
        except Exception as e:
            print(f"Critical error: {e}")
        finally:
            self.writer.close()
            await self.writer.wait_closed()

    async def send(self, message: dict):
        msg_type = message.get('type')

        if msg_type == 'http.response.start':
            self.response_status = message.get('status')
            self.response_headers = message.get('headers')

        elif msg_type == 'http.response.body':
            out_data = bytearray()

            reason = HTTPStatus(self.response_status).phrase
            if not self.headers_sent:
                status_line = f'HTTP/1.1 {self.response_status} {reason}\r\n'.encode()
                out_data.extend(status_line)

                conn_header = b'close' if self.should_close else b'keep-alive'
                self.response_headers.append((b'connection', conn_header))

                for key, value in self.response_headers:
                    out_data.extend(key + b': ' + value + b'\r\n')

                out_data.extend(b'\r\n')
                self.headers_sent = True

            body = message.get('body', b'')
            if body:
                out_data.extend(body)

            if out_data:
                self.writer.write(out_data)
                await self.writer.drain()

    async def receive(self):
        if self.body_bytes_read >= self.content_length:
            return {'type': 'http.request', 'body': b'', 'more_body': False}

        chunk = b''

        if self.buffer:
            read_size = min(len(self.buffer), self.content_length - self.body_bytes_read)
            chunk = self.buffer[:read_size]
            self.buffer = self.buffer[read_size:]
        elif self.body_bytes_read < self.content_length:
            to_read = min(4096, self.content_length - self.body_bytes_read)

            try:
                chunk = await self.reader.read(to_read)
            except ConnectionError:
                chunk = b''

        self.body_bytes_read += len(chunk)

        return {'type': 'http.request', 'body': chunk, 'more_body': self.body_bytes_read < self.content_length}


async def client_wrapper(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    connection = HTTPConnection(reader, writer, fastapi_app)
    await connection.run()


async def main():
    server = await asyncio.start_server(client_wrapper, 'localhost', 8000)
    print("Server running on http://localhost:8000")
    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    asyncio.run(main())
