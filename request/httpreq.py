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
    def __init__(self, id, req):
        self.timer = time.time()
        self.running = True
        self.req = req
        print(id)

    def send(self, req):
        try:
            start_time = self.timer
            resp = urlopen(req)
            conn_end_time = self.timer
            content = resp.read()
            end_time = self.timer
        except HTTPError as err:
            resp = None
            conn_end_time = self.timer
            content = 'Error occurs during urlopen func'
            end_time = self.timer
        return resp, content, start_time, end_time, conn_end_time

    def run(self):
        vu_start_time = self.timer
        while self.running:
            resp, content, start_time, end_time, conn_end_time = self.send(self.req)
        print(resp)
        print(content)
        print(start_time)
        print(end_time)
        print(conn_end_time)

    def stop(self):
        self.running = False


# reqs = get_request()
# for req in reqs:
#     LoadVU(req)

print('hello')