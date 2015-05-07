__author__ = 'Rakesh Kumar'


class Port():

    def __init__(self, sw, odl_port_json=None, ryu_port_json=None, port_type="physical", port_id=None):

        self.sw = sw
        self.port_type = port_type
        self.port_id = None

        # This dictionary is to hold a Match object per destination
        self.path_elements = {}
        self.admitted_traffic = {}
        self.traversal_distance = None

        # These apply specifically to physical ports
        self.mac_address = None
        self.port_number = None
        self.state = None

        if port_type == "physical" and odl_port_json:
            self._populate_with_odl_port_json(odl_port_json)

        elif port_type == "physical" and ryu_port_json:
            self._populate_with_ryu_port_json(ryu_port_json)

        elif port_type == "ingress":
            self.port_id = port_id
        elif port_type == "egress":
            self.port_id = port_id
        elif port_type == "table":
            self.port_id = port_id
        elif port_type == "controller":
            self.port_id = port_id

        else:
            raise Exception("Invalid port type specified.")

    def _populate_with_odl_port_json(self, odl_port_json):

        self.port_id = str(self.sw.node_id) + ":" + str(odl_port_json["flow-node-inventory:port-number"])
        self.port_number = odl_port_json["flow-node-inventory:port-number"]
        self.mac_address = odl_port_json["flow-node-inventory:hardware-address"]

        if odl_port_json["flow-node-inventory:state"]["link-down"]:
            self.state = "down"
        else:
            self.state = "up"

    def _populate_with_ryu_port_json(self, ryu_port_json):

        self.port_id = str(self.sw.node_id) + ":" + str(ryu_port_json["port_no"])
        self.port_number = ryu_port_json["port_no"]
        self.mac_address = ryu_port_json["hw_addr"]

        #TODO: Peep into ryu_port_json["state"]
        self.state = "up"

    def __str__(self):

        return " Id: " + str(self.port_id)
