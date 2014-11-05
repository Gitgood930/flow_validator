__author__ = 'Rakesh Kumar'

import json
import sys
import pprint

import httplib2
import networkx as nx

from flow_table import FlowTable

from group_table import GroupTable
from group_table import Group

from port import Port


class Model():
    def __init__(self):

        # Initialize the self.graph
        self.graph = nx.Graph()

        # Initialize lists of host and switch ids
        self.host_ids = []
        self.switch_ids = []

        #  Load up everything
        self._load_model()

    def _prepare_group_table(self, node_id):

        group_table = None

        baseUrl = 'http://localhost:8181/restconf/'
        h = httplib2.Http(".cache")
        h.add_credentials('admin', 'admin')

        # Get all the nodes/switches from the inventory API
        remaining_url = 'config/opendaylight-inventory:nodes/node/' + str(node_id)

        resp, content = h.request(baseUrl + remaining_url, "GET")

        if resp["status"] == "200":
            node = json.loads(content)

            if "flow-node-inventory:group" in node["node"][0]:
                groups_json = node["node"][0]["flow-node-inventory:group"]
                group_table = GroupTable(groups_json)

            else:
                print "No groups configured in node:", node_id
        else:
            print "Could not fetch any groups via the API, status:", resp["status"]

        return group_table

    def _load_model(self):
        baseUrl = 'http://localhost:8181/restconf/'
        h = httplib2.Http(".cache")
        h.add_credentials('admin', 'admin')

        # Get all the nodes/switches from the inventory API
        remaining_url = 'operational/opendaylight-inventory:nodes'

        resp, content = h.request(baseUrl + remaining_url, "GET")
        nodes = json.loads(content)

        #  Go through each node and grab the switches and the corresponding hosts associated with the switch
        for node in nodes["nodes"]["node"]:

            switch_id = node["id"]
            switch_flow_tables = []

            group_table = self._prepare_group_table(switch_id)

            # Parse out the flow tables in the switch
            for flow_table in node["flow-node-inventory:table"]:

                #  Only capture those flow_tables that have actual rules in them
                if "flow" in flow_table:
                    switch_flow_tables.append(FlowTable(flow_table["id"], flow_table["flow"], group_table))

            switch_port_dict = {}
            # Parse out the information about all the ports in the switch
            for nc in node["node-connector"]:
                switch_port_dict[nc["flow-node-inventory:port-number"]] = Port(nc)

            # Add the switch node
            self.switch_ids.append(switch_id)
            self.graph.add_node(switch_id, node_type="switch",
                                flow_tables= switch_flow_tables,
                                ports = switch_port_dict)


        # Go through the topology API
        remaining_url = 'operational/network-topology:network-topology'
        resp, content = h.request(baseUrl + remaining_url, "GET")
        topology = json.loads(content)

        topology_links = dict()
        if "link" in topology["network-topology"]["topology"][0]:
            topology_links = topology["network-topology"]["topology"][0]["link"]

        topology_nodes = dict()
        if "node" in topology["network-topology"]["topology"][0]:
            topology_nodes = topology["network-topology"]["topology"][0]["node"]

        # Extract all hosts in the topology
        for node in topology_nodes:
            if node["node-id"].startswith("host"):
                host_ip = node["host-tracker-service:addresses"][0]["ip"]
                self.host_ids.append(host_ip)
                self.graph.add_node(host_ip, node_type="host")

        for link in topology_links:

            node1_id = link["source"]["source-node"]
            node2_id = link["destination"]["dest-node"]

            node1_type = None
            node2_type = None

            node1_port = link["source"]["source-tp"].split(":")[2]
            node2_port = link["destination"]["dest-tp"].split(":")[2]

            if node1_id.startswith("host"):
                node1_type = "host"
                for node in topology_nodes:
                    if node["node-id"] == node1_id:
                        node1_id = node["host-tracker-service:addresses"][0]["ip"]
            else:
                node1_type = "switch"


            if node2_id.startswith("host"):
                node2_type = "host"
                for node in topology_nodes:
                    if node["node-id"] == node2_id:
                        node2 = node["host-tracker-service:addresses"][0]["ip"]
            else:
                node2_type = "switch"

            edge_port_dict = {node1_id: node1_port, node2_id: node2_port}
            e = (node1_id, node2_id)
            self.graph.add_edge(*e, edge_ports_dict=edge_port_dict)


            #  Set Node1 and Node2's ports' facing values while you are at.
            node1 = self.graph.node[node1_id]
            node2 = self.graph.node[node2_id]

            if node1_type == "switch" and not node1["ports"][node1_port].faces:
                node1["ports"][node1_port].faces = node2_type

            if node1_type == "switch" and not node1["ports"][node1_port].facing_node_id:
                node1["ports"][node1_port].facing_node_id = node2_id

            if node2_type == "switch" and not node2["ports"][node2_port].faces:
                node2["ports"][node2_port].faces = node1_type

            if node2_type == "switch" and not node2["ports"][node2_port].facing_node_id:
                node2["ports"][node2_port].facing_node_id = node1_id


        print "Hosts in the graph:", self.host_ids
        print "Switches in the graph:", self.switch_ids
        print "Number of nodes in the graph:", self.graph.number_of_nodes()
        print "Number of edges in the graph:", self.graph.number_of_edges()


    def get_node_graph(self):
        return self.graph

    def get_host_ids(self):
        return self.host_ids

    def get_switch_ids(self):
        return self.switch_ids



def main():
    m = Model()

if __name__ == "__main__":
    main()
