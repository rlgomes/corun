"""
corun is a coroutine-based Python library that uses only built-in Python 
features to provide a low-level event driven programming model to be used when 
you can't scale a very common thread based approach to 10K+ threads that need
to concurrently cooperate on the system. Its also the case that the tasks being
done by those threads is primarily I/O bound and not CPU bound as at that point
the coroutine approach may not perform as well as a regular threaded model 
would.
"""

import select
import heapq
import threading
import time

from Queue import Queue

__DEBUG__ = False

class Task(object):
    """
    the basic unit of work with a corun environment that represents the unit of
    work to be done at any given moment. this is also the object that holds
    the coroutine execution until the scheduler is ready to schedule this task
    back into execution
    """

    def __init__(self, target):
        # the hash is a great and free task id :)
        self.tid = self.__hash__()
        self.target = target
        self.sendval = None

    def run(self):
        """
        runs the task by sending the current sendval to the target generator 
        which is waiting a yield statement
        """
        return self.target.send(self.sendval)

class SystemCall(object):
    """
    system calls are special because they allow the system to do things such as
    wait for a given task to terminate or wait for I/O to be available on a 
    specific socket before giving control back to the task at hand.
    """
    def handle(self, scheduler, task):
        """
        system call handler which receives the current task that this system
        call is handling as well as the scheduler in case the system call 
        needs to interact with the scheduler.
        """
        pass

class KillTask(SystemCall):
    """
    System call to kill an existing coroutine by their taskid
    """
    def __init__(self, tid):
        SystemCall.__init__(self)
        self.tid = tid

    def handle(self, scheduler, task):
        """
        handle the killing of the specified task
        """
        dtask = scheduler.taskmap.get(self.tid)
        if dtask:
            dtask.target.close()
            task.sendval = True
        else:
            task.sendval = False
        scheduler.ready.put(task)    

class WaitForTask(SystemCall):
    """
    System call to wait for another Task to end
    """
    def __init__(self, tid):
        SystemCall.__init__(self)
        self.tid = tid

    def handle(self, scheduler, task):
        """
        handle the waiting for the specified task
        """
        result = scheduler.wait_for_exit(task, self.tid)
        task.sendval = result
        
        if not result:
            scheduler.ready.put(task)

class WaitForTime(SystemCall):
    """
    System call to wait for specified amoutn of time
    """
    def __init__(self, seconds):
        SystemCall.__init__(self)
        self.seconds = seconds
        
    def handle(self, scheduler, task):
        """
        handle the scheduling of when this task should be scheduled back into 
        the normal corun execution
        """
        exptime = time.time() + self.seconds
        scheduler.wait_for_time(task, exptime)

class ReadTask(SystemCall):
    """
    System call to wait for the specified file descriptor to have bytes to read
    """
    def __init__(self, fileobj):
        SystemCall.__init__(self)
        self.fileobj = fileobj
        
    def handle(self, scheduler, task):
        """
        places the current task into the read_waiting queue
        """
        fdesc = self.fileobj.fileno()
        scheduler.wait_for_read(task, fdesc)
        
class WriteTask(SystemCall):
    """
    System call to wait for the specified file descriptor to be able to write to
    """
    def __init__(self, fileobj):
        SystemCall.__init__(self)
        self.fileobj = fileobj

    def handle(self, scheduler, task):
        """
        places the current task into the write_waiting queue
        """
        fdesc = self.fileobj.fileno()
        scheduler.wait_for_write(task, fdesc) 

