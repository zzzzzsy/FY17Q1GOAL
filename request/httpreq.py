from configparser import ConfigParser
from urllib.parse import urlencode
from threading import Thread
from config import config
from pylab import *
import time
import requests
import csv
import os
import math


class RequestsConfig:
    def __init__(self, config_path=config.REQ_LIST):
        self.config_path = config_path
        self.req_list = []
        self.cf = ConfigParser()

    def get_request(self):
        self.cf.read(self.config_path)
        secs = self.cf.sections()
        l = len(secs)
        while l > 0:
            para = None
            strreq = 'request_' + str(l)
            url = self.cf.get(strreq, 'url')
            if self.cf.has_option(strreq, 'values'):
                values = self.cf.get(strreq, 'values')
                para = urlencode(eval(values)).encode('utf-8')
            if self.cf.has_option(strreq, 'headers'):
                headers = eval(self.cf.get(strreq, 'headers'))
            if self.cf.has_option(strreq, 'method'):
                method = self.cf.get(strreq, 'method')
            else:
                method = 'GET'
            req = Request(strreq, url, headers, method, para)
            l -= 1
            self.req_list.append(req)
        return self.req_list


class Request:
    def __init__(self, name, url, headers=None, method='GET', para=None):
        self.url = url
        self.name = name
        if headers:
            self.headers = headers
        else:
            self.headers = {}
        if 'user-agent' not in [header.lower() for header in self.headers]:
            self.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.2; WOW64; rv:22.0) Gecko/20100101 Firefox/22.0')
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
                resp = requests.get(req.url, headers=req.headers, timeout=60)
            else:
                resp = requests.post(req.url, req.para, headers=req.headers, timeout=60)
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
                    r = ResState(req.name, resp.status_code, resp.reason, self.count, res_bytes,
                                 str(conn_end_time - start_time),
                                 str(end_time - start_time), self.id)
                    self.count += 1
                    self.results[self.id].add_res_state(r)
                    if config.CONSOLE:
                        print('res time is:' + str(end_time - start_time))
                else:
                    break
                time.sleep(self.think_time)
        vu_end_time = time.clock()
        self.results[self.id].vu_finalize(vu_start_time, vu_end_time, self.err_count, self.excep_count, total_bytes)
        if config.CONSOLE:
            print('vu running time is:' + str(vu_end_time - vu_start_time))

    def stop(self):
        self.running = False


class ResState:
    def __init__(self, name, code, reason, count, res_bytes, conn_time, res_time, vu_id):
        self.name = name
        self.code = code
        self.reason = reason
        self.count = count
        self.bytes = res_bytes
        self.conn_time = conn_time
        self.res_time = res_time
        self.vu_id = vu_id
        self.res_lst = []

    def __str__(self):
        return 'VU %d Request %d Name %s: Code: %d, Desc: %s, Bytes: %d, Connection time: %s, Res time: %s' % (
            self.vu_id, self.count, self.name, self.code, self.reason, self.bytes, self.conn_time, self.res_time)

    def rowdict(self):
        self.res_lst.append(self.vu_id)
        self.res_lst.append(self.count)
        self.res_lst.append(self.name)
        self.res_lst.append(self.code)
        self.res_lst.append(self.reason)
        self.res_lst.append(self.bytes)
        self.res_lst.append(self.conn_time)
        self.res_lst.append(self.res_time)
        return self.res_lst


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
        self.res_lst = []

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

    def rowdict(self):
        self.res_lst.append(self.id)
        self.res_lst.append(self.vu_start_time)
        self.res_lst.append(self.vu_end_time)
        self.res_lst.append(self.err_cnt)
        self.res_lst.append(self.excp_cnt)
        self.res_lst.append(len(self.vu_res_state))
        self.res_lst.append(self.total_bytes)
        return self.res_lst


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


