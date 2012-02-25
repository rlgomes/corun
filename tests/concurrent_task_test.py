"""
concurrency test that creates a few thousand concurrent tests that simply 
increment a counter and sleep for a tiny bit of time (to simulate delay).
"""

import time
import threading
import unittest

# allows for more concurrent threads
threading.stack_size(32*1024)

import corun
import gevent

counter = 0

def testfunc():
    global counter
    time.sleep(1)
    counter += 1

def geventfunc():
    global counter
    gevent.sleep(1)
    counter += 1

def coruntestfunc():
    global counter
    yield corun.WaitForTime(1)
    counter += 1

class ConcurrenTaskTest(unittest.TestCase):

    def setUp(self):
        self.iterations = 10000

    def test_thread(self):
        global counter
        counter = 0
        threads = []
        
        start = time.time()
        for _ in range(0, self.iterations):
            thread = threading.Thread(target=testfunc)
            threads.append(thread)
            thread.start()

        for i in range(0, self.iterations):
            threads[i].join()
        elapsed = time.time() - start
        print("\nthread time:\t%f %d" % (elapsed, counter))
        
    def test_corun(self):
        global counter
        counter = 0
        scheduler = corun.Scheduler()
        start = time.time()
        tids = []
        for _ in range(0, self.iterations):
            tids.append(scheduler.new(coruntestfunc()))
        scheduler.joinall(tids)
        scheduler.shutdown()
        elapsed = time.time() - start
        print("\ncorun time:\t%f %d" % (elapsed, counter))
        
    def test_gevent(self):
        global counter
        counter = 0
        jobs = []
        start = time.time()
        for _ in range(0, self.iterations):
            jobs.append(gevent.spawn(geventfunc))
        gevent.joinall(jobs)
        elapsed = time.time() - start
        print("\ngevent time:\t%f %d" % (elapsed, counter))

if __name__ == '__main__':
    unittest.main()
    