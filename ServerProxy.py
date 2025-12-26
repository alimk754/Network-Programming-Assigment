from socket import *
import sys
import os

from urllib.parse import urlparse

# Check for server IP argument
if len(sys.argv) <= 1:
    print('Usage : "python proxy.py server_ip"')
    print('[server_ip : The IP Address of the Proxy Server]')
    sys.exit(2)

# Create a server socket
tcpSerSock = socket(AF_INET, SOCK_STREAM)
tcpSerSock.bind((sys.argv[1], 8888))  # Bind to IP and port
tcpSerSock.listen(5)  

print(f"Proxy Server running on {sys.argv[1]}:8888")

while True:
    print('Ready to serve...')
    tcpCliSock, addr = tcpSerSock.accept()
    print('Received a connection from:', addr)

    # Receive client request
    received = tcpCliSock.recv(4096)
    if not received:
        tcpCliSock.close()
        continue
    message = received.decode()

    print("\n--- Client Request ---")
    print(message)

    # Parse the full URL safely
    try:
        url = message.split()[1]
        method = message.split()[0]
    except IndexError:
        tcpCliSock.close()
        continue

    parsed_url = urlparse(url)
    hostn = parsed_url.hostname
    path = parsed_url.path
    if not path:
        path = "/"

    print("Full URL:", url)
    print("Host:", hostn)
    print("Path:", path)

    # Skip invalid hostnames
    if not hostn:
        tcpCliSock.close()
        continue

    # Create cache filename

    scheme = parsed_url.scheme or "http"

    if not hostn:
        # Try to read from Host header
        for line in message.split("\r\n"):
            if line.lower().startswith("host:"):
                hostn = line.split(":", 1)[1].strip().split(":")[0]
                break

    if not hostn:
        tcpCliSock.close()
        continue

    port = parsed_url.port or (443 if scheme == "https" else 80)
    normalized = f"{scheme}_{hostn.lower()}_{port}_{path}"
    cache_filename = normalized.replace("/", "_").replace("?", "_").replace("=", "_").replace("&", "_")
    print(f"Cache key: {cache_filename}")

    fileExist = False

    # Try to serve from cache
    print(cache_filename)
    if os.path.exists(cache_filename):
        print("\t\tCache hit — serving from local cache.")
        with open(cache_filename, "rb") as f:
            outputdata = f.read()
        # tcpCliSock.send(b"HTTP/1.0 200 OK\r\n")
        # tcpCliSock.send(b"Content-Type:text/html\r\n\r\n")
        tcpCliSock.send(outputdata)
        tcpCliSock.close()
        continue

    # Cache miss — fetch from remote
    try:
        print("Cache miss — fetching from remote server.")
        c = socket(AF_INET, SOCK_STREAM)
        c.connect((hostn, 80))

        # Handle POST (read and forward body if present)
        body = b""
        if method == "POST":
            # Find Content-Length
            content_length = 0
            for line in message.split("\r\n"):
                if line.lower().startswith("content-length:"):
                    try:
                        content_length = int(line.split(":")[1].strip())
                    except:
                        content_length = 0
                    break

            # Find where headers end
            header_end = message.find("\r\n\r\n")
            if header_end != -1:
                already = received[header_end + 4:]
                body = already
                remaining = content_length - len(already)
                while remaining > 0:
                    chunk = tcpCliSock.recv(min(4096, remaining))
                    if not chunk:
                        break
                    body += chunk
                    remaining -= len(chunk)
        # Send HTTP request to the real web server

        if method == "POST":
            c.sendall(received.split(b"\r\n\r\n")[0] + b"\r\n\r\n")  # headers
            if body:
                c.sendall(body)
        else:
            request = f"{method} {path} HTTP/1.0\r\nHost: {hostn}\r\n\r\n"
            c.sendall(request.encode())

        # Receive the response
        response = b""
        while True:
            data = c.recv(4096)
            if not data:
                break
            response += data

        # Send back to browser
        tcpCliSock.send(response)

        # Cache it
        if method == "GET":
            with open(cache_filename, "wb") as f:
                f.write(response)

        print(f"Fetched and cached: {cache_filename}")
        c.close()

    except Exception as e:
        print("Illegal request:", e)
        tcpCliSock.send(b"HTTP/1.0 404 Not Found\r\n")
        tcpCliSock.send(b"Content-Type:text/html\r\n\r\n")
        tcpCliSock.send(b"<html><body><h1>404 Not Found</h1></body></html>")

    tcpCliSock.close()