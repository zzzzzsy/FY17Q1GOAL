from threading import Thread
from config import config
from pylab import *
import time
import requests
import csv
import os
import math
import logging
import xml.etree.cElementTree as ET
from operator import itemgetter

REQ_NAMES = []
COLORS = ['blue', 'red', 'green', 'yellow', 'black', 'cyan', 'magenta']
logging.captureWarnings(True)


class RequestsConfig:
    def __init__(self):
        self.req_list = []

    def get_request_from_xml(self, path=config.REQ_XML):
        xml = ET.parse(path)
        root = xml.getroot()
        request = root.findall('request')
        for r in request:
            req = Request(r.get('trans_name'), r.find('url').text, eval(r.find('headers').text),
                          r.find('method').text, r.find('paras').text, r.find('data').text,
                          r.find('json').text, r.find('verify').text, r.find('cert').text)
            REQ_NAMES.append(r.get('trans_name'))
            # print(req.name, req.url, req.headers, req.method, req.para, req.json, req.verify, req.cert)
            self.req_list.append(req)
        return self.req_list


class Request:
    def __init__(self, name, url, headers=None, method='GET', para=None, data=None, json=None, verify=False, cert=None):
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
        self.json = json
        self.data = data
        if para:
            self.para = para.encode(config.ENCODING)
        if json:
            # pending test
            # no testable case
            json = json.replace('\r\n', '\\r\\n')
            self.json = json.encode(config.ENCODING)
        if data:
            self.data = data.encode(config.ENCODING)
        self.verify = verify
        self.cert = cert

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
            kwargs = {'params': req.para, 'data': req.data, 'json': req.json, 'headers': req.headers,
                      'timeout': config.REQ_TIMEOUT, 'verify': req.verify, 'cert': req.cert}
            start_time = time.clock()
            resp = requests.request(req.method, req.url, **kwargs)
            conn_end_time = time.clock()
            content = resp.content
            end_time = time.clock()
            # print(resp.text)
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
        vu_start_time = time.clock() + config.RAMPUP / config.VUS
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
                                 start_time, conn_end_time,
                                 end_time, self.id)
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
    def __init__(self, name, code, reason, count, res_bytes, start_time, conn_end_time, res_end_time, vu_id):
        self.name = name
        self.code = code
        self.reason = reason
        self.count = count
        self.bytes = res_bytes
        self.start_time = start_time
        self.conn_end_time = conn_end_time
        self.res_end_time = res_end_time
        self.vu_id = vu_id
        self.res_lst = []

    def __str__(self):
        return 'VU %d Request %d Name %s: Code: %d, Desc: %s, Bytes: %d, ' \
               'Start time: %s, Connection end time: %s, Res end time: %s' \
               'Conn elapsed time: %s, Res elapsed time: %s' % (
                   self.vu_id, self.count, self.name, self.code, self.reason, self.bytes,
                   self.start_time, self.conn_end_time, self.res_end_time,
                   str(self.conn_end_time - self.start_time), str(self.res_end_time - self.start_time))

    def rowdict(self):
        self.res_lst.append(self.vu_id)
        self.res_lst.append(self.count)
        self.res_lst.append(self.name)
        self.res_lst.append(self.code)
        self.res_lst.append(self.reason)
        self.res_lst.append(self.bytes)
        self.res_lst.append(self.start_time)
        self.res_lst.append(self.conn_end_time)
        self.res_lst.append(self.res_end_time)
        self.res_lst.append(self.conn_end_time - self.start_time)
        self.res_lst.append(self.res_end_time - self.start_time)
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
        res_headers = ['vu', 'req id', 'req name', 'res code', 'desc', 'bytes',
                       'start time', 'conn end time', 'res end time', 'conn elapsed time', 'res elapsed time']

        with open(self.vu_file, 'w', newline='\n') as vu_result:
            with open(self.res_file, 'w', newline='\n') as res_result:
                vu_writer = csv.writer(vu_result)
                vu_writer.writerow(vu_headers)
                res_writer = csv.writer(res_result)
                res_writer.writerow(res_headers)
                for res in self.load_magr.results:
                    vu_tmp = res.rowdict()
                    vu_writer.writerow(vu_tmp)
                    self.vu_res.append(vu_tmp)
                    for r in res:
                        res_tmp = r.rowdict()
                        res_writer.writerow(res_tmp)
                        self.req_res.append(res_tmp)

        if config.VU_GRAPH_ENABLE:
            x, y = self.vu_graph_data()
            g = Graph()
            g.vu_graph(x, y)
        if config.RES_GRAPH_ENABLE:
            res_data = self.res_graph_data(8, 10)
            g = Graph()
            g.res_graph(res_data)
        if config.CONN_GRAPH_ENABLE:
            res_data = self.res_graph_data(7, 9)
            g = Graph()
            g.conn_graph(res_data)
        if config.TP_GRAPH_ENABLE:
            x, y = self.tp_graph_data()
            g = Graph()
            g.tp_graph(x, y)

    def vu_graph_data(self):
        x_seq = [item[1] for item in self.vu_res]
        x_temp = [item[2] for item in self.vu_res]
        x_temp.sort()
        x_temp.insert(0, config.DURATION)
        x_seq.extend(x_temp)
        y_seq = [(item[0] + 1) for item in self.vu_res]
        y_temp = [y for y in range(max(y_seq) + 1)]
        y_temp.reverse()
        y_seq.extend(y_temp)
        x_seq.insert(0, 0)
        y_seq.insert(0, 0)
        return x_seq, y_seq

    def tp_graph_data(self):
        x_temp = [item[8] for item in self.req_res]
        x_seq = [x for x in range(math.ceil(max(x_temp)) + 2)]
        x_temp.sort()
        y_seq = [0]
        count = 0
        for i in x_seq:
            f = True
            for c in x_temp:
                if c <= i:
                    continue
                elif i < c < i + 1:
                    count += 1
                    f = True
                else:
                    if f:
                        y_seq.append(count)
                        f = False
                    count = 0
        y_seq.append(count)
        y_seq.append(0)
        return x_seq, y_seq

    # index m for end time
    # index n for elapsed time
    def res_graph_data(self, m, n):
        temp = [list() for x in range(len(REQ_NAMES))]
        res_data = []

        for row in self.req_res:
            if 0 < int(row[3]) < 400:
                for name in REQ_NAMES:
                    if row[2] == name:
                        temp[REQ_NAMES.index(name)].append(row)
        for reqs in temp:
            y_seq = []
            x_seq = []
            if reqs is not None:
                # xmax = 0
                # t = [item[m] for item in reqs]
                # v = [item[n] for item in reqs]
                # if len(t) > 0:
                #     for i in range(len(t)):
                #         for j in range(i, len(t)):
                #             if t[i] > t[j]:
                #                 temp = t[j]
                #                 t[j] = t[i]
                #                 t[i] = temp
                #                 temp = v[j]
                #                 v[j] = v[i]
                #                 v[i] = temp
                #     xmax = t[-1]
                sortedlist = sorted(reqs, key=itemgetter(m))
                t = [item[m] for item in sortedlist]
                v = [item[n] for item in sortedlist]
                xmax = t[-1]
            x_seq_temp = [i for i in range(0, math.ceil(xmax + config.RES_X_INTERVAL), config.RES_X_INTERVAL)]
            count = 0
            s = 0
            for x in x_seq_temp:
                if x == 0:
                    continue
                for i in range(len(t)):
                    if x - config.RES_X_INTERVAL < t[i] <= x:
                        count += 1
                        s += v[i]
                    else:
                        if s != 0:
                            if count != 0:
                                y_seq.append(s / count)
                                count = 0
                                s = 0
                                x_seq.append(x)
                        else:
                            continue
            if count != 0:
                y_seq.append(s / count)
                x_seq.append(x_seq_temp[-1])
            y_seq = [round(item * 1000, 3) for item in y_seq]
            res_data.append((x_seq, y_seq))
        return res_data


