# Copyright 2013-2018 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

"""
This implements a parallel map operation but it can accept more values
than multiprocessing.Pool.apply() can.  For example, apply() will fail
to pickle functions if they're passed indirectly as parameters.
"""
from multiprocessing import Process, Pipe, Semaphore, Value

__all__ = ['spawn', 'parmap', 'Barrier']


def spawn(f):
    def fun(pipe, x):
        pipe.send(f(x))
        pipe.close()
    return fun


def parmap(f, elements):
    pipe = [Pipe() for x in elements]
    proc = [Process(target=spawn(f), args=(c, x))
            for x, (p, c) in zip(elements, pipe)]
    [p.start() for p in proc]
    [p.join() for p in proc]
    return [p.recv() for (p, c) in pipe]


class Barrier:
    """Simple reusable semaphore barrier.

    Python 2.6 doesn't have multiprocessing barriers so we implement this.

    See http://greenteapress.com/semaphores/downey08semaphores.pdf, p. 41.
    """

    def __init__(self, n, timeout=None):
        self.n = n
        self.to = timeout
        self.count = Value('i', 0)
        self.mutex = Semaphore(1)
        self.turnstile1 = Semaphore(0)
        self.turnstile2 = Semaphore(1)

    def wait(self):
        if not self.mutex.acquire(timeout=self.to):
            raise BarrierTimeoutError()
        self.count.value += 1
        if self.count.value == self.n:
            if not self.turnstile2.acquire(timeout=self.to):
                raise BarrierTimeoutError()
            self.turnstile1.release()
        self.mutex.release()

        if not self.turnstile1.acquire(timeout=self.to):
            raise BarrierTimeoutError()
        self.turnstile1.release()

        if not self.mutex.acquire(timeout=self.to):
            raise BarrierTimeoutError()
        self.count.value -= 1
        if self.count.value == 0:
            if not self.turnstile1.acquire(timeout=self.to):
                raise BarrierTimeoutError()
            self.turnstile2.release()
        self.mutex.release()

        if not self.turnstile2.acquire(timeout=self.to):
            raise BarrierTimeoutError()
        self.turnstile2.release()


class BarrierTimeoutError(Exception):
    pass