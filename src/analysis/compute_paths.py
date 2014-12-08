__author__ = 'Rakesh Kumar'

import networkx as nx
import sys

from model.model import Model
from model.match import Match

from netaddr import IPNetwork

class ComputePaths:
    def __init__(self):
        self.model = Model()

    def dfs(self, node_obj, destination_node_obj, visited):

        visited.add(node_obj)

        for neighbor in self.model.graph.neighbors(node_obj.node_id):
            neighbor_obj = self.model.get_node_object(neighbor)

            # If haven't been to this neighbor before
            if neighbor_obj not in visited:

                # See if we can get to this neighbor from here with the match
                edge_port_dict = self.model.get_edge_port_dict(node_obj.node_id, neighbor)
                out_port_match = node_obj.transfer_function(node_obj.in_port_match)
                if edge_port_dict[node_obj.node_id] in out_port_match:

                    passing_match = out_port_match[edge_port_dict[node_obj.node_id]]
                    passing_match.in_port = edge_port_dict[neighbor]
                    neighbor_obj.in_port_match = passing_match

                    if neighbor_obj.node_id == destination_node_obj.node_id:
                        print "Arrived at the destination."
                    else:
                        self.dfs(neighbor_obj, destination_node_obj, visited)

    def bfs(self, start_node_obj, destination_node_obj):

        visited = set()
        queue =[start_node_obj]

        while queue:
            node_obj = queue.pop(0)

            if node_obj == destination_node_obj:
                print "Arrived at the destination:", node_obj.node_id
            else:
                print "Exploring node:", node_obj.node_id

            if node_obj not in visited:
                visited.add(node_obj)

                # Go through the neighbors of this node and see where else we can go
                for neighbor in self.model.graph.neighbors(node_obj.node_id):
                    neighbor_obj = self.model.get_node_object(neighbor)
                    if neighbor_obj not in visited:

                        # See if we can get to this neighbor from here with the match
                        edge_port_dict = self.model.get_edge_port_dict(node_obj.node_id, neighbor)
                        out_port_match = node_obj.transfer_function(node_obj.in_port_match)
                        if edge_port_dict[node_obj.node_id] in out_port_match:

                            # Account for what traffic will arrive at neighbor
                            passing_match = out_port_match[edge_port_dict[node_obj.node_id]]
                            passing_match.in_port = edge_port_dict[neighbor]
                            neighbor_obj.in_port_match = passing_match

                            # Add the neighbor to queue so it is visited
                            queue.append(neighbor_obj)

    def check_switch_crossing(self, node_obj, neighbor_obj):

        # See if we can get to this neighbor from here with the match
        edge_port_dict = self.model.get_edge_port_dict(node_obj.node_id, neighbor_obj.node_id)
        out_port_match = node_obj.transfer_function(node_obj.in_port_match)

        if edge_port_dict[node_obj.node_id] in out_port_match:

            # Account for what traffic will arrive at neighbor
            passing_match = out_port_match[edge_port_dict[node_obj.node_id]]
            passing_match.in_port = edge_port_dict[neighbor_obj.node_id]
            neighbor_obj.in_port_match = passing_match

            return True
        else:

            return False


    def bfs_paths(self, start_node_obj, destination_node_obj):

        queue = [(start_node_obj, [start_node_obj])]

        while queue:
            node_obj, path = queue.pop(0)

            for neighbor in self.model.graph.neighbors(node_obj.node_id):
                neighbor_obj = self.model.get_node_object(neighbor)

                # Consider only nodes that are not in the path accumulated so far
                if neighbor_obj not in path:

                    # If arrived at the destination already, stop
                    if neighbor_obj == destination_node_obj:
                        yield path + [neighbor_obj]

                    # Otherwise, where else can I go, add them to to the queue
                    else:
                        if self.check_switch_crossing(node_obj, neighbor_obj):
                            queue.append((neighbor_obj, path + [neighbor_obj]))

    def check_switch_crossing_reverse(self, neighbor_obj, node_obj, destination):

        print "At switch:", node_obj.node_id, "Neighbor Switch:", neighbor_obj.node_id

        edge_port_dict = self.model.get_edge_port_dict(neighbor_obj.node_id, node_obj.node_id)

        #Check to see if the required destination match can get from neighbor to node
        out_port_match = neighbor_obj.transfer_function(node_obj.accepted_destination_match[destination])

        if edge_port_dict[neighbor_obj.node_id] in out_port_match:

            # compute what traffic will arrive from neighbor
            passing_match = out_port_match[edge_port_dict[neighbor_obj.node_id]]

            # Set the match in the neighbor, indicating what passes
            neighbor_obj.accepted_destination_match[destination] = passing_match

            return True
        else:
            return False


    def bfs_paths_reverse(self, start_node_obj, destination_node_obj, destination):

        queue = [(destination_node_obj, [destination_node_obj])]

        while queue:
            node_obj, path = queue.pop(0)

            for neighbor in self.model.graph.neighbors(node_obj.node_id):
                neighbor_obj = self.model.get_node_object(neighbor)

                # Consider only nodes that are not in the path accumulated so far
                if neighbor_obj not in path:

                    # If arrived at the source already, stop
                    if neighbor_obj == start_node_obj:
                        yield [neighbor_obj] + path

                    # Otherwise, can I come from neighbor to here
                    else:
                        if self.check_switch_crossing_reverse(neighbor_obj, node_obj, destination):
                            queue.append((neighbor_obj, [neighbor_obj] + path))

    def analyze_all_node_pairs(self):

        # For each host, start a graph search at the switch it is connected to
        for src_h_id in self.model.get_host_ids():

            for dst_h_id in self.model.get_host_ids():

                src_h_obj = self.model.get_node_object(src_h_id)
                dst_h_obj = self.model.get_node_object(dst_h_id)

                if src_h_id == dst_h_id:
                    continue

                print "Injecting wildcard at switch:", src_h_obj.switch_obj, "connected to host", src_h_id

                src_h_obj.switch_obj.in_port_match = Match()
                src_h_obj.switch_obj.in_port_match.ethernet_type = 0x0800
                src_h_obj.switch_obj.in_port_match.ethernet_source = src_h_obj.mac_addr
                src_h_obj.switch_obj.in_port_match.ethernet_destination = dst_h_obj.mac_addr
                src_h_obj.switch_obj.in_port_match.has_vlan_tag = False
                src_h_obj.switch_obj.in_port = src_h_obj.switch_port_attached

                print "--"
                print list(self.bfs_paths(src_h_obj.switch_obj, dst_h_obj))


    def analyze_all_node_pairs_reverse(self):

        # For each host, start a graph search at the switch it is connected to
        for src_h_id in self.model.get_host_ids():

            for dst_h_id in self.model.get_host_ids():

                src_h_obj = self.model.get_node_object(src_h_id)
                dst_h_obj = self.model.get_node_object(dst_h_id)

                if src_h_id == dst_h_id:
                    continue

                print "Setting accepted destination at switch:", dst_h_obj.switch_obj, "connected to host", dst_h_id

                accepted_match = Match()
                accepted_match.ethernet_type = 0x0800
                accepted_match.ethernet_source = src_h_obj.mac_addr
                accepted_match.ethernet_destination = dst_h_obj.mac_addr


                dst_h_obj.switch_obj.accepted_destination_match[dst_h_obj.node_id] = accepted_match



                print "--"
                print list(self.bfs_paths_reverse(src_h_obj.switch_obj, dst_h_obj.switch_obj, dst_h_id))


    def tf_driver(self):
        for sw in self.model.get_switches():
            print sw.node_id
            sw.compute_transfer_function()


def main():
    bp = ComputePaths()
    bp.analyze_all_node_pairs()

    #bp.analyze_all_node_pairs_reverse()

    #bp.tf_driver()


if __name__ == "__main__":
    main()