class Graph:
    def __init__(self, output_dir=config.OUTPUT_DIR):
        self.str_time = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
        self.result_dir = output_dir + config.PROJECT_NAME

    @staticmethod
    def graph_init():
        fig = figure(figsize=(10, 4))
        ax = fig.add_subplot(111)
        ax.grid(True, color='#666666')
        xticks(size='x-small')
        yticks(size='x-small')
        return ax

    def res_graph(self, res_data):
        xmin = 0
        xmax = 0
        # pls = []
        ax = Graph.graph_init()
        color = 0
        for res in res_data:
            x = res[0]
            y = res[1]
            ax.set_xlabel('Elapsed Time In Test (secs)', size='x-small')
            ax.set_ylabel('Avg Res Time (millisecond)', size='x-small')
            ax.set_title('Response Time', size='medium')
            ax.plot(x, y, color=COLORS[color], linestyle='-', linewidth=1.0, marker='o',
                    markeredgecolor=COLORS[color], markerfacecolor='yellow', markersize=2.0)
            xmin = min(x) if xmin > min(x) else xmin
            xmax = max(x) if max(x) > xmax else xmax
            color += 1
        # ax.legend()
        axis(xmin=xmin, xmax=xmax)
        name = config.PROJECT_NAME + '_RES_' + self.str_time + '.png'
        save_to = self.result_dir + '/' + name
        savefig(save_to)
        close()

    def conn_graph(self, res_data):
        xmin = 0
        xmax = 0
        # pls = []
        ax = Graph.graph_init()
        color = 0
        for res in res_data:
            x = res[0]
            y = res[1]
            ax.set_xlabel('Elapsed Time In Test (secs)', size='x-small')
            ax.set_ylabel('Conn Time (millisecond)', size='x-small')
            ax.set_title('Connection Time', size='medium')
            ax.plot(x, y, color=COLORS[color], linestyle='-', linewidth=1.0, marker='o',
                    markeredgecolor=COLORS[color], markerfacecolor='yellow', markersize=2.0)
            xmin = min(x) if xmin > min(x) else xmin
            xmax = max(x) if max(x) > xmax else xmax
            color += 1
        # ax.legend()
        axis(xmin=xmin, xmax=xmax)
        name = config.PROJECT_NAME + '_CONN_' + self.str_time + '.png'
        save_to = self.result_dir + '/' + name
        savefig(save_to)
        close()

    def vu_graph(self, x, y):
        name = config.PROJECT_NAME + '_VU_' + self.str_time + '.png'
        save_to = self.result_dir + '/' + name
        ax = Graph.graph_init()
        ax.set_xlabel('Elapsed Time In Test (secs)', size='x-small')
        ax.set_ylabel('VU Number', size='x-small')
        ax.set_title('Running VUsers', size='medium')
        ax.plot(x, y, color='blue', linestyle='-', linewidth=1.0, marker='o',
                markeredgecolor='blue', markerfacecolor='yellow', markersize=2.0)
        axis(xmax=math.ceil(max(x) * 1.2), ymax=math.ceil(max(y) * 1.2))
        savefig(save_to)
        close()

    def tp_graph(self, x, y):
        name = config.PROJECT_NAME + '_TP_' + self.str_time + '.png'
        save_to = self.result_dir + '/' + name
        ax = Graph.graph_init()
        ax.set_xlabel('Elapsed Time In Test (secs)', size='x-small')
        ax.set_ylabel('Hits', size='x-small')
        ax.set_title('Hits per Sec', size='medium')
        ax.plot(x, y, color='blue', linestyle='-', linewidth=1.0, marker='o',
                markeredgecolor='blue', markerfacecolor='yellow', markersize=2.0)
        axis(xmin=min(x), xmax=max(x))
        savefig(save_to)
        close()


reqconfig = RequestsConfig()
reqs = reqconfig.get_request_from_xml()
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

# reqconfig = RequestsConfig()
# reqs = reqconfig.get_request_from_xml()
# req = reqs[0]
#
# kwargs = {'params': req.para, 'data': req.data, 'json': req.json, 'headers': req.headers,
#           'timeout': config.REQ_TIMEOUT, 'verify': req.verify, 'cert': req.cert}
#
# resp = requests.request(req.method, req.url, **kwargs)
#
# print(resp.text)
