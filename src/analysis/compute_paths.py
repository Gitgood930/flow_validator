__author__ = 'Rakesh Kumar'

import networkx as nx
import sys

from model.model import Model
from model.match import Match

from netaddr import IPNetwork

class ComputePaths:
    def __init__(self):
        self.model = Model()

    def check_flow_reachability(self, src, dst, node_path, path_type, in_port_match, switch_in_port=None):

        # The task of this loop is to examine whether there is a rule,
        #  in the switches along the path, that would admit the path
        #  and pass it to the next switch
        # Assume that there are no host firewalls filtering anything inbound/outbound
        #  The loop below goes from first switch to the second-last switch

        is_reachable = False

        edge_ports_dict = None
        out_port = None
        in_port = None

        # Sanity check -- Check that last node of the node_path is a host, no matter what
        if self.model.graph.node[node_path[len(node_path) - 1]]["node_type"] != "host":
            raise Exception("The last node in the node_path has to be a host.")

        # Check whether the first node of path is a host or a switch.
        if self.model.graph.node[node_path[0]]["node_type"] == "host":

            #Traffic arrives from the host to first switch at switch's port

            edge_ports_dict = self.model.get_edge_port_dict(node_path[0], node_path[1])
            in_port = edge_ports_dict[node_path[1]]

            # Traffic leaves from the first switch's post
            edge_ports_dict = self.model.get_edge_port_dict(node_path[1], node_path[2])
            out_port = edge_ports_dict[node_path[1]]

            node_path = node_path[1:]

        elif self.model.graph.node[node_path[0]]["node_type"] == "switch":
            if not switch_in_port:
                raise Exception("switching_in_port needed.")

            in_port = switch_in_port
            edge_ports_dict = self.model.get_edge_port_dict(node_path[0], node_path[1])
            out_port = edge_ports_dict[node_path[0]]

        # This loop always starts at a switch
        for i in range(len(node_path) - 1):
            switch = self.model.graph.node[node_path[i]]["sw"]
            print "At Switch:", switch.switch_id, "in_port:", in_port

            # Capturing during run for primary, what header-space arrives at each node
            if path_type == "primary":
                switch.in_port_match = in_port_match

            # When it comes time to look for backups, use the header-space saved earlier to kick up analysis
            # at first node
            elif path_type == "backup" and i == 0:
                if switch.in_port_match:
                    in_port_match = switch.in_port_match

            #  This has to happen at every switch, because every switch has its own in_port
            in_port_match.in_port = in_port

            switch_out_port_match = switch.transfer_function(in_port_match)
            if out_port not in switch_out_port_match:
                is_reachable = False
                break
            else:
                in_port_match = switch_out_port_match[out_port]
                is_reachable = True

            # Prepare for next switch along the path if there is a next switch along the path
            if self.model.graph.node[node_path[i+1]]["node_type"] != "host":

                # Traffic arrives from the host to first switch at switch's port
                edge_ports_dict = self.model.get_edge_port_dict(node_path[i], node_path[i+1])
                in_port = edge_ports_dict[node_path[i+1]]

                # Traffic leaves from the first switch's port
                edge_ports_dict = self.model.get_edge_port_dict(node_path[i+1], node_path[i+2])
                out_port = edge_ports_dict[node_path[i+1]]

        return is_reachable

    def check_flow_backups(self, src, dst, node_path, in_port_match):
        has_backup = False

        # Sanity check -- Check that first node of the node_path is a host, no matter what
        if self.model.graph.node[node_path[0]]["node_type"] != "host":
            raise Exception("The first node in the node_path has to be a host.")

        # Sanity check -- Check that last node of the node_path is a host, no matter what
        if self.model.graph.node[node_path[len(node_path) - 1]]["node_type"] != "host":
            raise Exception("The last node in the node_path has to be a host.")

        edge_ports_dict = self.model.get_edge_port_dict(node_path[0], node_path[1])

        in_port = edge_ports_dict[node_path[1]]

        #  Go through the path, one edge at a time

        for i in range(1, len(node_path) - 2):

            edge_has_backup = False

            # Keep a copy of this handy
            edge_ports_dict = self.model.get_edge_port_dict(node_path[i], node_path[i+1])

            # Delete the edge
            self.model.remove_edge(node_path[i], edge_ports_dict[node_path[i]],
                                   node_path[i+1], edge_ports_dict[node_path[i+1]])

            # Go through all simple paths that result when the link breaks
            #  If any of them passes the flow, then this edge has a backup

            asp = nx.all_simple_paths(self.model.graph, source=node_path[i], target=dst)
            for bp in asp:
                print "Topological Backup Path Candidate:", bp
                edge_has_backup = self.check_flow_reachability(src, dst, bp, "backup", in_port_match, in_port)

                print "edge_has_backup:", edge_has_backup
                if edge_has_backup:
                    break

            # Add the edge back and the data that goes along with it
            self.model.add_edge(node_path[i], edge_ports_dict[node_path[i]],
                                node_path[i+1], edge_ports_dict[node_path[i+1]])

            in_port = edge_ports_dict[node_path[i+1]]

            has_backup = edge_has_backup

            if not edge_has_backup:
                break

        return has_backup

    def has_primary_and_backup(self, src, dst, in_port_match):
        has_primary_and_backup = False

        #  First grab all topological paths between src/dst hosts
        asp = nx.all_simple_paths(self.model.graph, source=src, target=dst)

        for p in asp:
            print "Topological Primary Path Candidate", p

            is_reachable_flow = self.check_flow_reachability(src, dst, p, "primary", in_port_match)
            print "is_reachable_flow:", is_reachable_flow

            if is_reachable_flow:
                has_primary_and_backup = self.check_flow_backups(src, dst, p, in_port_match)

                # Keep going if this one did not have a backup
                if has_primary_and_backup:
                    break

        return has_primary_and_backup

    def dfs(self, node_obj):

        node_obj.discovered = True
        print "At node:", node_obj.node_id

#       for all edges from v to w in G.adjacentEdges(v) do
#           if vertex w is not labeled as discovered then
#               recursively call DFS(G,w)

        for neighbor in self.model.graph.neighbors(node_obj.node_id):
            neighbor_obj = self.model.get_node_object(neighbor)

            # If haven't been to this neighbor before
            if not neighbor_obj.discovered:

                print "Try to goto neighbor:", neighbor
                edge_port_dict = self.model.get_edge_port_dict(node_obj.node_id, neighbor)

                # See if we can get to this neighbor from here with the match
                out_port_match = node_obj.transfer_function(node_obj.in_port_match)
                if edge_port_dict[neighbor] in out_port_match:
                    print "Successfully on the other side, will call recursively"
                    passing_match = out_port_match[edge_port_dict[neighbor]]
                    neighbor_obj.in_port_match = passing_match
                    self.dfs(neighbor_obj)
                else:
                    print "could not go to the otherside"


    def analyze_all_node_pairs(self):

        # For each host, start a graph search at the switch it is connected to
        for h_id in self.model.get_host_ids():

            print "Injecting wildcard at host:", h_id

            h_obj = self.model.get_node_object(h_id)

            # Construct a all wildcard match to be injected at each one of these switches
            h_obj.in_port_match = Match()
            h_obj.in_port_match.ethernet_type = 0x0800
            h_obj.in_port_match.ethernet_source = h_obj.mac_addr
            h_obj.in_port_match.has_vlan_tag = False

            self.dfs(h_obj)

def main():
    bp = ComputePaths()
    bp.analyze_all_node_pairs()


if __name__ == "__main__":
    main()
