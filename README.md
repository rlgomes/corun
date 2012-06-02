corun
=====

Acknowledgements
----------------

I'd like to acknowledge that without the work previously done by
**David Beazey** I probably wouldn't have such a great starting point for writing
this module. I started writing corun after going through his presentation found
[here](http://www.dabeaz.com/coroutines/). From which I drew quite a bit of the
scheduler work done in **corun**. There were a few things I decided to drop
yield trampolining from the **corun** module because I found that it complicated
the code more (resulting in some performance issues that I couldn't easily
solve) as well as it didn't give the end module user the full control of when
his/her coroutine wanted to give time for the scheduler to schedule in more
workers. I also decided to add a few new notions which included the ability to
put coroutines to sleep for sometime and came up with a solution similar to the
solution presented by David on how to make a task wait for another task to
terminate.

Introduction
------------

**corun** is a coroutine based Python library that uses only built-in Python
features to provide a low-level event driven programming model to be used when
you can't scale a very common thread based approach to 10K+ concurrently
running threads. Its also the case that the tasks being done by those threads is
primarily I/O bound and not CPU bound as at that point the coroutine approach
may not perform as well as a regular threaded model.

There are a few other "similar" libraries out there such as gevent and cogen,
but I found that gevent tried to hide the exact points at which your coroutine
was "yielding" to the scheduler. Cogen was closer to what I wanted but I didn't
see why it needed you to decorate your coroutines with the **@coro** decorator
and their google code project hasn't been touched in 2 years and even pip or
easy_install couldn't find some dependencies when trying to install. So I'm
assuming that the code is unmaintained and an abadoned project at this point.

Requirements
------------

   * Python 2.5+

Installation
------------

	pip install -e git+git://github.com/rlgomes/corun.git#egg=corun

Usage Examples
--------------

For examples have a look at the tests folder. I will add more samples to this
README in the near future which will describe different ways of using corun.

Performance Stats
-----------------

You can easily run the built-in tests by issuing:

	python setup.py test

on a freshly checked out copy and you'll get results similar to the following:

	test_corun (tests.concurrent_task_test.ConcurrenTaskTest) ...
	corun time:	0.269580 10000
	ok
	test_gevent (tests.concurrent_task_test.ConcurrenTaskTest) ...
	gevent time:	0.497005 10000
	ok
	test_thread (tests.concurrent_task_test.ConcurrenTaskTest) ...
	thread time:	1.338474 10000
	ok
	test_corun (tests.io_task_test.IOTaskTest) ...
	corun time:	0.289584 100
	ok
	test_gevent (tests.io_task_test.IOTaskTest) ...
	gevent time:	3.748089 100
	ok
	test_thread (tests.io_task_test.IOTaskTest) ...
	thread time:	1.230650 100
	ok
	Starting tests in 3 seconds...
	concurrent connection limit is 2048
	listening at localhost:9999
	test_1_thread (tests.urlfetch_test.URLFetchTest) ...
	thread time:	4.171722 1000
	ok
	test_2_corun (tests.urlfetch_test.URLFetchTest) ...
	corun time:	0.450275 1000
	ok
	test_3_gevent (tests.urlfetch_test.URLFetchTest) ...
	gevent time:	0.489684 1000
	ok

	----------------------------------------------------------------------
	Ran 9 tests in 17.363s

	OK

The results of my tests are pretty impressive but I realize this library still
needs a few features and may certainly have situations where it does not
outperform the other two approaches.
