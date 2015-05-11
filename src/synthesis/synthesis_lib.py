__author__ = 'Rakesh Kumar'


import pprint
import time
import httplib2
import json

from model.network_graph import NetworkGraph


class SynthesisLib():

    def __init__(self, controller_host, controller_port, model=None, master_switch=False):

        if not model:
            self.network_graph = NetworkGraph()
        else:
            self.network_graph = model

        self.controller_host = controller_host
        self.controller_port = controller_port

        self.master_switch = master_switch

        self.group_id_cntr = 0
        self.flow_id_cntr = 0

        self.h = httplib2.Http(".cache")
        self.h.add_credentials('admin', 'admin')

    def push_change(self, url, pushed_content):

        time.sleep(0.1)

        if self.network_graph.controller == "odl":

            resp, content = self.h.request(url, "PUT",
                                           headers={'Content-Type': 'application/json; charset=UTF-8'},
                                           body=json.dumps(pushed_content))

        elif self.network_graph.controller == "ryu":

            resp, content = self.h.request(url, "POST",
                                           headers={'Content-Type': 'application/json; charset=UTF-8'},
                                           body=json.dumps(pushed_content))

        #resp = {"status": "200"}
        #pprint.pprint(pushed_content)

        if resp["status"] == "200":
            print "Pushed Successfully:", pushed_content.keys()[0]
            #print resp["status"]
        else:
            print "Problem Pushing:", pushed_content.keys()[0]
            print "resp:", resp, "content:", content
            pprint.pprint(pushed_content)


    def create_odl_group_url(self, node_id,  group_id):

        odl_node_id = "openflow:" + node_id[1]
        return "http://" + self.controller_host + ":" + self.controller_port + \
               "/restconf/config/opendaylight-inventory:nodes/node/" + \
               odl_node_id + '/group/' + str(group_id)

    def create_odl_flow_url(self, node_id, table_id, flow_id):

        odl_node_id = "openflow:" + node_id[1]
        return "http://" + self.controller_host + ":" + self.controller_port + \
               "/restconf/config/opendaylight-inventory:nodes/node/" + \
               odl_node_id + "/table/" + str(table_id) + '/flow/' + str(flow_id)

    def create_ryu_flow_url(self):
        return "http://localhost:8080/stats/flowentry/add"

    def push_flow(self, sw, flow):

        url = None

        if self.network_graph.controller == "odl":
            flow_id = flow["flow-node-inventory:flow"]["id"]
            table_id = flow["flow-node-inventory:flow"]["table_id"]
            url = self.create_odl_flow_url(sw, table_id, flow_id)

        elif self.network_graph.controller == "ryu":
            url = self.create_ryu_flow_url()

        self.push_change(url, flow)

    def push_group(self, sw, group):

        group_id = group["flow-node-inventory:group"]["group-id"]
        url = self.create_odl_group_url(sw, group_id)
        self.push_change(url, group)

    def create_base_flow(self, sw, table_id, priority):

        if self.network_graph.controller == "odl":

            flow = dict()

            flow["flags"] = ""
            flow["table_id"] = table_id
            self.flow_id_cntr +=  1
            flow["id"] = self.flow_id_cntr
            flow["priority"] = priority
            flow["idle-timeout"] = 0
            flow["hard-timeout"] = 0
            flow["cookie"] = self.flow_id_cntr
            flow["cookie_mask"] = 255

            # Empty match
            flow["match"] = {}

            # Empty instructions
            flow["instructions"] = {"instruction": []}

            #  Wrap it in inventory
            flow = {"flow-node-inventory:flow": flow}

            return flow

        elif self.network_graph.controller == "ryu":

            flow = {"dpid": sw[1:],
                    "cookie": self.flow_id_cntr,
                    "cookie_mask": 1,
                    "table_id": table_id,
                    "idle_timeout": 0,
                    "hard_timeout": 0,
                    "priority": priority,
                    "flags": 1,
                    "match": {},
                    "actions": []}

            return flow

    def populate_flow_action_instruction(self, flow, action_list, apply_immediately):

        if self.network_graph.controller == "odl":

            if apply_immediately:
                apply_actions_instruction = {"apply-actions": {"action": action_list}, "order": 0}
                flow["flow-node-inventory:flow"]["instructions"]["instruction"].append(apply_actions_instruction)
            else:
                write_actions_instruction = {"write-actions": {"action": action_list}, "order": 0}
                flow["flow-node-inventory:flow"]["instructions"]["instruction"].append(write_actions_instruction)

        elif self.network_graph.controller == "ryu":

            flow["actions"] = action_list

            if apply_immediately:
                pass
            else:
                pass


    def push_table_miss_goto_next_table_flow(self, sw, table_id):

        # Create a lowest possible flow
        flow = self.create_base_flow(sw, table_id, 0)

        #Compile instruction
        #  Assert that packet be sent to table with this table_id + 1

        if self.network_graph.controller == "odl":
            go_to_table_instruction = {"go-to-table": {"table_id": table_id + 1}, "order": 0}
            flow["flow-node-inventory:flow"]["instructions"]["instruction"].append(go_to_table_instruction)

        elif self.network_graph.controller == "ryu":
            flow["actions"] = [{"type": "GOTO_TABLE",  "table_id": str(table_id + 1)}]


        self.push_flow(sw, flow)

    def push_match_per_in_port_destination_instruct_group_flow(self, sw, table_id, group_id, priority,
                                                                flow_match, apply_immediately):

        flow = self.create_base_flow(sw, table_id, priority)

        #Compile match
        flow["flow-node-inventory:flow"]["match"] = \
            flow_match.generate_match_json(self.network_graph.controller, flow["flow-node-inventory:flow"]["match"])

        #Compile instruction

        #  Assert that group is executed upon match
        group_action = {"group-id": group_id}
        action_list = [{"group-action": group_action, "order": 0}]

        self.populate_flow_action_instruction(flow, action_list, apply_immediately)
        self.push_flow(sw, flow)

        return flow

    def create_base_group(self):
        group = dict()

        self.group_id_cntr += 1
        group["group-id"] = str(self.group_id_cntr)
        group["barrier"] = False

        #  Empty Bucket List
        bucket = {"bucket": []}
        group["buckets"] = bucket
        group = {"flow-node-inventory:group": group}

        return group

    def get_out_and_watch_port(self, intent):
        out_port = None
        watch_port = None

        if intent.in_port == intent.out_port:
            out_port = self.network_graph.OFPP_IN
            watch_port = intent.out_port
        else:
            out_port = intent.out_port
            watch_port = intent.out_port

        return out_port, watch_port

    def push_fast_failover_group(self, sw, primary_intent, failover_intent):

        group = self.create_base_group()
        bucket_list = group["flow-node-inventory:group"]["buckets"]["bucket"]
        group["flow-node-inventory:group"]["group-type"] = "group-ff"

        out_port, watch_port = self.get_out_and_watch_port(primary_intent)

        bucket_primary = {
            "action":[{'order': 0,
                       'output-action': {'output-node-connector': out_port}}],
            "bucket-id": 0,
            "watch_port": watch_port,
            "weight": 20}

        out_port, watch_port = self.get_out_and_watch_port(failover_intent)

        bucket_failover = {
            "action":[{'order': 0,
                       'output-action': {'output-node-connector': out_port}}],
            "bucket-id": 1,
            "watch_port": watch_port,
            "weight": 20}

        bucket_list.append(bucket_primary)
        bucket_list.append(bucket_failover)

        self.push_group(sw, group)

        return group

    def push_select_all_group(self, sw, intent_list):

        group = self.create_base_group()
        bucket_list = group["flow-node-inventory:group"]["buckets"]["bucket"]
        group["flow-node-inventory:group"]["group-type"] = "group-all"

        if intent_list:
            for intent in intent_list:

                out_port, watch_port = self.get_out_and_watch_port(intent)

                bucket = {"action": [{'order': 0,
                                      'output-action': {'output-node-connector': out_port}}],
                          "bucket-id": 1}

                bucket_list.append(bucket)

        else:
            raise Exception("Need to have either one or two forwarding intents")

        self.push_group(sw, group)

        return group

    def push_destination_host_mac_intent_flow(self, sw, mac_intent, table_id, priority):

        flow = self.create_base_flow(sw, table_id, priority)

        #Compile match
        flow["flow-node-inventory:flow"]["match"] = \
            mac_intent.flow_match.generate_match_json(self.network_graph.controller,
                                                      flow["flow-node-inventory:flow"]["match"])

        pop_vlan_action = None
        output_action = None

        if self.network_graph.controller == "odl":
            pop_vlan_action = {'order': 0, 'pop-vlan-action': {}}
            output_action = [{'order': 1, "output-action": {"output-node-connector": mac_intent.out_port}}]

        elif self.network_graph.controller == "ryu":
            pop_vlan_action = {"type": "POP_VLAN"}
            output_action = {"type": "OUTPUT", "port": mac_intent.out_port}

        action_list = [pop_vlan_action, output_action]

        self.populate_flow_action_instruction(flow, action_list, mac_intent.apply_immediately)
        self.push_flow(sw, flow)

        return flow

    def push_destination_host_mac_intents(self, sw, dst_intents, mac_intents, mac_forwarding_table_id):

        if mac_intents:

            if len(mac_intents) > 1:
                print "There are more than one mac intents for a single dst, will install only one"

            self.push_destination_host_mac_intent_flow(sw, mac_intents[0], mac_forwarding_table_id, 1)


    def push_vlan_push_intents(self, sw, dst_intents, push_vlan_intents, vlan_tag_push_rules_table_id):

        for push_vlan_intent in push_vlan_intents:
            flow = self.create_base_flow(sw, vlan_tag_push_rules_table_id, 1)


            # Compile instructions
            if self.network_graph.controller == "odl":

                # Compile match
                flow["flow-node-inventory:flow"]["match"] = \
                    push_vlan_intent.flow_match.generate_match_json(self.network_graph.controller,
                                                                    flow["flow-node-inventory:flow"]["match"])


                action1 = {'order': 0, 'push-vlan-action': {"ethernet-type": 0x8100,
                                                            "vlan-id": push_vlan_intent.required_vlan_id}}

                set_vlan_id_action = {'vlan-match': {"vlan-id": {"vlan-id": push_vlan_intent.required_vlan_id,
                                                                 "vlan-id-present": True}}}

                action2 = {'order': 1, 'set-field': set_vlan_id_action}

                action_list = [action1, action2]

                self.populate_flow_action_instruction(flow, action_list, push_vlan_intent.apply_immediately)

                # Also, punt such packets to the next table
                go_to_table_instruction = {"go-to-table": {"table_id": vlan_tag_push_rules_table_id + 1}, "order": 1}

                flow["flow-node-inventory:flow"]["instructions"]["instruction"].append(go_to_table_instruction)

            elif self.network_graph.controller == "ryu":

                # Compile match
                flow["match"] = push_vlan_intent.flow_match.generate_match_json(self.network_graph.controller,
                                                                                flow["match"])

                action_list = [{"type": "PUSH_VLAN", "ethertype": 0x8100},
                               {"type": "SET_FIELD", "field": "vlan_vid", "value": push_vlan_intent.required_vlan_id},
                               {"type": "GOTO_TABLE",  "table_id": str(vlan_tag_push_rules_table_id + 1)}]

                self.populate_flow_action_instruction(flow, action_list, push_vlan_intent.apply_immediately)

            self.push_flow(sw, flow)


    def push_loop_preventing_drop_rules(self, sw, loop_preventing_drop_table):

        for h_id in self.network_graph.get_experiment_host_ids():

            # Get concerned only with hosts that are directly connected to this sw
            h_obj = self.network_graph.get_node_object(h_id)
            if h_obj.switch_id != sw:
                continue

            # Get a vanilla flow
            flow = self.create_base_flow(sw, loop_preventing_drop_table, 100)


            #Compile match with in_port and destination mac address
            if self.network_graph.controller == "odl":

                host_flow_match = flow["flow-node-inventory:flow"]["match"]
                host_flow_match["in-port"] = str(h_obj.switch_port_attached)

                ethernet_match = {}
                ethernet_match["ethernet-destination"] = {"address": h_obj.mac_addr}
                host_flow_match["ethernet-match"] = ethernet_match

                # Drop is the action
                drop_action = {}
                action_list = [{"drop-action": drop_action, "order": 0}]

            elif self.network_graph.controller == "ryu":
                flow["match"]["in_port"] = str(h_obj.switch_port_attached)
                flow["match"]["eth_dst"] = h_obj.mac_addr

                # Empty list for drop action
                action_list = []

            # Make and push the flow
            self.populate_flow_action_instruction(flow, action_list, True)
            self.push_flow(sw, flow)
