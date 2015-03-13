import json
import time
import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as ss

# example data
data = {
"init_times" :{
    4:  [0.5, 0.6, 0.4],
    6:  [1.5, 1.6, 1.4],
    8:  [2.5, 2.6, 2.4],
    10: [3.5, 3.6, 3.4],
    12: [5.5, 5.6, 5.7]
},
"failover_update_times" : {
    4:  [5.5, 5.6, 5.4],
    6:  [6.5, 6.6, 6.4],
    8:  [7.5, 7.6, 7.4],
    10: [8.5, 8.6, 8.4],
    12: [9.5, 9.6, 9.7]
}
}

#Assuming that x-axis are keys to the data_dict

def get_x_y_err(data_dict):

    x = sorted(data_dict.keys())

    data_means = []
    data_sems = []

    for p in x:
        mean = np.mean(data_dict[p])
        sem = ss.sem(data_dict[p])
        data_means.append(mean)
        data_sems.append(sem)

    return x, data_means, data_sems


def plot_varying_size_topology(init_times, failover_update_times):

    h = []

    if init_times:

        x1, init_times_mean, init_times_sem = get_x_y_err(init_times)

        l_init_times = plt.errorbar(x1, init_times_mean, init_times_sem,
                                    label="Initialization", fmt="o")
        h.append(l_init_times)

    if failover_update_times:
        x2, failover_update_times_mean, failover_update_times_sem = get_x_y_err(failover_update_times)

        l_failover_update_times = plt.errorbar(x2, failover_update_times_mean, failover_update_times_sem,
                                            label="Single Link Failover", fmt="o")
        h.append(l_failover_update_times)


    plt.legend(handles=h, loc="upper left")
    plt.xlim((3, 20))
    plt.xlabel("Number of switches in the ring")
    plt.ylabel("Computation Time(ms)")
    plt.show()

with open("data/data_20150313_134840.json", "r") as infile:
#with open("data/data_20150313_114437.json", "r") as infile:
#with open("data/data_20150312_224744.json", "r") as infile:
    data = json.load(infile)


plot_varying_size_topology(data["init_times"], data["failover_update_times"])