class CollectCSVResults:
    def __init__(self, load_magr, output_dir=config.OUTPUT_DIR):
        self.load_magr = load_magr
        self.output_dir = output_dir
        strfile = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
        result_dir = self.output_dir + config.PROJECT_NAME
        if not os.path.exists(result_dir):
            os.makedirs(result_dir)
        self.vu_file = result_dir + '/' + 'vu_results_' + strfile + '.csv'
        self.res_file = result_dir + '/' + 'res_results_' + strfile + '.csv'
        self.vu_res = []
        self.req_res = []

    def generate_result(self):
        vu_headers = ['vu', 'st time', 'et time', 'err cnt', 'excp cnt', 'ttl reqs',
                      'ttl bytes']
        res_headers = ['vu', 'req id', 'req name', 'res code', 'desc', 'bytes', 'conn time', 'res time']

        with open(self.vu_file, 'w', newline='\n') as vu_result:
            with open(self.res_file, 'w', newline='\n') as res_result:
                vu_writer = csv.writer(vu_result)
                vu_writer.writerow(vu_headers)
                res_writer = csv.writer(res_result)
                res_writer.writerow(res_headers)
                for res in self.load_magr.results:
                    vu_writer.writerow(res.rowdict())
                    self.vu_res.append(res.rowdict())
                    for r in res:
                        res_writer.writerow(r.rowdict())
                        self.req_res.append(r.rowdict())

    def vu_graph_data(self):
        x_seq = [item[1] for item in self.vu_res]
        x_temp = [item[2] for item in self.vu_res]
        x_temp.sort()
        x_seq.extend(x_temp)
        y_seq = [item[0] for item in self.vu_res]
        y_temp = [y for y in range(max(y_seq) + 1)]
        y_temp.reverse()
        y_seq.extend(y_temp)
        return x_seq, y_seq


class Graph:
    def __init__(self, output_dir=config.OUTPUT_DIR):
        self.str_time = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
        self.result_dir = output_dir + config.PROJECT_NAME

    @staticmethod
    def graph_init():
        fig = figure(figsize=(8, 4))
        ax = fig.add_subplot(111)
        ax.grid(True, color='#666666')
        ax.set_xlabel('Elapsed Time In Test (secs)', size='x-small')
        xticks(size='x-small')
        yticks(size='x-small')
        return ax

    def res_graph(self, x, y):
        name = config.PROJECT_NAME + '_RES_' + self.str_time + '.png'
        save_to = self.result_dir + '/' + name
        ax = Graph.graph_init('RES Response')
        ax.plot(x, y, color='blue', linestyle='-', linewidth=1.0, marker='o',
                markeredgecolor='blue', markerfacecolor='yellow', markersize=2.0)
        axis(xmin=0, xmax=7, ymin=0, ymax=10)
        savefig(save_to)

    def conn_graph(self):
        name = config.PROJECT_NAME + '_CONN_' + self.str_time + '.png'
        save_to = self.result_dir + '/' + name

    def vu_graph(self, x, y):
        name = config.PROJECT_NAME + '_VU_' + self.str_time + '.png'
        save_to = self.result_dir + '/' + name
        ax = Graph.graph_init()
        ax.set_ylabel('VU Number', size='x-small')
        ax.set_title('Running VUsers', size='medium')
        ax.plot(x, y, color='blue', linestyle='-', linewidth=1.0, marker='o',
                markeredgecolor='blue', markerfacecolor='yellow', markersize=2.0)
        axis(xmax=math.ceil(max(x) * 1.2), ymax=math.ceil(max(y) * 1.2))
        savefig(save_to)

    def tp_graph(self):
        name = config.PROJECT_NAME + '_TP_' + self.str_time + '.png'
        save_to = self.result_dir + '/' + name


reqconfig = RequestsConfig()
reqs = reqconfig.get_request()
workload = WorkLoad(config.RAMPUP, config.INTERVAL, config.VUS)
t = LoadMagr(workload)
for req in reqs:
    t.add_req(req)
t.start()
time.sleep(config.DURATION)
t.stop()
if config.GENERATE_RESULTS:
    results = CollectCSVResults(t)
    results.generate_result()
    x_seq, y_seq = results.vu_graph_data()
    g = Graph()
    g.vu_graph(x_seq, y_seq)

