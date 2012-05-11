"""
performance test that hits a webserver with concurrent GET requests.

this test shows that the corun library can out perform the traditional threaded
solution.

"""

import time
import threading
import unittest

# allows for more concurrent threads and gives the threaded model a chance to
# compete ;)
threading.stack_size(128*1024)

import corun
import socket

CANNED_RESPONSE = bytes("""HTTP/1.0 200 OK\r
Server: CorunServer\r
Content-Length: 0\r \n\r\n\r
""",'utf8')

__SERVER_SOCKET = None
__SERVER_RUNNING = True
__SCHEDULER = None

def shutdown():
    global __SERVER_SOCKET, __SERVER_RUNNING
    __SERVER_RUNNING = False
    __SCHEDULER.shutdown()

def server_client(client):
    yield corun.ReadTask(client)
    client.recv(1024)

    yield corun.WriteTask(client)
    client.send(CANNED_RESPONSE)

    client.close()

def server_task(host,port):
    global __SERVER_SOCKET, __SERVER_RUNNING

    __SERVER_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    __SERVER_SOCKET.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    __SERVER_SOCKET.bind((host, port))
    __SERVER_SOCKET.listen(1024)

    print("listening at %s:%d" % (host,port))

    __SERVER_SOCKET.settimeout(2)
    socket_timeout = socket.timeout
    while __SERVER_RUNNING:
        try:
            yield corun.ReadTask(__SERVER_SOCKET)
            client, _ = __SERVER_SOCKET.accept()
            __SCHEDULER.new(server_client(client))
        except socket_timeout:
            pass

def start_server(host,port):
    global __SCHEDULER
    __SCHEDULER = corun.Scheduler()
    __SCHEDULER.new(server_task(host,port))

global counter
counter = 0

iterations = 2000
host = "localhost"
port = 9999

HTTP_GET = bytes("""GET / HTTP/1.0\r
Host: localhost:80\r\n\r\n""",'utf8')

def fetch(host,port):
    global counter
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))

    try:
        sent = 0
        while sent < len(HTTP_GET):
            sent += sock.send(HTTP_GET[sent:])

        read = True
        while read:
            read = sock.recv(1024)
    finally:
        sock.close()

    counter += 1

def coruntestfetch(host, port):
    global counter
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))

    try:
        sent = 0
        while sent < len(HTTP_GET):
            yield corun.WriteTask(sock)
            sent += sock.send(HTTP_GET[sent:])

        read = True
        while read:
            yield corun.ReadTask(sock)
            read = sock.recv(1024)
    finally:
        sock.close()

    counter += 1

class URLFetchTest(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        start_server(host, port)
        print("Starting tests in 2 seconds...")
        time.sleep(2)

    @classmethod
    def tearDownClass(self):
        shutdown()

    def test_1_thread(self):
        global counter
        counter = 0
        threads = []

        start = time.time()
        for _ in range(0,iterations):
            thread = threading.Thread(target=fetch, args=(host, port))
            threads.append(thread)
            thread.start()

        for i in range(0,iterations):
            threads[i].join()
        elapsed = time.time() - start

        print("\nthread time:\t%f %d" % (elapsed, counter))

    def test_2_corun(self):
        global counter
        counter = 0
        scheduler = corun.Scheduler()
        start = time.time()
        tasks = []
        for _ in range(0,iterations):
            tasks.append(scheduler.new(coruntestfetch(host, port)))
        scheduler.joinall(tasks)
        scheduler.shutdown()
        elapsed = time.time() - start

        print("\ncorun time:\t%f %d" % (elapsed, counter))

if __name__ == '__main__':
    unittest.main()

