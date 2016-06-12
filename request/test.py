from collections import deque
import sys
import time
from urllib.request import (Request, urlopen)


def countdown(n):
    while n > 0:
        print('count down: ', n)
        yield
        n -= 1


def countup(n):
    x = 0
    while x < n:
        print('count up: ', x)
        time.sleep(5)
        yield
        x += 1


class Task:
    def __init__(self):
        self._task_deque = deque()

    def new_task(self, task):
        self._task_deque.append(task)

    def run(self):
        while self._task_deque:
            task = self._task_deque.popleft()
            try:
                next(task)
                self._task_deque.append(task)
            except StopIteration:
                sys.exit(0)


c = countdown(1)
print(c)
next(c)
next(c)
