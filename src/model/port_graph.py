__author__ = 'Rakesh Kumar'

import networkx as nx
from collections import deque

import sys

from netaddr import IPNetwork
from copy import deepcopy

from port import Port
from match import Match
from flow_path import FlowPathElement


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
        self.added_host_ports = []

    def get_table_port_id(self, switch_id, table_number):
        return switch_id + ":table" + str(table_number)

    def get_incoming_port_id(self, switch_id, port_number):
        return switch_id + ":incoming" + str(port_number)

    def get_outgoing_port_id(self, switch_id, port_number):
        return switch_id + ":outgoing" + str(port_number)

    def add_port(self, port):
        self.g.add_node(port.port_id, p=port)

    def remove_port(self):
        pass

    def get_port(self, port_id):
        return self.g.node[port_id]["p"]

    def add_edge(self, port1, port2, key, edge_filter_match):

        edge_type = None
        if port1.port_type == "table" and port2.port_type == "outgoing":
            edge_type = "egress"
        elif port1.port_type == "incoming" and port2.port_type == "table":
            edge_type = "ingress"
        elif port1.port_type == "physical" and port2.port_type == "table":
            edge_type = "transport"

        e = (port1.port_id, port2.port_id, key)

        self.g.add_edge(*e,
                        edge_filter_match=edge_filter_match,
                        edge_type=edge_type)

        return e

    def remove_edge(self, port1, port2):

        print "remove_edge_called"

        # Remove the port-graph edges corresponding to ports themselves
        self.g.remove_edge(port1.port_id, port2.port_id)

        # But this could have structural fail-over consequences for this port's predecessors
        # So for all remaining predecessors of this port, recompute the impact on port graph edge status
        for pred_id in self.g.predecessors_iter(port1.port_id):
            pred = self.get_port(pred_id)
            edge_data = self.g.get_edge_data(pred_id, port1.port_id)

            edge_data_keys = edge_data.keys()
            for edge_data_key in edge_data_keys:
                if edge_data_key[0]:
                    edge_data_key[0].update_port_graph_edges()

            # For each predecessor, they would either still be able to do their admitted_match,
            # or things may have changed for worse, in which case their predecessor might want to know
            # Either way, this needs to be done.

            self.verify_and_correct_admitted_match(pred)

    def verify_and_correct_admitted_match(self, curr):

        print curr.port_id

        for dst in curr.admitted_match:
            print dst, curr.admitted_match[dst]

            # For each match element in the admitted match
            for me in curr.admitted_match[dst].match_elements:
                pass

                # Is the edge for this piece of admitted_match still active? It should not be...
                print me.relies_on

                ed = self.g.get_edge_data(curr.port_id, me.relies_on.port_id)
                print ed
                print len(ed)

                # Is there a fail-over at this edge for this particular me then?

                # There are other outgoing edges at this port where me will be carried AND
                # Those admitted matches have been propagated at those other ports...


                # If not, update yourself and your predecessors are gonna wanna know...

                # If so, no sweat, move on



    def init_global_controller_port(self):
        cp = Port(None, port_type="controller", port_id="4294967293")
        self.add_port(cp)

    def add_node_graph_edge(self, node1_id, node2_id):

        edge_data = self.model.get_edge_port_dict(node1_id, node2_id)

        from_port = self.get_port(self.get_outgoing_port_id(node1_id, edge_data[node1_id]))
        to_port = self.get_port(self.get_incoming_port_id(node2_id, edge_data[node2_id]))
        self.add_edge(from_port, to_port, (None, None), Match(init_wildcard=True))

        from_port = self.get_port(self.get_outgoing_port_id(node2_id, edge_data[node2_id]))
        to_port = self.get_port(self.get_incoming_port_id(node1_id, edge_data[node1_id]))
        self.add_edge(from_port, to_port, (None, None), Match(init_wildcard=True))

    def remove_node_graph_edge(self, node1_id, node2_id):

        edge_data = self.model.get_edge_port_dict(node1_id, node2_id)

        from_port = self.get_port(self.get_outgoing_port_id(node1_id, edge_data[node1_id]))
        to_port = self.get_port(self.get_incoming_port_id(node2_id, edge_data[node2_id]))
        self.remove_edge(from_port, to_port)

        from_port = self.get_port(self.get_outgoing_port_id(node2_id, edge_data[node2_id]))
        to_port = self.get_port(self.get_incoming_port_id(node1_id, edge_data[node1_id]))
        self.remove_edge(from_port, to_port)

    def init_port_graph(self):

        #Add a port for controller
        #TODO: Nothing gets added to this for now.
        self.init_global_controller_port()

        # Iterate through switches and add the ports and relevant abstract analysis
        for sw in self.model.get_switches():
            sw.compute_switch_port_graph()

        # Add edges between ports on node edges, where nodes are only switches.
        for node_edge in self.model.graph.edges():
            if not node_edge[0].startswith("host") and not node_edge[1].startswith("host"):
                self.add_node_graph_edge(node_edge[0], node_edge[1])

    def add_destination_host_port_traffic(self, host_obj, admitted_match):

        # Add the port for host

        hp = Port(None, port_type="physical", port_id=host_obj.node_id)
        hp.path_elements[host_obj.node_id] = FlowPathElement(host_obj.node_id, admitted_match, None)

        hp.admitted_match[host_obj.node_id] = admitted_match
        hp.admitted_match[host_obj.node_id].add_port_to_path(hp)

        self.add_port(hp)
        self.added_host_ports.append(hp)

        # Add edges between host and switch in the port graph

        switch_ingress_port = self.get_port(self.get_incoming_port_id(host_obj.switch_id,
                                                                       host_obj.switch_port_attached))

        switch_ingress_port.port_number = int(host_obj.switch_port.port_number)

        switch_egress_port = self.get_port(self.get_outgoing_port_id(host_obj.switch_id,
                                                                      host_obj.switch_port_attached))
        switch_egress_port.port_number = int(host_obj.switch_port.port_number)

        self.add_edge(hp, switch_ingress_port, (None, None), Match(init_wildcard=True))
        self.add_edge(switch_egress_port, hp, (None, None), Match(init_wildcard=True))

        host_obj.switch_ingress_port = switch_ingress_port
        host_obj.switch_egress_port = switch_egress_port

        return hp

    def remove_destination_host(self, host_obj):
        pass


    def process_edges_in_reverse(self, predecessor_port, curr_port, dst_port_id):

        pred_admitted_match = Match()
        edge_data = self.g.get_edge_data(predecessor_port.port_id, curr_port.port_id)

        for edge_data_key in edge_data:
            this_edge = edge_data[edge_data_key]

            if edge_data_key[1]:
                edge_action = edge_data_key[1]
                if not edge_action.is_active:
                    continue


            if dst_port_id in curr_port.admitted_match:
                curr_admitted_match = curr_port.admitted_match[dst_port_id]

                # You enter the switch at "egress" edges. Yes... Eye-roll:
                # At egress edges, set the in_port of the admitted match for destination to wildcard except for
                # the specific port you entered on
                if this_edge["edge_type"] == "egress":
                    curr_admitted_match.set_field("in_port", int(curr_port.port_number), exception=True)

                if edge_data_key[0]:
                    # This is what the match would be before passing this flow
                    attempted_match = curr_admitted_match.get_orig_match(edge_data_key[0].modified_fields,
                                                                         edge_data_key[0].match_element)
                else:
                    attempted_match = curr_admitted_match

                i = this_edge["edge_filter_match"].intersect(attempted_match)
                if not i.is_empty():
                    pred_admitted_match.union(i)

        return pred_admitted_match


    # curr in this function below represents the port we assumed to have already reached
    # and are either collecting goods and stopping or recursively trying to get to its predecessors

    def compute_admitted_match(self, curr, curr_admitted_match, succ, dst_port):

        # If curr has not seen destination at all, first get the curr_admitted_match account started
        if dst_port.port_id not in curr.admitted_match:
            curr.admitted_match[dst_port.port_id] = curr_admitted_match

        # If you already know something about this destination, then keep accumulating
        # this is for cases when recursion comes from multiple directions and accumulates here
        else:
            curr.admitted_match[dst_port.port_id].union(curr_admitted_match)

        # Whoever called me is what I rely on...
        curr_admitted_match.set_reliance(succ)


        # Base case: Stop at host ports.
        if curr in self.added_host_ports:
            return
        else:
            #Establish that curr is part of the path that the MatchElements are going to take to pred
            curr.admitted_match[dst_port.port_id].add_port_to_path(curr)

            # Recursively call myself at each of my predecessors in the port graph
            for pred_id in self.g.predecessors_iter(curr.port_id):

                pred = self.get_port(pred_id)
                pred_admitted_match = self.process_edges_in_reverse(pred, curr, dst_port.port_id)

                if not pred_admitted_match.is_empty():
                    self.compute_admitted_match(pred, pred_admitted_match, curr, dst_port)