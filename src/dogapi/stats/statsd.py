

import socket
from random import random


class StatsdAggregator(object):


    def __init__(self, host='localhost', port=9966):
        self.host = host
        self.port = port
        self.address = (self.host, self.port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def add_point(self, metric, tags, timestamp, value, metric_class, sample_rate=1):
        payload = '%s:%s|%s' % (metric, value, metric_class.stats_tag)
        if sample_rate != 1:
            if sample_rate > random():
                return
            payload += '|@%s' % sample_rate
        if tags:
            payload += '|#' + ','.join(tags)
        self.socket.sendto(payload, self.address)
