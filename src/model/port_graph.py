__author__ = 'Rakesh Kumar'

import networkx as nx

from traffic import Traffic
from traffic_path import TrafficPath

from collections import defaultdict


class PortGraph(object):

    @staticmethod
    def get_ingress_node_id(node_id, port_number):
        return node_id + ":ingress" + str(port_number)

    @staticmethod
    def get_egress_node_id(node_id, port_number):
        return node_id + ":egress" + str(port_number)

    def __init__(self, network_graph, report_active_state):

        self.network_graph = network_graph
        self.g = nx.DiGraph()

        # These are used to measure the points where changes are measured
        self.boundary_ingress_nodes = []
        self.boundary_egress_nodes = []
        self.report_active_state = report_active_state

    def get_table_node_id(self, switch_id, table_number):
        return switch_id + ":table" + str(table_number)

    def get_ingress_node(self, node_id, port_number):
        return self.get_node(self.get_ingress_node_id(node_id, port_number))

    def get_egress_node(self, node_id, port_number):
        return self.get_node(self.get_egress_node_id(node_id, port_number))

    def add_node(self, node):
        self.g.add_node(node.node_id, p=node)

    def remove_node(self, node):
        self.g.remove_node(node.node_id)

    def get_node(self, node_id):
        return self.g.node[node_id]["p"]

    def predecessors_iter(self, node):
        for pred_id in self.g.predecessors(node.node_id):
            yield self.get_node(pred_id)

    def successors_iter(self, node):
        for succ_id in self.g.successors(node.node_id):
            yield self.get_node(succ_id)

    def add_edge(self, pred, succ, edge_data):
        self.g.add_edge(pred.node_id, succ.node_id, e=edge_data)

    def remove_edge(self, pred, succ):

        edge_to_remove = self.get_edge(pred, succ)

        # First check if the edge exists
        if edge_to_remove:

            # Remove the port-graph edges corresponding to ports themselves
            self.g.remove_edge(pred.node_id, succ.node_id)

        return edge_to_remove

    def get_edge(self, pred, succ):

        if self.g.has_edge(pred.node_id, succ.node_id):
            return self.g.get_edge_data(pred.node_id, succ.node_id)["e"]
        else:
            return None

    def get_admitted_traffic(self, node, dst):

        dst_admitted_traffic = Traffic()

        if dst in node.admitted_traffic:
            for succ in node.admitted_traffic[dst]:
                dst_admitted_traffic.union(node.admitted_traffic[dst][succ])

        return dst_admitted_traffic

    def get_succs_with_admitted_traffic_and_vuln_rank(self, pred, at, vuln_rank, dst):

        succs_traffic = []
        possible_succs = self.get_admitted_traffic_succs(pred, dst)
        for succ in possible_succs:

            # First check if the successor would carry this traffic at all
            should, enabling_edge_data_list = self.should_add_succ(pred, succ, dst, at)
            traffic_at_succ = self.get_modified_traffic_at_succ(pred, succ, dst, at, enabling_edge_data_list)

            # If so, make sure the traffic is carried because of edge_data with vuln_rank as specified
            if should:
                vuln_rank_check = True

                # TODO: This may cause problem with duplicates (i.e. two edge data with exact same
                # traffic carried but with different vuln_ranks)

                for ed in enabling_edge_data_list:
                    if ed.get_vuln_rank() != vuln_rank:
                        vuln_rank_check = False
                        break

                if vuln_rank_check:
                    succs_traffic.append((succ, traffic_at_succ))

        return succs_traffic

    def get_admitted_traffic_via_succ(self, node, dst, succ):
        return node.admitted_traffic[dst][succ]

    def set_admitted_traffic_via_succ(self, node, dst, succ, admitted_traffic):
        node.admitted_traffic[dst][succ] = admitted_traffic

    def get_admitted_traffic_dsts(self, node):
        return node.admitted_traffic.keys()

    def get_admitted_traffic_succs(self, node, dst):
        succ_list = []
        if dst in node.admitted_traffic:
            succ_list = node.admitted_traffic[dst].keys()

        return succ_list

    def account_node_admitted_traffic(self, curr, dst_traffic_at_succ, succ, dst):

        # Keep track of what traffic looks like before any changes occur
        traffic_before_changes = self.get_admitted_traffic(curr, dst)

        # Compute what additional traffic is being admitted overall
        additional_traffic = traffic_before_changes.difference(dst_traffic_at_succ)

        # Do the changes...
        try:
            # First accumulate any more traffic that has arrived from this sucessor
            prev_dst_traffic_at_succ = self.get_admitted_traffic_via_succ(curr, dst, succ)
            more_from_succ = prev_dst_traffic_at_succ.difference(dst_traffic_at_succ)
            if not more_from_succ.is_empty():
                prev_dst_traffic_at_succ.union(more_from_succ)

            # Then get rid of traffic that this particular successor does not admit anymore
            less_from_succ = dst_traffic_at_succ.difference(self.get_admitted_traffic_via_succ(curr, dst, succ))
            if not less_from_succ.is_empty():
                remaining = less_from_succ.difference(self.get_admitted_traffic_via_succ(curr, dst, succ))
                self.set_admitted_traffic_via_succ(curr, dst, succ, remaining)

        # If there is no traffic for this dst-succ combination prior to this propagation,
        # setup a traffic object for successor
        except KeyError:
            if not dst_traffic_at_succ.is_empty():
                new_traffic = Traffic()
                new_traffic.union(dst_traffic_at_succ)
                self.set_admitted_traffic_via_succ(curr, dst, succ, new_traffic)

        # Then see what the overall traffic looks like after additional/reduced traffic for specific successor
        traffic_after_changes = self.get_admitted_traffic(curr, dst)

        # Compute what reductions (if any) in traffic has occured due to all the changes
        reduced_traffic = traffic_after_changes.difference(traffic_before_changes)

        traffic_to_propagate = traffic_after_changes

        return additional_traffic, reduced_traffic, traffic_to_propagate

    def propagate_admitted_traffic(self, curr, dst_traffic_at_succ, succ, dst, end_to_end_modified_edges):

        additional_traffic, reduced_traffic, traffic_to_propagate = \
            self.account_node_admitted_traffic(curr, dst_traffic_at_succ, succ, dst)

        if not additional_traffic.is_empty() or not reduced_traffic.is_empty():

            if curr in self.boundary_ingress_nodes:
                end_to_end_modified_edges.append((curr.node_id, dst.node_id))

            for pred in self.predecessors_iter(curr):

                edge = self.get_edge(pred, curr)
                pred_admitted_traffic = self.compute_edge_admitted_traffic(traffic_to_propagate, edge)
                self.propagate_admitted_traffic(pred, pred_admitted_traffic, curr, dst, end_to_end_modified_edges)

    def update_admitted_traffic(self, modified_edges, end_to_end_modified_edges):

        # This object holds for each pred/dst combinations
        # that have changed as keys and list of succ ports as values
        admitted_traffic_changes = defaultdict(defaultdict)

        for modified_edge in modified_edges:

            pred = self.get_node(modified_edge[0])
            succ = self.get_node(modified_edge[1])

            # TODO Limit the destinations by using markers in modified_flow_table_edges
            # Right now, just take all the destinations at succ and marking them as having been modified...

            for dst in self.get_admitted_traffic_dsts(succ):
                if dst not in admitted_traffic_changes[pred]:
                    admitted_traffic_changes[pred][dst] = [succ]
                else:
                    if succ not in admitted_traffic_changes[pred][dst]:
                        admitted_traffic_changes[pred][dst].append(succ)

        # Do this for each pred port that has changed
        for pred in admitted_traffic_changes:

            # For each destination that may have been affected at the pred port
            for dst in admitted_traffic_changes[pred]:

                now_pred_traffic = Traffic()

                # Check the fate of traffic from changed successors in this loop
                for succ in admitted_traffic_changes[pred][dst]:

                    edge = self.get_edge(pred, succ)

                    succ_traffic = self.get_admitted_traffic(succ, dst)

                    # Update admitted traffic at successor node to reflect changes
                    pred_traffic_via_succ = self.compute_edge_admitted_traffic(succ_traffic, edge)
                    self.set_admitted_traffic_via_succ(pred, dst, succ, pred_traffic_via_succ)

                    # Accumulate total traffic admitted at this pred
                    now_pred_traffic.union(pred_traffic_via_succ)

                # Collect traffic from any succs that was not changed
                for succ in self.get_admitted_traffic_succs(pred, dst):
                    if succ not in admitted_traffic_changes[pred][dst]:
                        now_pred_traffic.union(self.get_admitted_traffic_via_succ(pred, dst, succ))

                # Propagate the net unioned traffic to all of predecessors of the predecessor itself.
                for pred_pred in self.predecessors_iter(pred):

                    edge = self.get_edge(pred_pred, pred)
                    pred_pred_traffic = self.compute_edge_admitted_traffic(now_pred_traffic, edge)

                    self.propagate_admitted_traffic(pred_pred,
                                                    pred_pred_traffic,
                                                    pred,
                                                    dst, end_to_end_modified_edges)

    def get_graph_at(self):
        graph_ats = defaultdict(defaultdict)

        for src in self.boundary_ingress_nodes:
            for dst in self.boundary_egress_nodes:
                graph_ats[src][dst] = self.get_admitted_traffic(src, dst)

        return graph_ats

    def compare_graph_ats(self, graph_at_before, graph_at_after, verbose):
        all_equal = True

        for src in self.boundary_ingress_nodes:
            for dst in self.boundary_egress_nodes:

                if graph_at_before[src][dst].is_equal_traffic(graph_at_after[src][dst]):
                    if verbose:
                        print "From Port:", src, "To Port:", dst, "Admitted traffic match"
                else:
                    print "From Port:", src, "To Port:", dst, "Admitted traffic mismatch"
                    all_equal = False

        return all_equal

    def path_has_loop(self, path, succ):

        # Check for loops, if a node repeats more than twice, it is a loop
        indices = [i for i, x in enumerate(path) if x == succ]

        has_loop = len(indices) > 2

        if has_loop:
            for n in path:
                print n
            print "Found a loop in the path:", path

        return has_loop

    def should_add_succ(self, this_node, succ, dst, at):

        # For traffic going from ingress->egress node on any switch, set the ingress traffic
        # of specific traffic to simulate that the traffic would arrive on that port.

        if this_node.node_type == "ingress" and succ.node_type == "egress":
            at.set_field("in_port", int(this_node.parent_obj.port_number))

        should = False
        enabling_edge_data_list = []

        at_dst_succ = self.get_admitted_traffic_via_succ(this_node, dst, succ)

        # Check to see if the successor would carry some of the traffic from here
        succ_int = at.intersect(at_dst_succ)
        if not succ_int.is_empty():
            should = True
            enabling_edge_data_list = succ_int.get_enabling_edge_data()
        else:
            # Do not go further if there is no traffic admitted via this succ
            pass

        return should, enabling_edge_data_list

    def get_modified_traffic_at_succ(self, this_node, succ, dst, at, enabling_edge_data_list):

        at_dst_succ = self.get_admitted_traffic_via_succ(this_node, dst, succ)

        # Pick off successor admitted traffic that helps the traffic at pred (at) to exist.
        traffic_at_succ = at.intersect(at_dst_succ)

        # modify at to adjust to the modifications in traffic along the succ
        traffic_at_succ = traffic_at_succ.get_modified_traffic()

        return traffic_at_succ

    def get_paths(self, this_node, dst, at, path_prefix, path_edges, verbose):

        # if this_node.node_id == 's4:ingress2' and dst.node_id == 's2:egress1':
        #     pass

        this_level_paths = []
        this_level_prefix = path_prefix[:]
        this_level_path_edges = path_edges[:]

        if dst in self.get_admitted_traffic_dsts(this_node):

            remaining_succs = self.get_admitted_traffic_succs(this_node, dst)

            # If destination is one of the successors, stop
            if dst in remaining_succs:

                should, enabling_edge_data_list = self.should_add_succ(this_node, dst, dst, at)

                if should:

                    this_level_path_edges.append(((this_node, dst), enabling_edge_data_list, at))
                    path_nodes = list(this_level_prefix) + [dst]

                    this_path = TrafficPath(self, path_nodes, this_level_path_edges)
                    this_level_paths.append(this_path)

                    remaining_succs.remove(dst)

            # Explore all the remaining successors
            for succ in remaining_succs:

                should, enabling_edge_data_list = self.should_add_succ(this_node, succ, dst, at)

                if should:

                    # Make sure no loops will be caused by going down this successor
                    if not self.path_has_loop(path_prefix, succ):

                        traffic_at_succ = self.get_modified_traffic_at_succ(this_node, succ, dst, at, enabling_edge_data_list)

                        this_level_paths.extend(self.get_paths(succ,
                                                               dst,
                                                               traffic_at_succ,
                                                               this_level_prefix + [succ],
                                                               this_level_path_edges + [((this_node, succ),
                                                                                         enabling_edge_data_list,
                                                                                         at)],
                                                               verbose))

        return this_level_paths

    def get_graph_paths(self, verbose):
        graph_paths = defaultdict(defaultdict)

        for src in self.boundary_ingress_nodes:
            for dst in self.boundary_egress_nodes:

                at = self.get_admitted_traffic(src, dst)
                graph_paths[src][dst] = self.get_paths(src, dst, at, [src], [], verbose)

        return graph_paths

    def compare_graph_paths(self, graph_paths_before, graph_paths_after, verbose):

        all_equal = True

        for src in self.boundary_ingress_nodes:
            for dst in self.boundary_egress_nodes:

                if len(graph_paths_before[src][dst]) != len(graph_paths_after[src][dst]):
                    print "From Port:", src, "To Port:", dst, \
                        "Path Count mismatch - Before:", len(graph_paths_before[src][dst]), \
                        "After:", len(graph_paths_after[src][dst])
                    all_equal = False
                else:

                    all_before_paths_matched = True
                    for i in range(len(graph_paths_before[src][dst])):

                        this_before_path_matched = False
                        for j in range(len(graph_paths_after[src][dst])):
                            if graph_paths_before[src][dst][i] == graph_paths_after[src][dst][j]:
                                this_before_path_matched = True
                                break

                        if not this_before_path_matched:
                            all_before_paths_matched = False
                            break

                    if not all_before_paths_matched:
                        print "Before and after path contents don't match."
                    elif  verbose:
                        print "From Port:", src, "To Port:", dst, \
                            "Path Count match - Before:", len(graph_paths_before[src][dst]), \
                            "After:", len(graph_paths_after[src][dst])
        return all_equal