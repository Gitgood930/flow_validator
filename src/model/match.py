__author__ = 'Rakesh Kumar'


import sys

from netaddr import IPNetwork
from UserDict import DictMixin
from external.intervaltree import Interval, IntervalTree

field_names = ["in_port",
              "ethernet_type",
              "ethernet_source",
              "ethernet_destination",
              "src_ip_addr",
              "dst_ip_addr",
              "ip_protocol",
              "tcp_destination_port",
              "tcp_source_port",
              "udp_destination_port",
              "udp_source_port",
              "vlan_id",
              "has_vlan_tag"]

class MatchElement(DictMixin):

    def __init__(self, match_json=None, flow=None):

        self.match_elements = {}

        if match_json is not None and flow:
            self.add_element_from_match_json(match_json, flow)

    def __getitem__(self, item):
        return self.match_elements[item]

    def __setitem__(self, key, value):
        self.match_elements[key] = value

    def set_match_field_element(self, key, value, tag=None):
        self.match_elements[key] = Interval(value, value + 1, tag)

    def __delitem__(self, key):
        del self.match_elements[key]

    def keys(self):
        return self.match_elements.keys()

    def get_matched_tree(self, tree, iv):
    
        matched_tree = IntervalTree()
        for matched_interval in tree.search(iv.begin, iv.end):
    
            #Take the smaller interval of the two and put it in the matched_tree
            if matched_interval.contains_point(iv):
                matched_tree.add(iv)
            elif iv.contains_point(matched_interval):
                matched_tree.add(matched_interval)
    
        return matched_tree

    def intersect(self, in_match):

        match_intersection = Match()

        for field_name in self.match_elements:
            match_intersection[field_name] = self.get_matched_tree(in_match[field_name], self[field_name])

        return match_intersection

    def complement_match(self, tag):
        match_complement = Match(tag, init_wildcard=True)

        for field_name in self.match_elements:
            
            #If the field is not a wildcard, then chop it from the wildcard initialized Match
            if not (self[field_name].begin == 0 and self[field_name].end == sys.maxsize):
                match_complement[field_name].chop(self[field_name].begin, self[field_name].end)

        return match_complement

    def add_element_from_match_json(self, match_json, flow):

        for field_name in field_names:

            try:
                if field_name == "in_port":

                    self[field_name] = Interval(int(match_json["in-port"]),
                                                 int(match_json["in-port"]) + 1,
                                                 flow)

                elif field_name == "ethernet_type":
                    self[field_name] = Interval(int(match_json["ethernet-match"]["ethernet-type"]["type"]),
                                                 int(match_json["ethernet-match"]["ethernet-type"]["type"]) + 1,
                                                 flow)

                elif field_name == "ethernet_source":
                    mac_int = int(match_json["ethernet-match"]["ethernet-source"]["address"].replace(":", ""), 16)
                    self[field_name] = Interval(mac_int, mac_int + 1, flow)

                elif field_name == "ethernet_destination":
                    mac_int = int(match_json["ethernet-match"]["ethernet-destination"]["address"].replace(":", ""), 16)
                    self[field_name] = Interval(mac_int, mac_int + 1, flow)

                #TODO: Add graceful handling of IP addresses
                elif field_name == "src_ip_addr":
                    self[field_name] = Interval(IPNetwork(match_json["src_ip_addr"]))

                elif field_name == "dst_ip_addr":
                    self[field_name] = Interval(IPNetwork(match_json["dst_ip_addr"]))

                elif field_name == "ip_protocol":
                    self[field_name] = Interval(int(match_json["ip-match"]["ip-protocol"]),
                                                 int(match_json["ip-match"]["ip-protocol"]) + 1,
                                                 flow)

                elif field_name == "tcp_destination_port":
                    self[field_name] = Interval(int(match_json["tcp-destination-port"]),
                                                 int(match_json["tcp-destination-port"]) + 1,
                                                 flow)

                elif field_name == "tcp_source_port":
                    self[field_name] = Interval(int(match_json["tcp-source-port"]),
                                                 int(match_json["tcp-source-port"]) + 1,
                                                 flow)

                elif field_name == "udp_destination_port":
                    self[field_name] = Interval(int(match_json["udp-destination-port"]),
                                                 int(match_json["udp-destination-port"]) + 1,
                                                 flow)
                elif field_name == "udp_source_port":
                    self[field_name] = Interval(int(match_json["udp-source-port"]),
                                                 int(match_json["udp-source-port"]) + 1,
                                                 flow)
                elif field_name == "vlan_id":
                    self["vlan_id"] = Interval(int(match_json["vlan-match"]["vlan-id"]["vlan-id"]),
                                                int(match_json["vlan-match"]["vlan-id"]["vlan-id"]) + 1,
                                                flow)

                    self["has_vlan_tag"] = Interval(1, 1 + 1, flow)

            except KeyError:
                self[field_name] = Interval(0, sys.maxsize, flow)

                # Special case
                if field_name == "vlan_id":
                    self["has_vlan_tag"] = Interval(0, sys.maxsize, flow)

                continue

    def generate_match_json(self, match):

        if "in_port" in self and self["in_port"].end != sys.maxsize:
            match["in-port"] = self["in_port"].begin

        ethernet_match = {}

        if "ethernet_type" in self and self["ethernet_type"].end != sys.maxsize:
            ethernet_match["ethernet-type"] = {"type": self["ethernet_type"].begin}

        if "ethernet_source" in self and self["ethernet_source"].end != sys.maxsize:

            mac_int = self["ethernet_source"].begin
            mac_hex_str = hex(mac_int)[2:]
            mac_hex_str = unicode(':'.join(s.encode('hex') for s in mac_hex_str.decode('hex')))

            ethernet_match["ethernet-source"] = {"address": mac_hex_str}

        if "ethernet_destination" in self and self["ethernet_destination"].end != sys.maxsize:

            mac_int = self["ethernet_destination"].begin
            mac_hex_str = hex(mac_int)[2:]
            mac_hex_str = unicode(':'.join(s.encode('hex') for s in mac_hex_str.decode('hex')))

            ethernet_match["ethernet-destination"] = {"address": mac_hex_str}

        match["ethernet-match"] = ethernet_match

        if "src_ip_addr" in self and self["src_ip_addr"].end != sys.maxsize:
            match["ipv4-source"] = self["src_ip_addr"].begin

        if "dst_ip_addr" in self and self["dst_ip_addr"].end != sys.maxsize:
            match["ipv4-destination"] = self["dst_ip_addr"].begin

        if ("tcp_destination_port" in self and self["tcp_destination_port"].end != sys.maxsize) or \
                ("tcp_source_port" in self and self["tcp_source_port"].end != sys.maxsize):
            self["ip_protocol"].begin = 6
            match["ip-match"] = {"ip-protocol": self["ip_protocol"].begin}

            if "tcp_destination_port" in self and self["tcp_destination_port"].end != sys.maxsize:
                match["tcp-destination-port"] = self["tcp_destination_port"].begin

            if "tcp_source_port" in self and self["tcp_source_port"].end != sys.maxsize:
                match["tcp-source-port"] = self["tcp_source_port"].begin

        if ("udp_destination_port" in self and self["udp_destination_port"].end != sys.maxsize) or \
                ("udp_source_port" in self and self["udp_source_port"].end != sys.maxsize):
            self["ip_protocol"].begin = 17
            match["ip-match"] = {"ip-protocol": self["ip_protocol"].begin}

            if "udp_destination_port" in self and self["udp_destination_port"].end != sys.maxsize:
                match["udp-destination-port"]= self["udp_destination_port"].begin

            if "udp_source_port" in self and self["udp_source_port"].end != sys.maxsize:
                match["udp-source-port"] = self["udp_source_port"].begin

        if "vlan_id" in self and self["vlan_id"].end != sys.maxsize:
            vlan_match = {}
            vlan_match["vlan-id"] = {"vlan-id": self["vlan_id"].begin, "vlan-id-present": True}
            match["vlan-match"] = vlan_match

        return match

