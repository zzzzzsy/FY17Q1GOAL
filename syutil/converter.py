import codecs

with open('D:/04_Projects/10_Harley/Test Data/JPN/001LoadFile/JPN_CATEGORY_MASTER_20160711_test.csv', 'r+') as f:
    line = f.readline().encode('utf-8')
    print(line)
