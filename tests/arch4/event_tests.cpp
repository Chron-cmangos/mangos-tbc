#include "AI/EventAI/CreatureEventAI.h"
#include <cstdlib>
#include <iostream>
#include <memory>

#define CHECK(x) do { if (!(x)) { std::cerr << __LINE__ << ": " #x " failed\n"; std::abort(); } } while (false)

int main()
{
    auto generation=std::make_shared<CreatureEventAI_Event_Map>();
    CreatureEventAI_Event definition{};
    definition.event_id=123;
    (*generation)[42].push_back(definition);
    std::weak_ptr<CreatureEventAI_Event_Map> old=generation;
    {
        // The same generation pins used by CreatureEventAI keep definitions
        // alive while a newly loaded database generation replaces the map.
        std::shared_ptr<CreatureEventAI_Event_Map const> firstPin=generation, secondPin=generation;
        std::vector<CreatureEventAIHolder> first, second;
        first.emplace_back(firstPin->at(42).front());
        second.emplace_back(secondPin->at(42).front());
        first.front().timer=250;
        first.front().enabled=false;
        CHECK(second.front().timer==0 && second.front().enabled);
        CHECK(&first.front().event==&second.front().event);
        auto eventAddress=&first.front().event;
        for(int i=0;i<100;++i) first.emplace_back(firstPin->at(42).front());
        CHECK(&first.front().event==eventAddress && first.front().timer==250);
        generation=std::make_shared<CreatureEventAI_Event_Map>();
        definition.event_id=456;
        (*generation)[42].push_back(definition);
        CHECK(!old.expired() && first.front().event.event_id==123);
        CHECK(generation->at(42).front().event_id==456);
    }
    CHECK(old.expired());
    CHECK(ManTech::MemoryLedger::Read(ManTech::MemoryKind::EventHolders).count==0);
    std::cout << "EventAI shared definition lifetime and independent execution-state tests passed\n";
}
