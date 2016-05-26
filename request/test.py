import urllib.request
url = 'http://www.baidu.com'
user_agent = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
values = {
    'act': 'login',
    'login[email]': 'yzhang@i9i8.com',
    'login[password]': '123456'
}
print(values)
data = urllib.parse.urlencode(values).encode('utf-8')
print(data)
print(type(data))
req = urllib.request.Request(url, data)
req.add_header('Referer', 'http://www.python.org/')
response = urllib.request.urlopen(req)
print(response.getcode())
