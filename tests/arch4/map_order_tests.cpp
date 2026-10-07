#include "Util/MapUpdateOrder.h"
#include <array>
#include <vector>
#include <map>
#include <cstdint>
#include <iostream>
#include <cstdlib>
struct Job { unsigned id, diff; std::uint64_t estimatedMicros; };
#define CHECK(x) do {if(!(x))std::abort();}while(false)
double finish(std::vector<Job> const& jobs){
    std::array<double,3> workers{};
    for(auto const& j:jobs)*std::min_element(workers.begin(),workers.end())+=j.estimatedMicros;
    return *std::max_element(workers.begin(),workers.end());
}
int main(){
    std::vector<Job> jobs{{0,100,50},{1,103,52},{369,900,0},{530,107,37},{571,109,53},{609,800,0}};
    auto original=jobs;auto oldFinish=finish(jobs);ManTech::OrderMapUpdates(jobs);
    CHECK(jobs.front().id==571);CHECK(finish(jobs)<oldFinish);
    std::map<unsigned,unsigned> diffs;for(auto const& j:original)diffs.emplace(j.id,j.diff);
    for(auto const& j:jobs){CHECK(diffs.at(j.id)==j.diff);CHECK(diffs.erase(j.id)==1);}CHECK(diffs.empty());
    // No starvation: even zero-cost estimates remain in every due batch.
    CHECK(jobs[4].id==369&&jobs[5].id==609);
    for(auto& j:jobs)j.estimatedMicros=0;auto tied=jobs;ManTech::OrderMapUpdates(jobs);
    for(unsigned i=0;i<jobs.size();++i)CHECK(jobs[i].id==tied[i].id);
    jobs.clear();ManTech::OrderMapUpdates(jobs);CHECK(jobs.empty());
    jobs.push_back({77,125,999});ManTech::OrderMapUpdates(jobs);CHECK(jobs.front().diff==125);
    std::cout<<"Map batch membership, original diffs, stable ties, empty batches and heavy-tail scheduling passed\n";
}
