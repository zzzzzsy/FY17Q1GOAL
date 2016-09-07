# l = [0.01, 0.022, 0.035, 0.004, 0.02, 0.0111, 0.03]
# for i in range(len(l)):
#     for j in range(i, len(l)):
#         if l[i] > l[j]:
#             temp = l[j]
#             l[j] = l[i]
#             l[i] = temp
#
# l = [item*1000 for item in l]
# print(l)

# import codecs
# import encodings.shift_jis
#
# with open('D:/04_Projects/10_Harley/Test Data/JPN/001LoadFile/JPN_CATEGORY_MASTER_20160711_test.csv', 'rb') as f:
#     while f.readline():
#         line = f.readline().decode('utf-8','ignore')
#         print(line)


# test = [([1, 2, 5], [641.612, 640.181, 594.953]), ([4, 6, 10, 12, 16, 19], [1259.261, 3474.194, 7481.99, 9396.857, 13590.517, 15819.041])]
# print(type(test))
# print(test[1][1])

import requests
import urllib3
import logging

# urllib3.disable_warnings()
logging.captureWarnings(True)

resp = requests.get('https://tap.acxiom.com.cn/public/', verify=False)
# print(resp.content)
