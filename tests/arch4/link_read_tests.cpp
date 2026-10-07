#include <string>
#include <set>
#include <regex>
#include <vector>
#include <random>
#include <thread>
#include <chrono>
#include <iostream>
#include <cstdlib>
#include <cstdint>
using uint32=std::uint32_t;
struct ChatHelper {
    static std::set<uint32> ExtractAllItemIds(std::string const&);
    static std::set<uint32> ExtractAllQuestIds(std::string const&);
};
struct LegacyChatHelper {
    static std::set<uint32> ExtractAllItemIds(std::string const&);
    static std::set<uint32> ExtractAllQuestIds(std::string const&);
};
#include "link_functions.inc"
#include "legacy_link_functions.inc"
#define CHECK(x) do {if(!(x)){std::cerr<<__LINE__<<": " #x<<'\n';std::abort();}}while(false)
template<class F> auto outcome(F f,std::string const& text){
    try {return std::make_pair(0,f(text));}
    catch(std::invalid_argument const&){return std::make_pair(1,std::set<uint32>{});}
    catch(std::out_of_range const&){return std::make_pair(2,std::set<uint32>{});}
}
int main(){
    std::vector<std::string> samples={"","plain chat","Hitem:","Hquest:-1","Hitem:0012xHitem:12", "|cffa335ee|Hitem:19019:0:0|h[Thunderfury]|h|r", "Hquest:123 Hitem:456 Hquest:123", "Hitem:2147483647", "Hitem:2147483648", "Hquest:99999999999999999999", "hitem:123 HITEM:456", "Hitem:x Hquest:0020", "Hitem:\n12"};
    std::mt19937 rng(76543);
    for(unsigned n=0;n<500;++n){
        std::string s;
        for(unsigned i=0;i<8;++i){s+=std::string(rng()%20,'a');s+=rng()%2?"Hitem:":"Hquest:";s+=std::to_string(rng()%100000);s+=rng()%2?" ":":0|h";}
        samples.push_back(std::move(s));
    }
    for(auto const& s:samples){
        CHECK(outcome(ChatHelper::ExtractAllItemIds,s)==outcome(LegacyChatHelper::ExtractAllItemIds,s));
        CHECK(outcome(ChatHelper::ExtractAllQuestIds,s)==outcome(LegacyChatHelper::ExtractAllQuestIds,s));
    }
    std::vector<std::thread> threads;
    for(unsigned n=0;n<4;++n)threads.emplace_back([]{for(unsigned i=0;i<1000;++i){
        CHECK((ChatHelper::ExtractAllItemIds("Hitem:19019 Hitem:7 Hitem:7")==std::set<uint32>{7,19019}));
        CHECK((ChatHelper::ExtractAllQuestIds("Hquest:42")==std::set<uint32>{42}));
    }});
    for(auto& t:threads)t.join();
    auto benchmark=[](auto f){auto start=std::chrono::steady_clock::now();unsigned total=0;for(unsigned n=0;n<4000;++n)total+=unsigned(f("Looking for a group to run a dungeon").size());CHECK(total==0);return std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();};
    auto legacy=benchmark(LegacyChatHelper::ExtractAllItemIds);auto current=benchmark(ChatHelper::ExtractAllItemIds);
    std::cout<<"Production parser equivalence, overflow and concurrent readers passed; 4000 plain messages legacy_ms="<<legacy<<" current_ms="<<current<<'\n';
}
