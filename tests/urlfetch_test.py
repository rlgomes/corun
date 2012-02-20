"""
performance test that hits a webserver with concurrent GET requests. 

this test shows that the corun library can out perform the traditional threaded
solution as well as even beat out the gevent solution by a small margine. 

i had to place a sequence number in the test method name in order to gaurantee
the order of execution because otherwise the gevent.monkey patching would mess
up the socket libraries for the other threaded and corun tests.
"""

import time
import threading
import socket 
import unittest

import corun_server

# allows for more concurrent threads and gives the threaded model a chance to 
# compete ;)
threading.stack_size(32*1024)

import corun

global counter 
counter = 0

iterations = 1000
host = "localhost"
port = 9999

HTTP_GET = """GET / HTTP/1.0\r
Host: localhost:80\r\n\r\n"""

def fetch(host,port):
    global counter
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    
    sent = 0
    while sent < len(HTTP_GET):
        sent += sock.send(HTTP_GET[sent:])
        
    read = True
    while read:
        read = sock.recv(1024)
    
    counter += 1

def geventfetch(host,port):
    global counter
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    
    sent = 0
    while sent < len(HTTP_GET):
        sent += sock.send(HTTP_GET[sent:])
    
    read = True
    while read:
        read = sock.recv(1024)
    
    counter += 1
    
def coruntestfetch(host, port):
    global counter
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
        
    sent = 0
    while sent < len(HTTP_GET):
        yield corun.WriteTask(sock)
        sent += sock.send(HTTP_GET[sent:])

    read = True
    while read:
        yield corun.ReadTask(sock)
        read = sock.recv(1024)
    
    counter += 1
        
class URLFetchTest(unittest.TestCase):
    
    @classmethod
    def setUpClass(self):
        self.server = threading.Thread(target=start_web_server,args=(host,port))
        self.server.start()
        print("Starting tests in 3 seconds...")
        time.sleep(3)
        
    @classmethod
    def tearDownClass(self):
        corun_server.shutdown()
        self.server.join()
 
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
            
    def test_3_gevent(self):
        global counter
        import gevent
        import gevent.monkey as monkey
        monkey.patch_socket()
        
        counter = 0
        jobs = []
        start = time.time()
        for _ in range(0,iterations):
            jobs.append(gevent.spawn(geventfetch, host, port))
        gevent.joinall(jobs)
        elapsed = time.time() - start
            
        print("\ngevent time:\t%f %d" % (elapsed, counter))

def start_web_server(host, port):
    corun_server.start_server(host, port)
            
if __name__ == '__main__':
    unittest.main()
    
    