class Match(DictMixin):

    def __str__(self):
        ret_str = "Match: "
        for f in self.match_fields:
            ret_str +=  f + " " + str(self.match_fields[f])

        return ret_str

    def __init__(self, tag=None, match_element_list=[], init_wildcard=False):

        self.match_fields = {}
        self.tag = tag

        for field_name in field_names:
            self[field_name] = IntervalTree()

            if match_element_list:
                for match_element in match_element_list:
                    self[field_name].add(match_element[field_name])

            elif init_wildcard:
                self[field_name].add(Interval(0, sys.maxsize, tag))

    def __delitem__(self, key):
        del self.match_fields[key]

    def keys(self):
        return self.match_fields.keys()

    def __getitem__(self, item):
        return self.match_fields[item]

    def __setitem__(self, key, value):
        self.match_fields[key] = value

    def has_empty_field(self):
        for match_field in self.keys():
            if not self[match_field].items():
                return True

        return False

    def set_field(self, key, value):
        self[key] = IntervalTree()
        self[key].add(Interval(value, value + 1, self.tag))

    #TODO: away with the ugly hacks...
    def get_field(self, key):
        field = self.match_fields[key]

        # If the field is not a wildcard, return a value, otherwise none
        items = field.items()
        item = None
        if items:
            item = items.pop()

        if item.end != sys.maxsize:
            return item.begin
        else:
             return None

    def set_fields_with_match_json(self, match_json):

        for match_field in match_json:

            if match_field == 'in-port':
                self.set_field("in_port", int(match_json[match_field]))

            elif match_field == "ethernet-match":
                if "ethernet-type" in match_json[match_field]:
                    self.set_field("ethernet_type", int(match_json[match_field]["ethernet-type"]["type"]))

                if "ethernet-source" in match_json[match_field]:
                    self.set_field("ethernet_source", int(match_json[match_field]["ethernet-source"]["address"]))

                if "ethernet-destination" in match_json[match_field]:
                    self.set_field("ethernet_destination", int(match_json[match_field]["ethernet-destination"]["address"]))

            elif match_field == 'ipv4-destination':
                self.set_field("dst_ip_addr", IPNetwork(match_json[match_field]))

            elif match_field == 'ipv4-source':
                self.set_field("src_ip_addr", IPNetwork(match_json[match_field]))

            elif match_field == "ip-match":
                if "ip-protocol" in match_json[match_field]:
                    self.set_field("ip_protocol", int(match_json[match_field]["ip-protocol"]))

            elif match_field == "tcp-destination-port":
                self.set_field("tcp_destination_port", int(match_json[match_field]))

            elif match_field == "tcp-source-port":
                self.set_field("tcp_source_port", int(match_json[match_field]))

            elif match_field == "udp-destination-port":
                self.set_field("udp_destination_port", int(match_json[match_field]))

            elif match_field == "udp-source-port":
                self.set_field("udp_source_port", int(match_json[match_field]))

            elif match_field == "vlan-match":
                if "vlan-id" in match_json[match_field]:
                    self.set_field("vlan_id", int(match_json[match_field]["vlan-id"]["vlan-id"]))
                    self.set_field("has_vlan_tag", int(True))

    def get_matched_tree(self, tree1, tree2):

        matched_tree = IntervalTree()
        for iv in tree1:
            for matched_iv in tree2.search(iv.begin, iv.end):

                #Take the smaller interval of the two and put it in the matched_tree
                if matched_iv.contains_interval(iv):
                    matched_tree.add(iv)
                elif iv.contains_interval(matched_iv):
                    matched_tree.add(matched_iv)

        return matched_tree

    def intersect(self, in_match):

        match_intersection = Match()

        for field_name in self.match_fields:
            match_intersection[field_name] = self.get_matched_tree(in_match[field_name], self[field_name])

        return match_intersection

def main():
    m1 = Match()
    print m1

    m2 = Match()
    m3 = m1.intersect(m2)
    print m3

if __name__ == "__main__":
    main()
