CONNECTIVITY_CONSTRAINT = "Connectivity"
ISOLATION_CONSTRAINT = "Isolation"
PATH_LENGTH_CONSTRAINT = "PathLength"
LINK_AVOIDANCE_CONSTRAINT = "LinkAvoidance"


class PolicyConstraint(object):
    def __init__(self, constraint_type, constraint_params):
        self.constraint_type = constraint_type
        self.constraint_params = constraint_params

    def __str__(self):
        return "(constraint_type: " + str(self.constraint_type) +\
               ", constraint_params: " + str(self.constraint_params) + ")"

    def __repr__(self):
        return "(constraint_type: " + str(self.constraint_type) + \
               ", constraint_params: " + str(self.constraint_params) + ")"


class PolicyViolation(object):
    def __init__(self, lmbda, src_port, dst_port, constraint, counter_example):
        self.lmbda = lmbda
        self.src_port = src_port
        self.dst_port = dst_port
        self.constraint = constraint
        self.counter_example = counter_example

    def __str__(self):
        return "lmbda: " + str(self.lmbda) + \
               " src_port: " + str(self.src_port) + \
               " dst_port: " + str(self.dst_port) + \
               " constraint: " + str(self.constraint) + \
               " counter_example: " + str(self.counter_example)

    def __repr__(self):
        return " lmbda: " + str(self.lmbda) + \
               " src_port: " + str(self.src_port) + \
               " dst_port: " + str(self.dst_port) + \
               " constraint: " + str(self.constraint) + \
               " counter_example: " + str(self.counter_example)


class PolicyStatement(object):

    def __init__(self, network_graph, src_zone, dst_zone, traffic, constraints, lmbdas):
        self.network_graph = network_graph
        self.src_zone = src_zone
        self.dst_zone = dst_zone
        self.traffic = traffic
        self.constraints = constraints
        self.lmbdas = lmbdas

        # Convert constraint link tuples to objects
        for c in self.constraints:
            if c.constraint_type == LINK_AVOIDANCE_CONSTRAINT:
                converted_links = []
                for link in c.constraint_params:
                    converted_links.append(self.network_graph.get_link_data(link[0], link[1]))

                c.constraint_params = converted_links

