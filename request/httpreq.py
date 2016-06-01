from urllib.request import (Request, urlopen)
from urllib.error import HTTPError
from configparser import ConfigParser
from urllib.parse import urlencode
from threading import Thread
import time


def get_request():
    temp = []
    cf = ConfigParser()
    cf.read('../config/requests.conf')
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


class LoadVU(Thread):
    def __init__(self, req):
        Thread.__init__(self)
        self.running = True
        self.req = req

    def send(self):
        try:
            start_time = time.clock()
            resp = urlopen(self.req)
            conn_end_time = time.clock()
            content = resp.read()
            end_time = time.clock()
        except HTTPError as err:
            resp = None
            conn_end_time = time.clock()
            content = err.reason
            end_time = time.clock()
        return resp, content, start_time, end_time, conn_end_time

    def run(self):
        vu_start_time = time.clock()
        while self.running:
            if self.running:
                resp, content, start_time, end_time, conn_end_time = self.send()
                print('res time is:' + str(end_time-start_time))
            else:
                break
        vu_end_time = time.clock()
        print('vu running time is:' + str(vu_end_time - vu_start_time))

    def stop(self):
        self.running = False


class LoadMagr(Thread):
    def __init__(self, reqs, num_vus):
        Thread.__init__(self)
        self.requests = reqs
        self.num_vus = num_vus
        self.running = True
        self.lstvu = []

    def run(self):
        while self.running:
            for i in range(self.num_vus):
                if self.running:
                    for req in self.requests:
                        vu = LoadVU(req)
                        vu.start()
                        self.lstvu.append(vu)
                        print('start')

    def stop(self):
        self.running = False
        for vu in self.lstvu:
            vu.stop()
            print('stop')


reqs = get_request()
t = LoadMagr(reqs, 10)
t.start()
# time.sleep(5)
t.stop()
