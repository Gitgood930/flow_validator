#include "flow_validator.h"
#include "switch_graph.h"


Status FlowValidatorImpl::Initialize(ServerContext* context, const NetworkGraph* ng, InitializeInfo* info) {
    cout << "Received Initialize request" << endl;

    SwitchGraph sg(ng);
    sg.print_graph();
    sg.find_topological_path();

    info->set_successful(true);
    info->set_time_taken(0.1);

    return Status::OK;
}

Status FlowValidatorImpl::ValidatePolicy(ServerContext* context, const Policy* p, ValidatePolicyInfo* info) {
    cout << "Received ValidatePolicy request" << endl;

    map <Lmbda, map<PolicyPort, PolicyPort>> p_map;

    cout << p->policy_statements_size() << endl;

    for (int i = 0; i < p->policy_statements_size(); i++) {
        auto this_ps = p->policy_statements(i);

        for (int j = 0; j <this_ps.src_zone().ports_size(); j++) {
            cout << "port:" << j << endl;
            cout << this_ps.src_zone().ports(j).port_num() << endl;
            cout << this_ps.src_zone().ports(j).switch_id() << endl;
        }

        for (int j = 0; j <this_ps.dst_zone().ports_size(); j++) {
            cout << "port:" << j << endl;
            cout << this_ps.dst_zone().ports(j).port_num() << endl;
            cout << this_ps.dst_zone().ports(j).switch_id() << endl;
        }

        for (int l = 0; l <this_ps.lmbdas_size(); l++) {
            auto this_lmbda = this_ps.lmbdas(l);
            for (int k=0; k<this_lmbda.links_size(); k++) {
                cout << this_lmbda.links(k).src_node() << "--" << this_lmbda.links(k).dst_node() << endl;
            }

        }

    }
    info->set_successful(true);
    info->set_time_taken(0.1);

    return Status::OK;
}