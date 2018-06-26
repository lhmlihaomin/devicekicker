import requests
import json
import threading
import datetime
import time

class JmxReader(threading.Thread):
    def __init__(self, url):
        threading.Thread.__init__(self)
        self.url = url
        self.device_num = None

    def run(self):
        response = requests.get(self.url)
        result = json.loads(response.text)
        result = result['value']['stat.onlineDeviceNum']['count']
        self.device_num = int(result)
        return True


url_format = "http://{IP}:8778/jolokia/read/connector:name=StatJmx/stat"

with open('connectors.json', 'r') as fp:
    txt = fp.read()
    connectors = json.loads(txt)


with open('output.csv', 'w') as fp:
    for name, ip in connectors:
        fp.write(", "+name)
    fp.write("\r\n")


for i in range(20):
    print "Performing run {0} ...".format(i)
    readers = []
    for name, ip in connectors:
        url = url_format.format(IP=ip)
        reader = JmxReader(url)
        readers.append(reader)
    for reader in readers:
        reader.start()
    for reader in readers:
        reader.join()
    with open('output.csv', 'a') as fp: 
        fp.write(
            datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")+", "
        )
        for reader in readers:
            fp.write(str(reader.device_num) + ", ")
        fp.write("\r\n")
    
    print "Sleep 60 ..." 
    time.sleep(60)
    
