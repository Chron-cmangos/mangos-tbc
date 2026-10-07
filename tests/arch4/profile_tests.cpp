#include "Memory/AllocationProfile.h"
#include <new>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <thread>
#include <cstring>

static bool verify(char const* filename, unsigned long long expectedBytes, unsigned long long expectedCount) {
    FILE* f=std::fopen(filename,"r"); if(!f)return false;
    char line[16384]; unsigned long long bytes=0,count=0;
    if(!std::fgets(line,sizeof(line),f) || !std::strstr(line,"allocation_drops=0; site_drops=0;")) {std::fclose(f);return false;}
    std::fgets(line,sizeof(line),f);
    while(std::fgets(line,sizeof(line),f)) {
        unsigned site; unsigned long long b,c;
        if(std::sscanf(line,"%u\t%llu\t%llu",&site,&b,&c)!=3) {std::fclose(f);return false;}
        bytes+=b;count+=c;
    }
    std::fclose(f); return bytes==expectedBytes && count==expectedCount;
}

void* held[128];
int main() {
    ManTech::StartAllocationProfile(0);
    for (unsigned i=0;i<128;++i) {
        held[i]=::operator new(32+i);
        if (!held[i]) return 1;
    }
    auto aligned=::operator new(512,std::align_val_t(128));
    if (reinterpret_cast<std::uintptr_t>(aligned)%128) return 2;
    ManTech::WriteAllocationProfile();
    if (!verify("arch4-heap-001.tsv",12736,129)) return 3;
    auto captured=ManTech::ReadAllocationTotals();
    if(captured.live!=12736||captured.count!=129||captured.probability!=1||!captured.recording)return 6;
    ManTech::StopAllocationProfile();
    auto untracked=::operator new(999); ::operator delete(untracked);
    for (auto p:held) ::operator delete(p);
    ::operator delete(aligned,std::align_val_t(128));
    auto released=ManTech::ReadAllocationTotals();
    if(released.live!=0||released.count!=0||released.recording||released.freed!=released.allocated)return 7;
    ManTech::WriteAllocationProfile();
    if (!verify("arch4-heap-002.tsv",0,0)) return 4;
    ManTech::StartAllocationProfile(0);
    std::thread a([]{for(int i=0;i<10000;++i){auto p=::operator new(173);::operator delete(p);}});
    std::thread b([]{for(int i=0;i<10000;++i){auto p=::operator new(197);::operator delete(p);}});
    a.join();b.join();
    ManTech::WriteAllocationProfile();
    if (!verify("arch4-heap-003.tsv",0,0)) return 5;
    std::puts("Profiler allocation/alignment/concurrent-free probes completed");
}
