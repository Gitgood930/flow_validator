__author__ = 'Rakesh Kumar'

from collections import defaultdict
from traffic import Traffic
from port_graph_edge import PortGraphEdge
from port_graph import PortGraph

class SwitchPortGraph(PortGraph):

    def __init__(self, network_graph, sw):

        super(SwitchPortGraph, self).__init__(network_graph)

        self.sw = sw

    def init_switch_port_graph(self):

        print "Initializing Port Graph for switch:", self.sw.node_id

        # Add a node per table in the port graph
        for flow_table in self.sw.flow_tables:
            self.add_node(flow_table.port_graph_node)

        # Add two nodes per physical port in port graph one for incoming and outgoing direction
        # Connect incoming direction port to table 0's port
        for port_num in self.sw.ports:

            port = self.sw.ports[port_num]

            self.add_node(port.switch_port_graph_ingress_node)
            self.add_node(port.switch_port_graph_egress_node)

            self.boundary_ingress_nodes.append(port.switch_port_graph_ingress_node)
            self.boundary_egress_nodes.append(port.switch_port_graph_egress_node)

            edge = PortGraphEdge(port.switch_port_graph_ingress_node, self.sw.flow_tables[0].port_graph_node)
            edge_traffic_filter = Traffic()
            edge_traffic_filter.union(port.ingress_node_traffic)
            edge.add_edge_data((edge_traffic_filter, None, None, None))
            self.add_edge(port.switch_port_graph_ingress_node, self.sw.flow_tables[0].port_graph_node, edge)

        # Try passing a wildcard through the flow table
        for flow_table in self.sw.flow_tables:
            flow_table.compute_flow_table_port_graph_edges()
            self.add_flow_table_edges(flow_table)

        # Initialize all groups' active buckets
        for group_id in self.sw.group_table.groups:
            self.sw.group_table.groups[group_id].set_active_bucket()

    def de_init_switch_port_graph(self):

        # Try passing a wildcard through the flow table
        for flow_table in self.sw.flow_tables:
            flow_table.de_init_flow_table_port_graph()

        # Remove nodes for physical ports
        for port_num in self.sw.ports:

            port = self.sw.ports[port_num]

            ingress_node = self.get_ingress_node(self.sw.node_id, port_num)
            egress_node = self.get_egress_node(self.sw.node_id, port_num)

            self.remove_edge(ingress_node, self.sw.flow_tables[0].port_graph_node)

            self.remove_node(ingress_node)
            self.remove_node(egress_node)

            del ingress_node
            del egress_node

        # Remove table ports
        for flow_table in self.sw.flow_tables:
            self.remove_node(flow_table.port_graph_node)
            flow_table.port = None
            flow_table.port_graph = None

    def get_edges_from_flow_table_edges(self, flow_table, succ):

        edge = PortGraphEdge(flow_table.port_graph_node, succ)

        if succ not in flow_table.current_port_graph_edges:
            pass
        else:
            for edge_data in flow_table.current_port_graph_edges[succ]:

                edge.add_edge_data((edge_data[0],
                                    edge_data[1],
                                    edge_data[2],
                                    edge_data[3]))

        return edge

    def add_flow_table_edges(self, flow_table):

        for succ in flow_table.current_port_graph_edges:
            edge = self.get_edges_from_flow_table_edges(flow_table, succ)
            self.add_edge(flow_table.port_graph_node, succ, edge)


    def modify_flow_table_edges(self, flow_table, modified_flow_table_edges):

        for modified_edge in modified_flow_table_edges:
            pred = self.get_node(modified_edge[0])
            succ = self.get_node(modified_edge[1])

            # First remove the edge
            edge = self.get_edge(pred, succ)
            if edge:
                self.remove_edge(pred, succ)

            edge = self.get_edges_from_flow_table_edges(flow_table, succ)
            self.add_edge(flow_table.port_graph_node, succ, edge)

    def compute_switch_admitted_traffic(self):

        print "Computing Transfer Function for switch:", self.sw.node_id

        # Inject wildcard traffic at each ingress port of the switch
        for port_num in self.sw.ports:

            egress_node = self.get_egress_node(self.sw.node_id, port_num)

            dst_traffic_at_succ = Traffic(init_wildcard=True)
            end_to_end_modified_edges = []
            self.compute_admitted_traffic(egress_node, dst_traffic_at_succ, None, egress_node, end_to_end_modified_edges)

    def compute_edge_admitted_traffic(self, traffic_to_propagate, edge):

        pred_admitted_traffic = Traffic()

        for edge_filter_traffic, edge_action, applied_modifications, written_modifications in edge.edge_data_list:

            if edge.edge_type == "egress":

                # Case when traffic changes switch boundary
                traffic_to_propagate.set_field("in_port", is_wildcard=True)

                for te in traffic_to_propagate.traffic_elements:
                    if edge_action:
                        te.instruction_type = edge_action.instruction_type

                if not edge_action:
                    pass

                for te in traffic_to_propagate.traffic_elements:
                    te.vuln_rank = edge_action.vuln_rank

            if applied_modifications:
                ttp = traffic_to_propagate.get_orig_traffic(applied_modifications)
            else:
                ttp = traffic_to_propagate

            if edge.edge_type == "ingress":
                ttp = traffic_to_propagate.get_orig_traffic()
            else:
                # At all the non-ingress edges accumulate written modifications
                # But these are useless if the instruction_type is applied.
                if written_modifications:
                    for te in ttp.traffic_elements:
                        te.written_modifications.update(written_modifications)

            i = edge_filter_traffic.intersect(ttp)

            if not i.is_empty():
                pred_admitted_traffic.union(i)

        return pred_admitted_traffic

    def update_admitted_traffic_due_to_port_state_change(self, port_num, event_type):

        end_to_end_modified_edges = []

        ingress_node = self.get_ingress_node(self.sw.node_id, port_num)
        egress_node = self.get_egress_node(self.sw.node_id, port_num)

        for pred in self.predecessors_iter(egress_node):

            edge = self.get_edge(pred, egress_node)
            flow_table = pred.parent_obj

            # First get the modified edges in this flow_table (edges added/deleted/modified)
            modified_flow_table_edges = flow_table.update_port_graph_edges()

            self.modify_flow_table_edges(flow_table, modified_flow_table_edges)

            self.update_admitted_traffic(modified_flow_table_edges, end_to_end_modified_edges)

        if event_type == "port_down":

            edge = self.get_edge(ingress_node, self.sw.flow_tables[0].port_graph_node)
            for edge_data_tuple in edge.edge_data_list:
                 del edge_data_tuple[0].traffic_elements[:]

            dsts = self.get_admitted_traffic_dsts(ingress_node)
            for dst in dsts:
                self.compute_admitted_traffic(ingress_node, Traffic(), self.sw.flow_tables[0].port_graph_node, dst, end_to_end_modified_edges)

        elif event_type == "port_up":

            edge = self.get_edge(ingress_node, self.sw.flow_tables[0].port_graph_node)
            for edge_data_tuple in edge.edge_data_list:
                edge_data_tuple[0].union(ingress_node.parent_obj.ingress_node_traffic)

            for dst in self.get_admitted_traffic_dsts(self.sw.flow_tables[0].port_graph_node):
                traffic_to_propagate = Traffic()
                for succ_succ in self.get_admitted_traffic_succs(self.sw.flow_tables[0].port_graph_node, dst):
                    more = self.get_admitted_traffic_via_succ(self.sw.flow_tables[0].port_graph_node, dst, succ_succ)
                    traffic_to_propagate.union(more)

                edge = self.get_edge(ingress_node, self.sw.flow_tables[0].port_graph_node)
                traffic_to_propagate = self.compute_edge_admitted_traffic(traffic_to_propagate, edge)
                self.compute_admitted_traffic(ingress_node, traffic_to_propagate,
                                              self.sw.flow_tables[0].port_graph_node, dst, end_to_end_modified_edges)

        return end_to_end_modified_edges

    def count_paths(self, this_p, dst_p, verbose, path_str="", path_elements=[]):

        path_count = 0
        if dst_p in self.get_admitted_traffic_dsts(this_p):
            for succ_p in self.get_admitted_traffic_succs(this_p, dst_p):

                if succ_p:

                    # Try and detect a loop, if a port repeats more than twice, it is a loop
                    indices = [i for i,x in enumerate(path_elements) if x == succ_p.node_id]
                    if len(indices) > 2:
                        if verbose:
                            print "Found a loop, path_str:", path_str
                    else:
                        path_elements.append(succ_p.node_id)
                        path_count += self.count_paths(succ_p, dst_p, verbose, path_str + " -> " + succ_p.node_id, path_elements)

                # A none succcessor means, it originates here.
                else:
                    if verbose:
                        print path_str

                    path_count += 1

        return path_count

    def get_path_counts_and_tt(self, verbose):
        path_count = defaultdict(defaultdict)
        tt = defaultdict(defaultdict)

        for src_port_number in self.sw.ports:
            src_p = self.get_ingress_node(self.sw.node_id, src_port_number)

            for dst_port_number in self.sw.ports:
                dst_p = self.get_egress_node(self.sw.node_id, dst_port_number)

                path_count[src_p][dst_p] = self.count_paths(src_p, dst_p, verbose, src_p.node_id, [src_p.node_id])
                tt[src_p][dst_p] = self.get_admitted_traffic(src_p, dst_p)

        return path_count, tt

    def compare_path_counts_and_tt(self, path_count_before, tt_before, path_count_after, tt_after, verbose):

        all_equal = True

        for src_port_number in self.sw.ports:
            src_p = self.get_ingress_node(self.sw.node_id, src_port_number)

            for dst_port_number in self.sw.ports:
                dst_p = self.get_egress_node(self.sw.node_id, dst_port_number)

                if verbose:
                    print "From Port:", src_port_number, "To Port:", dst_port_number

                if path_count_before[src_p][dst_p] != path_count_after[src_p][dst_p]:
                    print "Path Count mismatch - Before:", path_count_before[src_p][dst_p], \
                        "After:", path_count_after[src_p][dst_p]
                    all_equal = False
                else:
                    if verbose:
                        print "Path Count match - Before:", path_count_before[src_p][dst_p], \
                            "After:", path_count_after[src_p][dst_p]

                if tt_before[src_p][dst_p].is_equal_traffic(tt_after[src_p][dst_p]):
                    if verbose:
                        print "Transfer traffic match"
                else:
                    print "Transfer traffic mismatch"
                    all_equal = False

        return all_equal

    def test_one_port_failure_at_a_time(self, verbose=False):

        test_passed = True

        # Loop over ports of the switch and fail and restore them one by one
        for testing_port_number in self.sw.ports:

            # if testing_port_number != 2:
            #     continue

            testing_port = self.sw.ports[testing_port_number]

            path_count_before, tt_before = self.get_path_counts_and_tt(verbose)

            testing_port.state = "down"
            end_to_end_modified_edges = self.update_admitted_traffic_due_to_port_state_change(testing_port_number, "port_down")

            path_count_intermediate, tt_intermediate = self.get_path_counts_and_tt(verbose)

            testing_port.state = "up"
            end_to_end_modified_edges = self.update_admitted_traffic_due_to_port_state_change(testing_port_number, "port_up")

            path_count_after, tt_after = self.get_path_counts_and_tt(verbose)

            all_equal = self.compare_path_counts_and_tt(path_count_before, tt_before, path_count_after, tt_after, verbose)

            if not all_equal:
                test_passed = all_equal
                print "Test Failed."

        return test_passed