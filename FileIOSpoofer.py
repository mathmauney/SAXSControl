"""A file for testing real-time generation of data"""
import csv
import time

INFILE = "Elveflow/responsetime_noresist_01_15ul.txt"
OUTFILE = "Elveflow/temp.txt"
TIME_INTERVAL = 0.2 # in s

if __name__ == '__main__':
    with open(INFILE, 'r', newline='') as fr:
        reader = csv.reader(fr, delimiter='\t')
        with open(OUTFILE, 'w', newline='') as fw:
            writer = csv.writer(fw, delimiter='\t')
            i = 0
            for row in reader:
                writer.writerow(row)
                fw.flush()
                print(i)
                i += 1
                time.sleep(TIME_INTERVAL)
