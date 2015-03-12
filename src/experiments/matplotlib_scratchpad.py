import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as ss

# example data
x = np.arange(0.1, 4, 0.5)
y1 = np.exp(-x)
y2 = np.exp(-2*x)

print type(x)
print type(y1)

#Assuming that x-axis are keys to the data_dict

def plot_varying_size_topology(init_times, failover_fix_times):

    x1 = init_times.keys()
    x2 = failover_fix_times.keys()

    init_times_mean = []
    init_times_sem = []
    for x in x1:
        init_times_mean.append(np.mean(init_times[x]))
        init_times_sem.append(ss.sem(init_times[x]))

#    for x in x2:
#        y2 = np.mean(failover_fix_times[x])
#        y2_err = ss.sem(failover_fix_times[x])

    plt.errorbar(x1, init_times_mean, init_times_sem)
#    plt.errorbar(x2, y2, y2_err)

    plt.xlabel("Number of switches in the ring")
    plt.ylabel("Computation Time(ms)")
    plt.show()


init_times = {
    4:  [0.5, 0.6, 0.4],
    6:  [1.5, 1.6, 1.4],
    8:  [2.5, 2.6, 2.4],
    10: [3.5, 3.6, 3.4],
    12: [5.5, 5.6, 5.7]
}

failover_fix_times = {
    4:  [5.5, 5.6, 5.4],
    6:  [6.5, 6.6, 6.4],
    8:  [7.5, 7.6, 7.4],
    10: [8.5, 8.6, 8.4],
    12: [9.5, 9.6, 9.7]
}

plot_varying_size_topology(init_times, failover_fix_times)