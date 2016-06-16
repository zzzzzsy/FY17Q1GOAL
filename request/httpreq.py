from configparser import ConfigParser
from urllib.parse import urlencode
from threading import Thread
import time
import requests
from config import config


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
        self.method = method
        self.para = para

    def add_header(self, header, value):
        self.headers[header] = value


class ErrResponse:
    def __init__(self, reason='Unknow Error Message'):
        self.status_code = -1
        self.reason = reason


class LoadVU(Thread):
    def __init__(self, vu_id, think_time, req_list, results, err_states):
        Thread.__init__(self)
        self.running = True
        self.id = vu_id
        self.think_time = think_time
        self.req_list = req_list
        self.results = results
        self.err_states = err_states

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
                    res_bytes = 0
                    if resp.status_code >= 400:
                        error_flag = True
                    elif resp.status_code <= 0:
                        excep_flag = True
                    else:
                        res_bytes = len(content)
                        total_bytes += res_bytes
                    if error_flag:
                        self.err_count += 1
                    if excep_flag:
                        self.excep_count += 1
                    r = ResState(resp.status_code, resp.reason, self.count, res_bytes, str(conn_end_time - start_time),
                                 str(end_time - start_time))
                    self.count += 1
                    self.results[self.id].add_res_state(r)
                    if config.CONSOLE:
                        print('res time is:' + str(end_time - start_time))
                else:
                    break
        vu_end_time = time.clock()
        self.results[self.id].vu_finalize(vu_start_time, vu_end_time, self.err_count, self.excep_count, total_bytes)
        if config.CONSOLE:
            print('vu running time is:' + str(vu_end_time - vu_start_time))

    def stop(self):
        self.running = False


class ResState:
    def __init__(self, code, reason, count, res_bytes, conn_time, res_time):
        self.code = code
        self.reason = reason
        self.count = count
        self.bytes = res_bytes
        self.conn_time = conn_time
        self.res_time = res_time

    def __str__(self):
        return 'Request %d: Code: %d, Desc: %s, Bytes: %d, Connection time: %s, Res time: %s' % (
            self.count, self.code, self.reason, self.bytes, self.conn_time, self.res_time)


class VUResCollection:
    def __init__(self, vu_id):
        self.id = vu_id
        self.vu_res_state = []
        self.vu_start_time = None
        self.vu_end_time = None
        self.err_cnt = 0
        self.excp_cnt = 0
        self.total_bytes = 0
        self.cursor = 0

    def add_res_state(self, res_state):
        self.vu_res_state.append(res_state)

    def vu_finalize(self, st, et, err_cnt, excp_cnt, total_bytes):
        self.vu_start_time = st
        self.vu_end_time = et
        self.err_cnt = err_cnt
        self.excp_cnt = excp_cnt
        self.total_bytes = total_bytes

    def __iter__(self):
        return self

    def __next__(self):
        if self.cursor == len(self.vu_res_state):
            raise StopIteration
        temp = self.vu_res_state[self.cursor]
        self.cursor += 1
        return temp

    def __str__(self):
        return 'VU %d: Start time %s, End time %s; Error count: %d, ' \
               'Exception count: %d; Total request: %d, Total bytes: %d' % (
                   self.id, self.vu_start_time, self.vu_end_time, self.err_cnt,
                   self.excp_cnt, len(self.vu_res_state),
                   self.total_bytes)


class WorkLoad:
    def __init__(self, ramp_up, think_time, vu_nums):
        self.ramp_up = ramp_up
        self.think_time = think_time
        self.vu_nums = vu_nums


class LoadMagr(Thread):
    def __init__(self, work_load):
        Thread.__init__(self)
        self.work_load = work_load
        self.results = []
        self.err_states = []
        if isinstance(work_load, WorkLoad):
            self.num_vus = work_load.vu_nums
            self.ranm_up = work_load.ramp_up
            self.think_time = work_load.think_time
            for i in range(self.num_vus):
                self.results.append(VUResCollection(i))
        else:
            self.num_vus = 1
            self.ranm_up = 1
            self.think_time = 0
        self.running = True
        self.vu_list = []
        self.req_list = []

    def run(self):
        self.running = True
        for i in range(self.num_vus):
            spacing = round(self.ranm_up / self.num_vus, 2)
            if i > 0:
                time.sleep(spacing)
            if self.running:
                vu = LoadVU(i, self.think_time, self.req_list, self.results,
                            self.err_states)
                vu.start()
                # time.sleep(0.05)
                self.vu_list.append(vu)
                if config.CONSOLE:
                    print('VU ' + str(i) + ' started.' + str(time.clock()))

    def stop(self):
        self.running = False
        for vu in self.vu_list:
            vu.stop()
        for vu in self.vu_list:
            while vu.isAlive():
                time.sleep(0.01)

    def add_req(self, req):
        self.req_list.append(req)


class Calculate:
    def __init__(self, val):
        self.val = [float(item) for item in val]

    def sum(self):
        if len(self.val) < 1:
            return None
        else:
            return sum(self.val)

    def count(self):
        return len(self.val)

    def max(self):
        if len(self.val) < 1:
            return None
        else:
            return max(self.val)

    def min(self):
        if len(self.val) < 1:
            return None
        else:
            return min(self.val)

    def avg(self):
        if len(self.val) < 1:
            return None
        else:
            return sum(self.val) / len(self.val)

    def mid(self):
        if len(self.val) < 1:
            return None
        else:
            seq = self.val
            seq.sort()
            return seq[len(seq) // 2]

    def percentile(self, p):
        if len(self.val) < 1:
            value = None
        elif p >= 100:
            print('ERROR: percentile must be < 100.  you supplied: %s\n' % p)
            value = None
        else:
            seq = self.val
            seq.sort()
            print(seq)
            index = int(len(self.val) * (p / 100))
            if len(self.val) * p % 100 == 0:
                value = seq[index - 1]
            else:
                value = (seq[index - 1] + seq[index]) / 2
        return value


reqs = get_request()
workload = WorkLoad(50, 0.05, 3000)
t = LoadMagr(workload)
for req in reqs:
    t.add_req(req)
t.start()
time.sleep(200)
t.stop()

for res in t.results:
    print(res)
    for r in res:
        print(r)
