__author__ = 'Rakesh Kumar'

from netaddr import IPNetwork


class Match():

    def __init__(self):

        self.src_ip_addr = None
        self.dst_ip_addr = None
        self.in_port = None
