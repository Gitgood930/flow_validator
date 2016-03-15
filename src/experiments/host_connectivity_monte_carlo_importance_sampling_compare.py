__author__ = 'Rakesh Kumar'

import sys

sys.path.append("./")

import matplotlib.pyplot as plt
import numpy as np
import scipy.stats as ss

from collections import defaultdict
from timer import Timer
from analysis.monte_carlo_analysis import MonteCarloAnalysis
from experiment import Experiment

class HostConnectivityMonteCarloImportanceSamplingCompare(Experiment):
    def __init__(self,
                 num_iterations,
                 load_config,
                 save_config,
                 controller,
                 fanout,
                 core,
                 estimate_multipliers,
                 numbers_of_monte_carlo_runs):

        super(HostConnectivityMonteCarloImportanceSamplingCompare, self).__init__("monte_carlo",
                                                                                  num_iterations,
                                                                                  load_config,
                                                                                  save_config,
                                                                                  controller,
                                                                                  1)

        self.estimate_multipliers = estimate_multipliers

        self.fanout = fanout
        self.core = core

        self.numbers_of_monte_carlo_runs = numbers_of_monte_carlo_runs

        self.uniform_data = {
            "execution_time": defaultdict(defaultdict),
            "number_of_links_to_break_estimate": defaultdict(defaultdict),
            "number_of_links_to_break_estimate_data": defaultdict(defaultdict),
        }

        self.skewed_data = {
            "execution_time": defaultdict(defaultdict),
            "number_of_links_to_break_estimate": defaultdict(defaultdict),
            "number_of_links_to_break_estimate_data": defaultdict(defaultdict),
        }

    def perform_monte_carlo(self, num_runs):
        run_links = []
        run_values = []

        for i in xrange(num_runs):

            print "Performing Run:", i + 1

            run_value, run_broken_links = self.mca.break_random_links_until_any_pair_disconnected(verbose=False)
            run_links.append(run_broken_links)
            run_values.append(run_value)

        run_mean = np.mean(run_values)
        run_sem = ss.sem(run_values)

        #return run_links, run_values, run_mean, run_sem

        return run_mean, run_sem

    def perform_monte_carlo_importance_sampling(self, num_uniform_runs, num_runs, estimate_multiplier):

        uniform_run_mean, uniform_run_sem = self.perform_monte_carlo(num_uniform_runs)

        skewed_run_links = []
        skewed_run_values = []

        for i in xrange(num_runs):

            print "Performing Run:", i + 1

            run_value, run_broken_links =  self.mca.break_random_links_until_any_pair_disconnected_importance(uniform_run_mean * estimate_multiplier, verbose=False)
            skewed_run_links.append(run_broken_links)
            skewed_run_values.append(run_value)

        run_mean = np.mean(skewed_run_values)
        run_sem = ss.sem(skewed_run_values)

        #return skewed_run_links, skewed_run_values, run_mean, run_sem

        return run_mean, run_sem

    def trigger(self):

        print "Starting experiment..."

        for estimate_multiplier in self.estimate_multipliers:

            #self.topo_description = ("ring", 4, 1, None, None)
            self.topo_description = ("clostopo", None, 1, self.fanout, self.core)

            ng = self.setup_network_graph(self.topo_description,
                                          mininet_setup_gap=1,
                                          dst_ports_to_synthesize=None,
                                          synthesis_setup_gap=60,
                                          synthesis_scheme="IntentSynthesis")

            self.mca = MonteCarloAnalysis(ng)
            self.mca.init_network_port_graph()
            self.mca.add_hosts()
            self.mca.initialize_admitted_traffic()

            print "Initialization done."

            for total_runs in self.numbers_of_monte_carlo_runs:
                print "total_runs:", total_runs

                self.uniform_data["execution_time"][estimate_multiplier][total_runs] = []
                self.uniform_data["number_of_links_to_break_estimate"][estimate_multiplier][total_runs] = []
                self.uniform_data["number_of_links_to_break_estimate_data"][estimate_multiplier][total_runs] = []

                self.skewed_data["execution_time"][estimate_multiplier][total_runs] = []
                self.skewed_data["number_of_links_to_break_estimate"][estimate_multiplier][total_runs] = []
                self.skewed_data["number_of_links_to_break_estimate_data"][estimate_multiplier][total_runs] = []

                for i in xrange(self.num_iterations):
                    print "iteration:", i + 1

                    with Timer(verbose=True) as t:
                        est = self.perform_monte_carlo(total_runs)

                    print "est:", est[0], est[1]

                    self.uniform_data["execution_time"][estimate_multiplier][total_runs].append(t.msecs)
                    self.uniform_data["number_of_links_to_break_estimate"][estimate_multiplier][total_runs].append(total_runs)
                    self.uniform_data["number_of_links_to_break_estimate_data"][estimate_multiplier][total_runs].append(est)

                    with Timer(verbose=True) as t:
                        est = self.perform_monte_carlo_importance_sampling(10, total_runs, float(estimate_multiplier))

                    print "est:", est[0], est[1]

                    self.skewed_data["execution_time"][estimate_multiplier][total_runs].append(t.msecs)
                    self.skewed_data["number_of_links_to_break_estimate"][estimate_multiplier][total_runs].append(total_runs)
                    self.skewed_data["number_of_links_to_break_estimate_data"][estimate_multiplier][total_runs].append(est)

            self.mca.de_init_network_port_graph()

    def plot_monte_carlo(self):
        pass
        # fig = plt.figure(0)
        # self.plot_line_error_bars("execution_time",
        #                           "Number of Monte Carlo Runs",
        #                           "Execution Time (ms)",
        #                           y_scale='linear')

        # fig = plt.figure(0)
        # self.plot_line_error_bars("number_of_links_to_break_estimate",
        #                           "Number of Monte Carlo Runs",
        #                           "Estimated number of links to break",
        #                           y_scale='linear')

def main():
    num_iterations = 1
    load_config = True
    save_config = False
    controller = "ryu"

    fanout = 2
    core = 1

    numbers_of_monte_carlo_runs = [20]#[10, 20, 30]
    estimate_multipliers = ["1.0"]#, "1.25", "1.5"]

    exp = HostConnectivityMonteCarloImportanceSamplingCompare(num_iterations,
                                                              load_config,
                                                              save_config,
                                                              controller,
                                                              fanout,
                                                              core,
                                                              estimate_multipliers,
                                                              numbers_of_monte_carlo_runs)

    exp.trigger()
    exp.dump_data()

    #exp.plot_monte_carlo()

if __name__ == "__main__":
    main()
