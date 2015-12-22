""" Some helper objects and functions to help optimise slow functions.

    Author: Alastair Hughes
"""

from threading import BoundedSemaphore, Lock, Thread
import functools

# Local imports
from constants import THREAD_COUNT


class ThreadedGroup:
    """ An object to keep an arbitary number of workers on an easily-split
        task.
    """
    
    def __init__(self):
        """ Initialise self """
        
        self._job_count = 0 # The number of active jobs.
        self.lock = Lock() # Lock protecting job_count...
        self.semaphore = BoundedSemaphore(THREAD_COUNT)
        
    def start(self, func, *args, **kargs):
        """ Start the given job. This will block until there are free
            workers.
        """
        
        def job_wrapper():
            """ Run the job, then decrement the job count and release the
                semaphore.
            """
            try:
                func(*args, **kargs)
            finally:
                with self.lock:
                    self._job_count -= 1
                self.semaphore.release()
        
        # Create the job.
        job = Job(job_wrapper)
        # Acquire the semaphore and start.
        self.semaphore.acquire()
        with self.lock:
            self._job_count += 1
        job.start()
        
    def wait(self):
        """ Wait until all of the jobs are finished """
        
        print("Waiting for jobs to finish...")
        
        while self.get_job_count() != 0:
            # Block until another job ends.
            self.semaphore.acquire()
            
        print("Jobs finished!")

    def get_job_count(self):
        """ Return the current job count """

        with self.lock:
            return self._job_count
           

class ThreadedDict(object):
    """ A threaded, locking, load-from-disk dict """
    
    def __init__(self, load_func):
        """ Initialise self.
            load_func is the function to call to try to load a value.
            start and end are callbacks passed to the lock wrapper to provide
            a means of giving user feedback.
        """
        
        # The dict of loading jobs. (name: job)
        self.job_dict = {}
        # The lock protecting self's dict.
        self.lock = Lock()
        # Self's dict.
        self.dict = {}
        # The load function takes a name, and returns the corresponding value.
        def wrapper(name):
            value = load_func(name)
            with self.lock:
                self.dict[name] = value
        self.load_func = wrapper
        
    def __getitem__(self, name):
        """ Try to get the given item """
        
        # See whether the value is cached.
        with self.lock:
            if name in self.dict:
                # It is cached; return it!
                return self.dict[name]
        
        # Otherwise, cache it, wait for the job to finish, and then return.
        self.cache(name)
        # Wait for the job to finish.
        self.job_dict[name].join()
        # Now we lock, retrieve the value, and return.
        with self.lock:
            return self.dict[name]
        
    def cache(self, name):
        """ Cache the given item, if required """
        
        print("Caching {}".format(name))
        
        # Check wether or not the item is in the process of being cached.
        if name in self.job_dict:
            # The item is cached or being cached; return.
            return
                
        # Otherwise, start loading it and return.
        job = Job(self.load_func, name)
        self.job_dict[name] = job
        job.start()
            
            
class Job(Thread):
    """ Threaded job class """
    
    def __init__(self, function, *args, **kargs):
        """ Initialise self """
        
        Thread.__init__(self)
        self.daemon = True # This is a daemon thread by default.
        self.function = function
        self.args = args
        self.kargs = kargs
        
    def run(self):
        """ Run the function """
        # TODO: Currently, if this fails, the exception is not passed out to
        #       the caller.
        self.function(*self.args, **self.kargs)


class FuncVar():
    """ A stupid 'variable', supporting set and get methods """

    def __init__(self, value = None):
        """ Initialise self """
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class ListVar(FuncVar):
    """ A 'variable' list, supporting get and set methods """

    def __init__(self, value = None):
        """ Initialise self """
        if value != None:
            self.value = value
        else:
            self.value = []

        # Init the wrappers.
        self.append = self.value.append
        self.__getitem__ = self.value.__getitem__
        self.__setitem__ = self.value.__setitem__
        self.__delitem__ = self.value.__delitem__
        self.__iter__ = self.value.__iter__
        

def cache(func):
    """ Wrap the given function to cache it """
    cache = {}
    
    @functools.wraps(func)
    def cacher(*args, **kargs):
        key = tuple(args, *[(key, value) for key, value in kargs.items()])
        if key not in cache:
            cache[key] = func(*args, **kargs)
        return cache[key]
    return cacher
    
