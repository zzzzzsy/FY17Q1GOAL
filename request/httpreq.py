from urllib.request import (Request, urlopen)
from urllib.error import (HTTPError, URLError, ContentTooShortError)
from configparser import ConfigParser
from urllib.parse import urlencode
from threading import Thread
import time
import socket
import requests


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
    def __init__(self, reqs, thinktime=0):
        Thread.__init__(self)
        self.running = True
        self.reqs = reqs
        self.thinktime = thinktime

    def send(self, req):
        try:
            start_time = time.clock()
            resp = urlopen(req)
            conn_end_time = time.clock()
            content = resp.read().decode()
            end_time = time.clock()
            resp.close()
        except HTTPError as err1:
            resp = None
            conn_end_time = time.clock()
            content = err1.reason
            end_time = time.clock()
        except URLError as err2:
            resp = None
            conn_end_time = time.clock()
            content = err2.reason
            end_time = time.clock()
        except ContentTooShortError as err3:
            resp = None
            conn_end_time = time.clock()
            content = err3.reason
            end_time = time.clock()
        except socket.timeout:
            resp = None
            conn_end_time = time.clock()
            content = 'Request time out'
            end_time = time.clock()
        finally:
            if resp is not None:
                resp.close()
        return resp, content, start_time, end_time, conn_end_time

    def run(self):
        vu_start_time = time.clock()
        while self.running:
            for req in self.reqs:
                time.sleep(self.thinktime)
                if self.running:
                    resp, content, start_time, end_time, conn_end_time = self.send(req)
                    print('res time is:' + str(end_time - start_time))
                else:
                    break
        vu_end_time = time.clock()
        print('vu running time is:' + str(vu_end_time - vu_start_time))

    def stop(self):
        self.running = False


class LoadMagr(Thread):
    def __init__(self, reqs, num_vus, thinktime=0):
        Thread.__init__(self)
        self.requests = reqs
        self.num_vus = num_vus
        self.running = True
        self.lstvu = []
        self.thinktime = thinktime
        socket.setdefaulttimeout(20)

    def run(self):
        self.running = True
        for i in range(self.num_vus):
            if self.running:
                vu = LoadVU(self.requests, self.thinktime)
                vu.start()
                time.sleep(0.05)
                self.lstvu.append(vu)
                print('VU ' + str(i) + ' started.')

    def stop(self):
        self.running = False
        for vu in self.lstvu:
            vu.stop()


# class ErrorResponse:
#     def __init__(self):


reqs = get_request()
t = LoadMagr(reqs, 3000)
t.start()
time.sleep(200)
t.stop()
