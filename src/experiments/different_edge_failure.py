__author__ = 'Rakesh Kumar'

import sys
import json
import time
import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as ss


sys.path.append("./")

from pprint import pprint

from timer import Timer
from analysis.flow_validator import FlowValidator
from controller_man import ControllerMan
from mininet_man import MininetMan
from experiment import Experiment


class DifferentEdgeFailure(Experiment):

    def __init__(self,
                 num_iterations,
                 load_config,
                 save_config,
                 controller,
                 experiment_switches):

        super(DifferentEdgeFailure, self).__init__("different_edge_failure",
                                                   num_iterations,
                                                   load_config,
                                                   save_config,
                                                   controller,
                                                   experiment_switches)


        self.edges_broken = {}
        self.data["edges_broken"] = self.edges_broken

        if not load_config and save_config:
            cm = ControllerMan(1, controller=controller)
            self.controller_port = cm.get_next()

    def trigger(self):

        self.topo_description = ("ring", 4, 1)
        ng = self.setup_network_graph(self.topo_description)

        for (node1, node2) in self.mm.synthesis_dij.primary_path_edges:
            s1 = node1[1:]
            s2 = node2[1:]
            self.data["edges_broken"][s1 + "<->" + s2] = []

        for i in range(self.num_iterations):

            fv = FlowValidator(ng)
            fv.init_port_graph()
            fv.add_hosts()
            fv.initialize_admitted_traffic()

            for (node1, node2) in self.mm.synthesis_dij.primary_path_edges:

                with Timer(verbose=True) as t:
                    fv.port_graph.remove_node_graph_edge(node1, node2)
                    fv.port_graph.add_node_graph_edge(node1, node2)

                s1 = node1[1:]
                s2 = node2[1:]
                self.data["edges_broken"][s1 + "<->" + s2].append(t.msecs)

    def plot_different_edge_failure(self):

        x, edges_broken_mean, edges_broken_sem = self.get_x_y_err(self.data["edges_broken"])
        ind = np.arange(len(x))
        width = 0.3

        plt.bar(ind + width, edges_broken_mean, yerr=edges_broken_sem, color="0.90", align='center',
                error_kw=dict(ecolor='gray', lw=2, capsize=5, capthick=2))

        plt.xticks(ind + width, tuple(x))
        plt.xlabel("Edge Broken", fontsize=18)
        plt.ylabel("Computation Time (ms)", fontsize=18)
        plt.show()

def main():

    num_iterations = 10
    load_config = False
    save_config = True
    controller = "ryu"
    experiment_switches = ["s1", "s3"]

    exp = DifferentEdgeFailure(num_iterations,
                               load_config,
                               save_config,
                               controller,
                               experiment_switches)

    exp.trigger()
    exp.dump_data()
    exp.plot_different_edge_failure()


if __name__ == "__main__":
    main()
