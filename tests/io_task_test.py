"""
io concurrency test that creates a few thousand concurrent file writes to a few
hundred files.
"""

import time
import threading
import unittest

# allows for more concurrent threads
threading.stack_size(32*1024)

import corun

global counter
counter = 0

DATA = ''.join([ 'X' for _ in range(0,32*1024) ])

def testfunc():
    global counter
    with open("/tmp/somefile-%d" % counter,"w") as output:
        for _ in range(0,100):
            output.write(DATA)
        counter += 1

def coruntestfunc():
    global counter
    with open("/tmp/somefile-%d" % counter,"w") as output:
        for _ in range(0,100):
            yield output.write(DATA)
        counter += 1

class IOTaskTest(unittest.TestCase):

    def setUp(self):
        self.iterations = 500

    def test_thread(self):
        global counter
        counter = 0
        threads = []

        start = time.time()
        for _ in range(0,self.iterations):
            thread = threading.Thread(target=testfunc)
            threads.append(thread)
            thread.start()

        for i in range(0,self.iterations):
            threads[i].join()
        elapsed = time.time() - start

        print("\nthread time:\t%f %d" % (elapsed, counter))

    def test_corun(self):
        global counter
        counter = 0
        start = time.time()
        scheduler = corun.Scheduler()
        tids = []
        for _ in range(0,self.iterations):
            tids.append(scheduler.new(coruntestfunc()))
        scheduler.joinall(tids)
        scheduler.shutdown()
        elapsed = time.time() - start

        print("\ncorun time:\t%f %d" % (elapsed, counter))

if __name__ == '__main__':
    unittest.main()
