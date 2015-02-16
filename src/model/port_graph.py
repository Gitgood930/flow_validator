__author__ = 'Rakesh Kumar'

import networkx as nx
from networkx import bfs_edges

import sys

from netaddr import IPNetwork
from copy import deepcopy

from port import Port
from match import Match

class PortGraph:
    '''

    This function populates the port graph with edges and match state
    Before this function gets triggered for a specific destination host, we need some
    abstract, generic analysis prepared that applies to more than this host. This pre-analysis need to consider
    how a wildcard flow moves from one port to another in the switch through all the tables.

    What I just described above is essentially what a transfer function does right now. If we keep that inside it,
    Then the transfer function essentially needs to be pre-computed once and then queried by ports as hosts for analysis
    get added

    Capture the action_list for ports before and after a table for a wildcard match,
    The path from one external facing port to another goes through a sequence of action lists
    This breaks when the next action depends on changes that have already been made to the header
    aka apply-action
    The same nature of things also applies when we are traversing switch boundaries, except the action_list
    is empty
    Each switch port has entries for all the destination switches +
    hosts that are directly to the switch as destinations
    Takes a destination port, and source port and computes precisely just that.

    Go a level higher, i.e. Go to the ports that are physically
    connected to ports in this switch from other switches and then compute the same from there.
    This sounds _eerily_ recursive. :)

    These other ports can not be things that we have already seen though

    This whole thing terminates at ports that are connected to other switches.
    This sounds eerily like the end case of recursion
    '''

    def __init__(self, model):
        self.model = model
        self.g = nx.MultiDiGraph()

    def get_table_port_id(self, switch_id, table_number):
        return switch_id + ":table" + str(table_number)

    def get_table_port(self, switch_id, table_number):
        return self.g.node[self._get_table_port_id(switch_id,table_number)]["p"]

    def add_port(self, port):
        self.g.add_node(port.port_id, p=port)

    def remove_port(self):
        pass

    def get_port(self, port_id):
        return self.g.node[port_id]["p"]

    def add_edge(self, port1, port2, match, actions, active_status=True):

        edge_data = {"match": match, "actions": actions, "active_status": active_status}
        e = (port1.port_id, port2.port_id)
        self.g.add_edge(*e, edge_data=edge_data)

    def remove_edge(self, port1, port2):
        pass
        # Look at the source port and see what admitted_matches rely on this edge to be admitted
        # TODO: Store tht information in the first place

        # Ones that do, need to be found alternatives... This can be achieved by looking at other outgoing edges
        # that may be active now...

        # If the admitted matches chance (i,e. their content changes), everybody who relies on that edge needs to be
        # updated, so the change travels back in the bfs fashion

    def get_edge_data(self, node1, node2):
        a = self.g[node1.port_id][node2.port_id]
        return a[0]['edge_data']

    def init_global_controller_port(self):
        cp = Port(None, port_type="controller", port_id="4294967293")
        self.add_port(cp)

    def remove_node_graph_edge(self, node1, node2):
        pass

    def init_port_graph(self):

        #Add a port for controller
        self.init_global_controller_port()

        # Iterate through switches and add the ports and relevant abstract analysis
        for sw in self.model.get_switches():
            sw.compute_switch_port_graph()

        # Add edges between ports on node edges, where nodes are only switches.
        for node_edge in self.model.graph.edges():
            if not node_edge[0].startswith("host") and not node_edge[1].startswith("host"):

                edge_port_dict = self.model.get_edge_port_dict(node_edge[0], node_edge[1])
                port1 = self.get_port(node_edge[0] + ":" + edge_port_dict[node_edge[0]])
                port2 = self.get_port(node_edge[1] + ":" + edge_port_dict[node_edge[1]])

                self.add_edge(port1, port2, Match(init_wildcard=True), None)
                self.add_edge(port2, port1, Match(init_wildcard=True), None)

    def update_edge_down(self):
        pass

    def update_edge_up(self):
        pass

    def add_destination_host_port_traffic(self, host_obj, admitted_match):

        # Add the port for host
        hp = Port(None, port_type="physical", port_id=host_obj.node_id)
        hp.admitted_match[host_obj.node_id] = admitted_match
        self.add_port(hp)

        # Add edges between host and switch in the port graph
        self.add_edge(hp, host_obj.switch_port, Match(init_wildcard=True), None)
        self.add_edge(host_obj.switch_port, hp, Match(init_wildcard=True), None)

        return hp

    def remove_destination_host(self, host_obj):
        pass


    def bfs_paths_2(self, destination_port):
        print "bfs_paths_2"

        # Traverse in reverse.
        for edge in bfs_edges(self.g, destination_port.port_id, reverse=True):
            next_port_towards_dst = self.get_port(edge[0])
            curr_port = self.get_port(edge[1])
            edge_data = self.get_edge_data(self.get_port(edge[1]), self.get_port(edge[0]))

            # print edge[1], "->", edge[0]
            # print "predecessors of", edge[1], ":", self.g.predecessors(edge[1])
            # print "successors of", edge[1], ":", self.g.successors(edge[1])

            # At next_port_towards_dst, set up the admitted traffic for the destination_port, by examining
            # admitted_matches at curr_port
            for dst in next_port_towards_dst.admitted_match:

                to_be_intersected = None
                if edge_data["actions"]:
                    to_be_intersected = edge_data["actions"].get_resulting_match(edge_data["match"])
                else:
                    to_be_intersected = edge_data["match"]

                intersection = to_be_intersected.intersect(next_port_towards_dst.admitted_match[dst])

                if not intersection.has_empty_field():
                    #print "Carried for destination:", dst, "the match:", edge_data["match"]
                    curr_port.admitted_match[dst] = edge_data["match"]
                else:
                    print "Did not carry:", intersection
                    print "Next Port Admits:", next_port_towards_dst.admitted_match[dst]
                    print edge_data