__author__ = 'Rakesh Kumar'

from netaddr import IPNetwork

class Match():

    def __init__(self, match_json=None):

        self.in_port = "all"

        # Ethernet (Layer - 2 Fields)
        self.ethernet_type = "all"

        # IP Level (Layer - 3 Fields)
        self.src_ip_addr = "all"
        self.dst_ip_addr = "all"
        self.ip_protocol = "all"

        # Application (Layer-4 Fields)

        # TCP
        self.tcp_destination_port = "all"
        self.tcp_source_port = "all"

        # UDP
        self.udp_destination_port = "all"
        self.udp_source_port = "all"

        if match_json:
            self.populate_with_match_json(match_json)

    def populate_with_match_json(self, match_json):

        for match_field in match_json:

            if match_field == 'in-port':
                self.in_port = match_json[match_field]

            elif match_field == "ethernet-match":
                if "ethernet-type" in match_json[match_field]:
                    self.ethernet_type = match_json[match_field]["ethernet-type"]["type"]

            elif match_field == 'ipv4-destination':
                self.dst_ip_addr = IPNetwork(match_json[match_field])

            elif match_field == 'ipv4-source':
                self.src_ip_addr = IPNetwork(match_json[match_field])

            elif match_field == "ip-match":
                if "ip-protocol" in match_json[match_field]:
                    self.ip_protocol = match_json[match_field]["ip-protocol"]

            elif match_field == "tcp-destination-port":
                self.tcp_destination_port = match_json[match_field]

            elif match_field == "tcp-source-port":
                self.tcp_source_port = match_json[match_field]

            elif match_field == "udp-destination-port":
                self.udp_destination_port = match_json[match_field]

            elif match_field == "udp-source-port":
                self.udp_source_port = match_json[match_field]


    def generate_match_json(self, match):

        if self.in_port and self.in_port != "all":
            match["in-port"] = self.in_port

        if self.ethernet_type and self.ethernet_type != "all":
            ethernet_match = {"ethernet-type": {"type": self.ethernet_type}}
            match["ethernet-match"] = ethernet_match

        if self.src_ip_addr and self.src_ip_addr != "all":
            match["ipv4-source"] = self.src_ip_addr

        if self.dst_ip_addr and self.dst_ip_addr != "all":
            match["ipv4-destination"] = self.dst_ip_addr

        if (self.tcp_destination_port and self.tcp_destination_port != "all") or \
                (self.tcp_source_port and self.tcp_source_port != "all"):
            self.ip_protocol = 6
            match["ip-match"] = {"ip-protocol": self.ip_protocol}

            if self.tcp_destination_port and self.tcp_destination_port != "all":
                match["tcp-destination-port"]= self.tcp_destination_port

            if self.tcp_source_port and self.tcp_source_port != "all":
                match["tcp-source-port"] = self.tcp_source_port

        if (self.udp_destination_port and self.udp_destination_port != "all") or \
                (self.udp_source_port and self.udp_source_port != "all"):
            self.ip_protocol = 17
            match["ip-match"] = {"ip-protocol": self.ip_protocol}

            if self.udp_destination_port and self.udp_destination_port != "all":
                match["udp-destination-port"]= self.udp_destination_port

            if self.udp_source_port and self.udp_source_port != "all":
                match["udp-source-port"] = self.udp_source_port

        return match

    '''
    Return the match object containing the intersection of self and in_match,
        If the intersection is empty, return None
    '''

    def intersect(self, in_match):

        match_intersection = Match()

        if self.in_port == "all":
            match_intersection.in_port = in_match.in_port
        elif in_match.in_port == "all":
            match_intersection.in_port = self.in_port
        elif self.in_port == in_match.in_port:
            match_intersection.in_port = in_match.in_port
        else:
            match_intersection.in_port = None

        if self.ethernet_type == "all":
            match_intersection.ethernet_type = in_match.ethernet_type
        elif in_match.ethernet_type == "all":
            match_intersection.ethernet_type = self.ethernet_type
        elif self.ethernet_type == in_match.ethernet_type:
            match_intersection.ethernet_type = in_match.ethernet_type
        else:
            match_intersection.ethernet_type = None

        # TODO: Handle masks

        if self.src_ip_addr == "all":
            match_intersection.src_ip_addr = in_match.src_ip_addr
        elif in_match.src_ip_addr == "all":
            match_intersection.src_ip_addr = self.src_ip_addr
        elif in_match.src_ip_addr in self.src_ip_addr:
            match_intersection.src_ip_addr = in_match.src_ip_addr
        else:
            match_intersection.src_ip_addr = None

        if self.dst_ip_addr == "all":
            match_intersection.dst_ip_addr = in_match.dst_ip_addr
        elif in_match.dst_ip_addr == "all":
            match_intersection.dst_ip_addr = self.dst_ip_addr
        elif in_match.dst_ip_addr in self.dst_ip_addr:
            match_intersection.dst_ip_addr = in_match.dst_ip_addr
        else:
            match_intersection.dst_ip_addr = None

        if self.ip_protocol == "all":
            match_intersection.ip_protocol = in_match.ip_protocol
        elif in_match.ip_protocol == "all":
            match_intersection.ip_protocol = self.ip_protocol
        elif self.ip_protocol == in_match.ip_protocol:
            match_intersection.ip_protocol = in_match.ip_protocol
        else:
            match_intersection.ip_protocol = None

        if self.tcp_destination_port == "all":
            match_intersection.tcp_destination_port = in_match.tcp_destination_port
        elif in_match.tcp_destination_port == "all":
            match_intersection.tcp_destination_port = self.tcp_destination_port
        elif self.tcp_destination_port == in_match.tcp_destination_port:
            match_intersection.tcp_destination_port = in_match.tcp_destination_port
        else:
            match_intersection.tcp_destination_port = None

        if self.tcp_source_port == "all":
            match_intersection.tcp_source_port = in_match.tcp_source_port
        elif in_match.tcp_source_port == "all":
            match_intersection.tcp_source_port = self.tcp_source_port
        elif self.tcp_source_port == in_match.tcp_source_port:
            match_intersection.tcp_source_port = in_match.tcp_source_port
        else:
            match_intersection.tcp_source_port = None

        if self.udp_destination_port == "all":
            match_intersection.udp_destination_port = in_match.udp_destination_port
        elif in_match.udp_destination_port == "all":
            match_intersection.udp_destination_port = self.udp_destination_port
        elif self.udp_destination_port == in_match.udp_destination_port:
            match_intersection.udp_destination_port = in_match.udp_destination_port
        else:
            match_intersection.udp_destination_port = None

        if self.udp_source_port == "all":
            match_intersection.udp_source_port = in_match.udp_source_port
        elif in_match.udp_source_port == "all":
            match_intersection.udp_source_port = self.udp_source_port
        elif self.udp_source_port == in_match.udp_source_port:
            match_intersection.udp_source_port = in_match.udp_source_port
        else:
            match_intersection.udp_source_port = None

        if match_intersection.in_port and \
            match_intersection.ethernet_type and \
            match_intersection.src_ip_addr and \
            match_intersection.dst_ip_addr and \
            match_intersection.ip_protocol and \
            match_intersection.tcp_destination_port and \
            match_intersection.tcp_source_port and \
            match_intersection.udp_destination_port and \
            match_intersection.udp_source_port:

            return match_intersection
        else:
            return None