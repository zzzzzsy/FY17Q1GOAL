from urllib.request import (Request, urlopen)
from configparser import ConfigParser
from urllib.parse import urlencode


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


test = get_request()
for t in test:
    res = urlopen(t)
    print(res.read())
