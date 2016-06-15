from configparser import ConfigParser
from urllib.parse import urlencode
from threading import Thread
import time
import requests
from queue import Queue


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
    def __init__(self, url, headers=None, method='GET', para=None):
        self.url = url
        if headers:
            self.headers = headers
        else:
            self.headers = {}
        if 'user-agent' not in [header.lower() for header in self.headers]:
            self.add_header('User-Agent', 'Mozilla/4.0 (compatible; Pylot)')
        # if 'connection' not in [header.lower() for header in self.headers]:
        #     self.add_header('Connection', 'close')
        self.method = method
        self.para = para

    def add_header(self, header, value):
        self.headers[header] = value


class ErrResponse:
    def __init__(self, reason='Unknow Error Message'):
        self.status_code = -1
        self.reason = reason


class LoadVU(Thread):
    def __init__(self, id, think_time, req_list, result_states, err_states, result_queue):
        Thread.__init__(self)
        self.running = True
        self.id = id
        self.think_time = think_time
        self.req_list = req_list
        self.result_states = result_states
        self.err_states = err_states
        self.result_queue = result_queue

        self.count = 0
        self.err_count = 0
        self.excep_count = 0

    def send(self, req):
        try:
            start_time = time.clock()
            if req.method == 'GET':
                resp = requests.get(req.url, timeout=60)
            conn_end_time = time.clock()
            content = resp.content
            end_time = time.clock()
        except requests.exceptions.Timeout:
            conn_end_time = time.clock()
            content = 'Time Out Error'
            resp = ErrResponse(content)
            end_time = time.clock()
        except requests.exceptions.ConnectionError:
            conn_end_time = time.clock()
            content = 'Connection Error'
            resp = ErrResponse(content)
            end_time = time.clock()
            time.sleep(1)
        return resp, content, start_time, end_time, conn_end_time

    def run(self):
        vu_start_time = time.clock()
        total_bytes = 0
        while self.running:
            for req in self.req_list:
                if self.running:
                    resp, content, start_time, end_time, conn_end_time = self.send(req)
                    error_flag = False
                    excep_flag = False
                    if resp.status_code >= 400:
                        error_flag = True
                    elif resp.status_code <= 0:
                        excep_flag = True
                    else:
                        total_bytes += len(content)
                    if error_flag:
                        self.err_count += 1
                    if excep_flag:
                        self.excep_count += 1
                    self.count += 1
                    self.result_states[self.id] = ResultState(resp.status_code, resp.reason, self.count,
                                                              self.err_count, self.excep_count, total_bytes)

                    print('res time is:' + str(end_time - start_time))
                else:
                    break
        vu_end_time = time.clock()
        self.result_states[self.id].vu_start_time = vu_start_time
        self.result_states[self.id].vu_end_time = vu_end_time
        print('vu running time is:' + str(vu_end_time - vu_start_time))

    def stop(self):
        self.running = False


class ResultState:
    def __init__(self, code, reason, count, err_coount, excep_count, total_bytes):
        self.code = code
        self.reason = reason
        self.count = count
        self.err_count = err_coount
        self.excep_count = excep_count
        self.total_bytes = total_bytes
        self.vu_start_time = None
        self.vu_end_time = None


class WorkLoad:
    def __init__(self, ramp_up, think_time, vu_nums):
        self.ramp_up = ramp_up
        self.think_time = think_time
        self.vu_nums = vu_nums


class LoadMagr(Thread):
    def __init__(self, work_load, result_states, err_states):
        Thread.__init__(self)
        self.work_load = work_load
        if isinstance(work_load, WorkLoad):
            self.num_vus = work_load.vu_nums
            self.ranm_up = work_load.ramp_up
            self.think_time = work_load.think_time
        else:
            self.num_vus = 1
            self.ranm_up = 1
            self.think_time = 0
        self.running = True
        self.result_states = result_states
        self.err_states = err_states
        self.vu_list = []
        self.req_list = []
        self.result_queue = Queue()
        for i in range(self.num_vus):
            self.result_states[i] = ResultState(0, '', 0, 0, 0, 0)

    def run(self):
        self.running = True
        for i in range(self.num_vus):
            spacing = round(self.ranm_up / self.num_vus, 2)
            if i > 0:
                time.sleep(spacing)
            if self.running:
                vu = LoadVU(i, self.think_time, self.req_list, self.result_states,
                            self.err_states, self.result_queue)
                vu.start()
                # time.sleep(0.05)
                self.vu_list.append(vu)
                print('VU ' + str(i) + ' started.')

    def stop(self):
        self.running = False
        for vu in self.vu_list:
            vu.stop()

    def add_req(self, req):
        self.req_list.append(req)


reqs = get_request()
workload = WorkLoad(1, 0.05, 100)
result_states = []
err_states = []
for i in range(200):
    result_states.append(None)
    err_states.append(None)
t = LoadMagr(workload, result_states, err_states)
for req in reqs:
    t.add_req(req)
t.start()
time.sleep(50)
t.stop()
