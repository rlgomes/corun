"""
corun web server example that is also used by some of the tests to do high 
concurrency performance validation.
"""

import socket
import corun
import resource

CANNED_RESPONSE = """HTTP/1.0 200 OK\r
Server: CorunServer\r
Content-Length: 0\r
\n\r\n\r
"""

__SERVER_SOCKET = None
__SERVER_RUNNING = True

def shutdown():
    global __SERVER_SOCKET, __SERVER_RUNNING
    __SERVER_RUNNING = False
    __SERVER_SOCKET.close()
    
def server_client(client):
    yield corun.ReadTask(client)
    client.recv(1024)
        
    yield corun.WriteTask(client)
    client.send(CANNED_RESPONSE)
    
    client.close()
    
def start_server(host,port):
    global __SERVER_SOCKET, __SERVER_RUNNING
    
    rlimit = resource.getrlimit(resource.RLIMIT_NOFILE)
    print("concurrent connection limit is %d" % rlimit[0])
        
    __SERVER_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    __SERVER_SOCKET.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    __SERVER_SOCKET.bind((host, port))
    __SERVER_SOCKET.listen(1024)
        
    print("listening at %s:%d" % (host,port))
    scheduler = corun.Scheduler()
    
    try:
        __SERVER_SOCKET.settimeout(2)
        while __SERVER_RUNNING:
            try:
                client, _ = __SERVER_SOCKET.accept()
                scheduler.new(server_client(client))
            except socket.timeout:
                pass
    finally:
        scheduler.shutdown()
    
if __name__ == "__main__":
    start_server("localhost",9999)
    