class Scheduler(threading.Thread):
    """
    The heart of the corun module that basically handles everything from 
    scheduling new tasks into the corun environment to handling that all dead
    tasks are correctly cleaned up after wards.
    """

    def __init__(self):
        threading.Thread.__init__(self)

        self.ready = Queue()
        self.taskmap = {}
        self.exit_waiting = {}

        self.write_waiting = {}
        self.read_waiting = {}

        self.epoll = select.epoll()
        self.epoll_wait_time = 0.1
        
        self.time_waiting_heap = []

        self.running = True
        self.start()

    def new(self, target, name=None):
        """
        takes the target function which should be a generator and puts it into 
        the corun scheduler to be executed as soon as possible.
        """
        newtask = Task(target)
        newtask.name = name
        self.taskmap[newtask.tid] = newtask
        # schedule this task now!
        self.ready.put(newtask)
        return newtask.tid

    def wait_for_time(self, task, exptime):
        """
        add the current task to the time waiting queue which is checked by the 
        __time_poll_task task
        """
        heapq.heappush(self.time_waiting_heap,(exptime,task))
    
    def wait_for_read(self, task, fdesc):
        """
        setup the required polling mechanism for read waiting
        """
        if fdesc in self.write_waiting:
            self.epoll.modify(fdesc, select.EPOLLOUT | select.EPOLLIN)
        else:
            self.epoll.register(fdesc, select.EPOLLIN)
        if __DEBUG__:
            print("%f: w4r %s" % (time.time(), fdesc))
        self.read_waiting[fdesc] = task

    def wait_for_write(self, task, fdesc):
        """
        setup the required polling mechanism for write waiting
        """
        if fdesc in self.read_waiting:
            self.epoll.modify(fdesc, select.EPOLLIN | select.EPOLLOUT)
        else:
            self.epoll.register(fdesc, select.EPOLLOUT)
        if __DEBUG__:
            print("%f: w4w %s" % (time.time(), fdesc))
        self.write_waiting[fdesc] = task
            
    def wait_for_exit(self, task, waitid):
        """
        just add the task to the exit_waiting list that is checked on each task
        exit
        """
        if waitid in self.taskmap:
            self.taskmap.pop(task.tid)
            if waitid in self.exit_waiting:
                self.exit_waiting[waitid].append(task)
            else:
                self.exit_waiting[waitid] = [task]   
            return True
        else:
            return False
        
    def __epoll(self, timeout):
        """
        epoll checking 
        """
        fdevents = self.epoll.poll(timeout)

        for (fdesc, eventmask) in fdevents:
            task = None
            if eventmask & select.EPOLLHUP or eventmask & select.EPOLLERR:
                if __DEBUG__:
                    print("%f: ERROR %s" % (time.time(), fdesc))
                        
                self.epoll.unregister(fdesc) 
                task = None
                    
                if fdesc in self.read_waiting:
                    task = self.read_waiting.pop(fdesc)
                        
                if fdesc in self.write_waiting:
                    task = self.write_waiting.pop(fdesc)
                    
                task.sendval = False    
                self.ready.put(task)
            elif eventmask & select.EPOLLOUT:
                task = self.write_waiting.pop(fdesc)
                task.senval = True
                        
                if __DEBUG__:
                    print("%f: ww.pop %s" % (time.time(), fdesc))
                    
                if fdesc in self.read_waiting.keys():
                    self.epoll.modify(fdesc, select.EPOLLIN)
                else:
                    self.epoll.unregister(fdesc)
                        
                self.ready.put(task)
            elif eventmask & select.EPOLLIN:
                task = self.read_waiting.pop(fdesc)
                task.sendval = True
                        
                if __DEBUG__:
                    print("%f: rw.pop %s" % (time.time(), fdesc))
                        
                if fdesc in self.write_waiting.keys():
                    self.epoll.modify(fdesc, select.EPOLLOUT)
                else:
                    self.epoll.unregister(fdesc)
                        
                self.ready.put(task)
                
    def __io_epoll_task(self): 
        """
        epoll task that checks if currently awaiting io tasks can be dispatched
        """
        while True:
            if self.ready.qsize() == 0:
                # nothing else to do then lets do a "long" wait
                self.__epoll(self.epoll_wait_time)
            else:
                self.__epoll(0)
            yield

    def __time_poll_task(self):
        """
        internal task that basically polls for tasks that are suppose to 
        execute at an instant of time in the future.
        """
        while True:
            current_time = time.time()
            try:
                (exptime,task) = self.time_waiting_heap[0]
                    
                while exptime <= current_time:
                    heapq.heappop(self.time_waiting_heap)
                    self.ready.put(task)
                    (exptime,task) = self.time_waiting_heap[0]
            except IndexError:
                pass
                    
            yield
            
    def wait_for_tasks(self, coroutines, event): 
        """
        built-in scheduler task that waits for all of the coroutines identified
        before finishing
        """
        count = 0
        for tid in coroutines:
            if tid in self.taskmap:
                count+=1
                yield WaitForTask(tid)
        event.set()
           
    def joinall(self, coroutines):
        """
        wait for the specified coroutine ids to exit
        """
        event = threading.Event()
        self.new(self.wait_for_tasks(coroutines, event))
        event.wait()

    def shutdown(self):
        """
        tell the corun scheduler to shutdown 
        """
        self.running = False
        self.join()

    def run(self):
        self.new(self.__io_epoll_task(),"epoll")
        self.new(self.__time_poll_task(), "tpoll")

        while self.running:
            task = self.ready.get()

            try:
                result = task.run()

                if isinstance(result, SystemCall):
                    result.handle(self, task)
                else:
                    self.ready.put(task)
            except StopIteration:
                del self.taskmap[task.tid]

                # notify others of exit
                if task.tid in self.exit_waiting:
                    others = self.exit_waiting.pop(task.tid)
                    for other in others:
                        self.taskmap[other.tid] = other
                        self.ready.put(other)
            except:
                # we don't want the scheduler to die 
                import traceback
                traceback.print_exc()
                del self.taskmap[task.tid]
                        