# Custom HTTP/1.1 ASGI Server

A simple HTTP/1.1 server implementation that supports the ASGI interface.

> **Note:** This is an educational project created to understand HTTP/1.1 protocol and ASGI interface internals. Not intended for production use.

## Features

- HTTP/1.1 protocol support
- Persistent connections (keep-alive)
- Request header parsing
- Request body handling with Content-Length
- ASGI 3.0 interface
- Connection timeouts (60 seconds)

## Requirements

- Python 3.11+
- FastAPI (or any ASGI application)

## Installation
```bash
git clone https://github.com/UlanKurmanbekov/simple-asgi-server.git
cd simple-asgi-server
pip install fastapi
```

## Usage
```bash
python main.py
```

Server runs on `http://localhost:8000`

## Limitations

- No chunked transfer encoding support
- No HTTPS support
- Single-threaded async execution
- Maximum header size: 64KB

## Example Application

The repository includes a simple FastAPI application with basic CRUD operations.
