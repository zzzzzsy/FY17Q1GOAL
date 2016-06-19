from config import config
import time
import csv


class CollectResults:
    def __init__(self, load_magr, output_dir=config.OUTPUT_DIR):
        self.load_magr = load_magr
        self.output_dir = output_dir
        strfile = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
        self.vu_file = self.output_dir + 'vu_results_' + strfile + '.csv'
        self.res_file = self.output_dir + 'res_results_' + strfile + '.csv'

    def generate_result(self):
        for res in self.load_magr.results:
            with open(self.vu_file, 'wb') as vu_result:
                vu_writer = csv.writer(vu_result)
                vu_writer.writerow(res)


with open('D:/eggs.csv', 'w', newline='') as csvfile:
    spamwriter = csv.writer(csvfile
                            )
    print(type(['1']))
    spamwriter.writerow(['1'] * 5)
    spamwriter.writerow(['Spam', 'Lovely Spam', 'Wonderful Spam'])