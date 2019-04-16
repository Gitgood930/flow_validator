#include "flow_validator.h"
#include "thread_pool.h"

Status FlowValidatorImpl::Initialize(ServerContext* context, const NetworkGraph* ng, InitializeInfo* info) {
    cout << "Received Initialize request" << endl;
    ag = new AnalysisGraph(ng);
    info->set_successful(true);
    info->set_time_taken(0.1);
    return Status::OK;
}

Status FlowValidatorImpl::ValidatePolicy(ServerContext* context, const Policy* p, ValidatePolicyInfo* info) {
    cout << "Received ValidatePolicy request" << endl;

    ThreadPool pool(4);
    vector< future<int> > results;

    for (int i = 0; i < p->policy_statements_size(); i++) {
        auto this_ps = p->policy_statements(i);

        for (int j = 0; j <this_ps.src_zone().ports_size(); j++) {
            string src_port = this_ps.src_zone().ports(j).switch_id() + ":" + to_string(this_ps.src_zone().ports(j).port_num());
            for (int k = 0; k <this_ps.dst_zone().ports_size(); k++) {
                string dst_port = this_ps.dst_zone().ports(k).switch_id() + ":" + to_string(this_ps.dst_zone().ports(k).port_num());
                if (src_port == dst_port) {
                    continue;
                }
                policy_match_t policy_match;
                for (auto & p : this_ps.policy_match())
                {
                    policy_match[p.first] = p.second;
                }

                for (int l = 0; l <this_ps.lmbdas_size(); l++) {
                    auto this_lmbda = this_ps.lmbdas(l);

                    results.emplace_back(
                        pool.enqueue([this, src_port, dst_port, policy_match, this_lmbda] {
                            auto p = ag->find_path(src_port, dst_port, policy_match, this_lmbda);
                            ag->print_paths(src_port, dst_port, p);
                            return 0;
                        })  
                    );
                }          
            }
        }
    }
/*
    for(auto && result: results) {
        cout << result.get() << ' ';
    }
    cout << endl;
*/

    info->set_successful(true);
    info->set_time_taken(0.1);

    return Status::OK;
}

Status FlowValidatorImpl::GetTimeToDisconnect(ServerContext* context, const MonteCarloParams* mcp, TimeToDisconnectInfo* ttf) {
    cout << "Received GetTimeToDisconnect request" << endl;

    cout << "Link Failure Rate: " << mcp->link_failure_rate() << endl;
    cout << "Num Iterations: " << mcp->num_iterations() << endl;

    for (int i = 0; i < mcp->src_ports_size() ; i++) {

        string src_port = mcp->src_ports(i).switch_id() + ":" + to_string(mcp->src_ports(i).port_num());
        string dst_port = mcp->dst_ports(i).switch_id() + ":" + to_string(mcp->dst_ports(i).port_num());
        cout << "Src Port: " << src_port << " Dst Port: " << dst_port << endl;
    }

    ttf->set_mean(1.0);
    ttf->set_sd(0.05);
    ttf->set_time_taken(0.1);

    return Status::OK;
}
