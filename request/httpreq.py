from urllib.request import (Request, urlopen)
from configparser import ConfigParser
from urllib.parse import urlencode
from config import config
from threading import Thread
import time


# To generate requests
class Reqs():
    def __init__(self):
        self.reqs = self.__get_requests()

    @staticmethod
    def __get_requests():
        temp = []
        cf = ConfigParser()
        cf.read(config.REQ_LIST)
        secs = cf.sections()
        l = len(secs)
        while l > 0:
            data = None
            if cf.has_section('values'):
                values = cf.get('request_' + str(l), 'values')
                data = urlencode(eval(values)).encode('utf-8')
            req = Request(cf.get('request_' + str(l), 'url'), data)
            if cf.has_section('headers'):
                req.headers = eval(cf.get('request_' + str(l), 'headers'))
            l -= 1
            temp.append(req)
        return temp


class Load(Thread):
    def __init__(self, req):
        Thread.__init__(self)
        self.__req = req
        self.__stop = False

    def send(self, req):
        try:
            res = urlopen(req)
        except Exception as e:
            print(e)
        return res

    def run(self):
        while not self.__stop:
            s = time.time()
            res = self.send(self.__req)
            e = time.time()
            print(self.name)
            print(res.getcode())
            print(e-s)

    def stop(self):
        self.__stop = True

reqs = Reqs().reqs
temp = []
for req in reqs:
    res = Load(req)
    temp.append(res)

for t in temp:
    t.start()
time.sleep(5)
for t in temp:
    t.stop()







