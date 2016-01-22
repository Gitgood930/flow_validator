__author__ = 'Rakesh Kumar'


import json
import time
import os
import httplib2

from functools import partial

from mininet.topo import LinearTopo
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.node import OVSSwitch

from experiments.topologies.fat_tree import FatTree
from experiments.topologies.two_ring_topo import TwoRingTopo
from experiments.topologies.ring_topo import RingTopo
from experiments.topologies.ring_line_topo import RingLineTopo
from experiments.topologies.clos_topo import ClosTopo
from experiments.topologies.clique_topo import CliqueTopo

from synthesis.synthesize_dij_qos import SynthesizeQoS


class MininetMan():

    def __init__(self,
                 synthesis_scheme,
                 controller_port,
                 topo_name,
                 num_switches,
                 num_hosts_per_switch,
                 fanout=None,
                 core=None,
                 per_switch_links=None):

        self.net = None
        self.synthesis_scheme = synthesis_scheme

        self.num_switches = num_switches
        self.num_hosts_per_switch = num_hosts_per_switch
        self.fanout = fanout
        self.core = core
        self.controller_port = int(controller_port)

        self.topo_name = topo_name
        self.experiment_switches = None

        if self.topo_name == "ring":
            self.topo = RingTopo(self.num_switches, self.num_hosts_per_switch)
            self.experiment_switches = self.topo.switch_names
        elif self.topo_name == "linear":
            self.topo = LinearTopo(self.num_switches, self.num_hosts_per_switch)
        elif self.topo_name == "two_ring":
            self.topo = TwoRingTopo(self.num_switches, self.num_hosts_per_switch)
        elif self.topo_name == "fat_tree":
            self.topo = FatTree(self.num_switches, self.num_hosts_per_switch)
        elif self.topo_name == "ringline":
            self.topo = RingLineTopo(self.num_switches, self.num_hosts_per_switch)
        elif self.topo_name == "clostopo":
            self.topo = ClosTopo(self.fanout, self.core, self.num_hosts_per_switch)
            self.experiment_switches = self.topo.edge_switches.values()
        elif self.topo_name == "cliquetopo":
            self.topo = CliqueTopo(self.num_switches, self.num_hosts_per_switch, per_switch_links)
        else:
            raise Exception("Invalid, unknown topology type: " % topo_name)

        self.switch = partial(OVSSwitch, protocols='OpenFlow13')

        if self.num_switches and self.num_hosts_per_switch:
            self.mininet_configuration_name = self.synthesis_scheme + "_" + \
                                              self.topo_name + "_" + \
                                              str(self.num_switches) + "_" + \
                                              str(self.num_hosts_per_switch)
        elif self.fanout and self.core and self.num_hosts_per_switch:
            self.mininet_configuration_name = self.synthesis_scheme + "_" + \
                                              self.topo_name + "_" + \
                                              str(self.num_hosts_per_switch) + "_" + \
                                              str(self.fanout) + "_" + \
                                              str(self.core)

    def __del__(self):
        self.cleanup_mininet()

    def start_mininet(self):

        self.cleanup_mininet()

        self.net = Mininet(topo=self.topo,
                           cleanup=True,
                           autoStaticArp=True,
                           controller=lambda name: RemoteController(name, ip='127.0.0.1', port=self.controller_port),
                           switch=self.switch)

        self.net.start()

    def cleanup_mininet(self):

        if self.net:
            print "Mininet cleanup..."
            self.net.stop()

        os.system("sudo mn -c")

    def get_all_switch_hosts(self, switch_id):

        p = self.topo.ports

        for node in p:

            # Only look for this switch's hosts
            if node != switch_id:
                continue

            for switch_port in p[node]:
                dst_list = p[node][switch_port]
                dst_node = dst_list[0]
                if dst_node.startswith("h"):
                    yield self.net.get(dst_node)

    def get_experiment_switch_hosts(self, switch_id, experiment_switches):

        if switch_id in experiment_switches:
            for i in range(0, self.num_hosts_per_switch):
                host_name = "h" + switch_id[1:] + str(i+1)
                yield self.net.get(host_name)
        else:
            return

    def _get_experiment_host_pair(self):

        for src_switch in self.experiment_switches:
            for dst_switch in self.experiment_switches:
                if src_switch == dst_switch:
                    continue

                # Assume one host per switch
                src_host = "h" + src_switch[1:] + "1"
                dst_host = "h" + dst_switch[1:] + "1"

                src_host_node = self.net.get(src_host)
                dst_host_node = self.net.get(dst_host)

                yield (src_host_node, dst_host_node)

    def _ping_host_pair(self, src_host, dst_host):
        hosts = [src_host, dst_host]
        ping_loss_rate = self.net.ping(hosts, '1')

        if ping_loss_rate < 100.0:
            return True
        else:
            return False

    def is_bi_connected_manual_ping_test(self, experiment_host_pairs_to_check=None):

        is_bi_connected= True

        if not experiment_host_pairs_to_check:
            experiment_host_pairs_to_check = list(self._get_experiment_host_pair())

        for (src_host, dst_host) in experiment_host_pairs_to_check:

            for edge in self.topo.g.edges():

                # Only try and break switch-switch edges
                if edge[0].startswith("h") or edge[1].startswith("h"):
                    continue
                else:

                    is_connected_before_failure = self._ping_host_pair(src_host, dst_host)
                    self.net.configLinkStatus(edge[0], edge[1], 'down')
                    is_connected_after_failure = self._ping_host_pair(src_host, dst_host)
                    self.net.configLinkStatus(edge[0], edge[1], 'up')
                    is_connected_after_restoration = self._ping_host_pair(src_host, dst_host)

                    if is_connected_before_failure != is_connected_after_failure:

                        cmd_output = src_host.cmd("ping -c 3 " + dst_host.IP())
                        print cmd_output
                        if cmd_output.find("0 received") != -1:
                            is_bi_connected = False
                            print "Got a problem with edge:", edge, " for src_host:", src_host, "dst_host:", dst_host

        return is_bi_connected

    def setup_mininet_with_ryu_qos(self, ng):

        def parse_iperf_output(iperf_output_string):
            data_lines =  iperf_output_string.split('\r\n')
            interesting_line_index = None
            for i in range(len(data_lines)):
                if data_lines[i].endswith('Server Report:'):
                    interesting_line_index = i + 1
            data_tokens =  data_lines[interesting_line_index].split()
            print "Transferred Rate:", data_tokens[7]
            print "Jitter:", data_tokens[9]

        def parse_ping_output(ping_output_string):

            data_lines =  ping_output_string.split('\r\n')
            interesting_line_index = None
            for i in range(len(data_lines)):
                if data_lines[i].startswith('5 packets transmitted'):
                    interesting_line_index = i + 1
            data_tokens =  data_lines[interesting_line_index].split()
            data_tokens =  data_tokens[3].split('/')
            print 'Min Delay:', data_tokens[0]
            print 'Avg Delay:', data_tokens[1]
            print 'Max Delay:', data_tokens[2]

        self.synthesis_dij = SynthesizeQoS(ng, master_switch=self.topo_name == "linear")
        last_hop_queue_rate = 5
        send_rates_to_try = ['1M', '2M', '3M', '4M', '5M', '6M']

        self.synthesis_dij.synthesize_all_node_pairs(last_hop_queue_rate)

        # Get all the nodes
        self.h1s1 = self.net.getNodeByName("h1s1")
        self.h1s2 = self.net.getNodeByName("h1s2")
        self.h2s1 = self.net.getNodeByName("h2s1")
        self.h2s2 = self.net.getNodeByName("h2s2")

        # Start the server at h1s1
        h1s1_output = self.h1s1.cmd("iperf -s -u -i 1 5001&")
        print h1s1_output

        iperf_output_dict = {}
        ping_output_dict = {}

        for rate in send_rates_to_try:
            self.h1s2.cmd("iperf -c " + self.h1s1.IP() + " -p 5001 -u -b " + rate + " -t 5&")
            time.sleep(1)
            ping_output_dict[rate] = self.h1s2.cmd("ping -c 5 " + self.h1s1.IP())
            time.sleep(3)
            iperf_output_dict[rate] = self.h1s2.read()

        # Parse the output for jitter and delay
        print "Last-Hop Queue Rate:", str(last_hop_queue_rate), "M"
        for rate in send_rates_to_try:
            print "Sending Rate:", rate

            parse_iperf_output(iperf_output_dict[rate])
            parse_ping_output(ping_output_dict[rate])

    def setup_mininet_with_ryu_router(self):

        # Get all the nodes
        self.h1 = self.net.getNodeByName("h1")
        self.h2 = self.net.getNodeByName("h2")
        self.h3 = self.net.getNodeByName("h3")

        self.h1.cmd("ip addr del 10.0.0.1/8 dev h1-eth0")
        self.h1.cmd("ip addr add 172.16.20.10/24 dev h1-eth0")
        self.h1.cmd("ip route add default via 172.16.20.1")

        self.h2.cmd("ip addr del 10.0.0.2/8 dev h2-eth0")
        self.h2.cmd("ip addr add 172.16.10.10/24 dev h2-eth0")
        self.h2.cmd("ip route add default via 172.16.10.1")

        self.h3.cmd("ip addr del 10.0.0.3/8 dev h3-eth0")
        self.h3.cmd("ip addr add 192.168.30.10/24 dev h3-eth0")
        self.h3.cmd("ip route add default via 192.168.30.1")

        self.h = httplib2.Http(".cache")
        self.baseUrl = "http://localhost:8080"

        router_conf_requests = []
        router_conf_requests.append(({"address": "172.16.20.1/24"},
                                     "/router/0000000000000001"))
        router_conf_requests.append(({"address": "172.16.30.30/24"},
                                     "/router/0000000000000001"))
        router_conf_requests.append(({"gateway": "172.16.30.1"},
                                     "/router/0000000000000001"))

        router_conf_requests.append(({"address": "172.16.10.1/24"},
                                     "/router/0000000000000002"))
        router_conf_requests.append(({"address": "172.16.30.1/24"},
                                     "/router/0000000000000002"))
        router_conf_requests.append(({"address": "192.168.10.1/24"},
                                     "/router/0000000000000002"))
        router_conf_requests.append(({"gateway": "172.16.30.30"},
                                     "/router/0000000000000002"))
        router_conf_requests.append(({"destination": "192.168.30.0/24", "gateway": "192.168.10.20"},
                                     "/router/0000000000000002"))

        router_conf_requests.append(({"address": "192.168.30.1/24"},
                                     "/router/0000000000000003"))
        router_conf_requests.append(({"address": "192.168.10.20/24"},
                                     "/router/0000000000000003"))
        router_conf_requests.append(({"gateway": "192.168.10.1"},
                                     "/router/0000000000000003"))

        for data, remainingUrl in router_conf_requests:

            resp, content = self.h.request(uri=self.baseUrl + remainingUrl,
                                           method="POST",
                                           headers={'Content-Type': 'application/json; charset=UTF-8'},
                                           body=json.dumps(data))

            time.sleep(0.2)

            if resp["status"] != "200":
                print "Problem Resp:", resp

        # Ping from h1-> h3
        print self.h1.cmd("ping -c3 192.168.30.10")

        # Ping from h2->h3
        print self.h2.cmd("ping -c3 192.168.30.10")

        # Ping from h2->h1
        print self.h2.cmd("ping -c3 172.16.20.10")
