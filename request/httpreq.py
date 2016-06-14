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
        para = None
        url = cf.get('request_' + str(l), 'url')
        if cf.has_section('values'):
            values = cf.get('request_' + str(l), 'values')
            para = urlencode(eval(values)).encode('utf-8')
        if cf.has_option('request_' + str(l), 'headers'):
            headers = eval(cf.get('request_' + str(l), 'headers'))
        if cf.has_option('request_' + str(l), 'method'):
            method = cf.get('request_' + str(l), 'method')
        else:
            method = 'GET'
        req = Request(url, headers, method, para)
        l -= 1
        temp.append(req)

    return temp


class Request:
    def __init__(self, url, headers, method, para):
        self.url = url
        self.headers = headers
        self.method = method
        self.para = para


class LoadVU(Thread):
    def __init__(self, reqs, thinktime=0):
        Thread.__init__(self)
        self.running = True
        self.reqs = reqs
        self.thinktime = thinktime

    def send(self, req):
        try:
            start_time = time.clock()
            if req.method == 'GET':
                resp = requests.get(req.url, timeout=60)
            conn_end_time = time.clock()
            content = resp.content
            end_time = time.clock()
        except requests.exceptions.Timeout:
            resp = None
            conn_end_time = time.clock()
            content = 'Time Out'
            end_time = time.clock()
        except requests.exceptions.ConnectionError:
            resp = None
            time.sleep(1)
            conn_end_time = time.clock()
            content = 'ConnectionError'
            end_time = time.clock()
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
                # time.sleep(0.05)
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
time.sleep(50)
t.stop()
