from socket import *
import sys

CACHE = dict()

if len(sys.argv) <= 1:
    server_ip = 'localhost'
else:
    server_ip = sys.argv[1]

# Create a server socket, bind it to a port and start listening
tcpSerSock = socket(AF_INET, SOCK_STREAM)

# Fill in start.
Proxy_Port = 8885
tcpSerSock.bind(('', Proxy_Port))
tcpSerSock.listen(5)
print("proxy server is ready to listen in port", Proxy_Port)
# Fill in end.

while 1:
    # Start receiving data from the client
    print('Ready to serve...')
    tcpCliSock, addr = tcpSerSock.accept()  # addr -> address of client
    print('Received a connection from:', addr)
    message = tcpCliSock.recv(1024).decode()  # client request
    print(message)
    if message=="" :
        continue
    # Skip CONNECT requests (HTTPS)
    if message.startswith('CONNECT'):
        print("Skipping HTTPS CONNECT request")
        tcpCliSock.close()
        continue

    # Extract the filename from the given message
    url = message.split()[1]
    print("URL:", url)


    if url.startswith('http://'):

        path = url[7:]
        if '/' in path:
            hostname, filepath = path.split('/', 1)
            filename = filepath if filepath else "index.html"
        else:
            hostname = path
            filename = "index.html"
    else:
        hostname = url.split('/')[0]
        filename = url.partition("/")[2]

    if not filename:
        filename = "index.html"

    print("Hostname:", hostname)
    print("Filename:", filename)
    fileExist = "false"
    filetouse = "/" + filename
    print("File to use:", hostname.replace('.', '_') + ".html")

    if message.split()[0] == "GET" :
        try:
            outputdata = ""
            # Check whether the file exist in the cache
            def read_from_disk(path):
                with open(path, "rb") as f:
                    return f.read()
            if message in CACHE :
                print(CACHE[message])
                outputdata=read_from_disk(CACHE[message])
                print("ooo",outputdata)
            else:
                raise IOError()

            fileExist = "true"

            # ProxyServer finds a cache hit and generates a response message
            tcpCliSock.send("HTTP/1.0 200 OK\r\n".encode())
            tcpCliSock.send("Content-Type:text/html\r\n".encode())
            # Fill in start.

            tcpCliSock.send(outputdata)
            # Fill in end
            print('Read from cache')


        except IOError:
            if fileExist == "false":
                # Create a socket on the proxyserver
                c = socket(AF_INET, SOCK_STREAM)

                try:
                    # Connect to the socket to port 80
                    # Fill in start.
                    print(f"Connecting to {hostname} on port 80")
                    c.connect((hostname, 80))
                    # Fill in end.

                    # Create a temporary file on this socket and ask port 80 for the file requested by the client
                    # Send proper HTTP request
                    request = f"GET /{filename} HTTP/1.1\r\nHost: {hostname}\r\nConnection: close\r\n\r\n"
                    c.send(request.encode())

                    # Read the response into buffer
                    # Fill in start.
                    response = b""
                    while True:
                        data = c.recv(4096)
                        if not data:
                            break
                        response += data
                    # Fill in end.

                    # Create a new file in the cache for the requested file
                    # Also send the response in the buffer to client socket and the corresponding file in the cache
                    cache_path = "./" + hostname.replace('.', '_') + "."+filename
                    tmpFile = open(cache_path, "wb")

                    # Fill in start.
                    # Send response to client
                    print(response)
                    tcpCliSock.send(response)
                    tmpFile.write(response)
                    tmpFile.close()
                    CACHE[message] = cache_path
                    # Fill in end.

                    print(f'Fetched from web and cached: {len(response)} bytes')
                    c.close()

                except Exception as e:
                    print("Illegal request - Error:", e)
                    # Send error response
                    error_msg = "HTTP/1.0 500 Proxy Error\r\n\r\n<html><body><h1>Proxy Failed to Fetch Resource</h1></body></html>"
                    tcpCliSock.send(error_msg.encode())
            else:
                # HTTP response message for file not found
                # Fill in start.
                tcpCliSock.send("HTTP/1.0 404 Not Found\r\n".encode())
                tcpCliSock.send("Content-Type:text/html\r\n\r\n".encode())
                tcpCliSock.send("<html><body><h1>404 Not Found</h1></body></html>".encode())
                # Fill in end.

        # Close the client socket
        tcpCliSock.close()
    else :
        # Split the request into headers and body
        parts = message.split('\r\n\r\n', 1)
        if len(parts) == 2:
            headers_part, body = parts
        else:
            headers_part = message
            body = ""

        # Parse headers into a dictionary
        headers_lines = headers_part.split('\r\n')
        headers = {}
        for line in headers_lines[1:]:  # skip request line like POST /path HTTP/1.1
            if ': ' in line:
                key, value = line.split(': ', 1)
                headers[key.lower()] = value

        # Get content length if present
        content_length = int(headers.get('content-length', 0))

        # If body is shorter than content_length, receive more data from socket
        while len(body) < content_length:
            more = tcpCliSock.recv(1024).decode()
            if not more:
                break
            body += more
        # Print the body on proxy console (optional)
        print("POST body received from client:")
        print(body)

        # Build an HTTP response with the same body
        # response = (
        #     "HTTP/1.1 200 OK\r\n"
        #     "Content-Type: text/plain\r\n"
        #     f"Content-Length: {len(body.encode())}\r\n"
        #     "Connection: close\r\n"
        #     "\r\n"  # End of headers
        #     f"{body}"  # The POST body is sent back
        # )
        c = socket(AF_INET, SOCK_STREAM)
        c.connect((hostname, 80))
        c.send(message.encode())
        data=""
        response = b""
        while True:
            data = c.recv(4096)
            if not data:
                break
            response += data
        print("response from server",response)
        tcpCliSock.send(response)
        tcpCliSock.close()
        c.close()

# tcpSerSock.close()