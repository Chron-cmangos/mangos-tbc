int main() {
    ObjectGuid guid(HIGHGUID_PLAYER,1);Player player;
    auto grant=[&]{return ManTechPortableUtilityGrant::GrantToCharacter(guid,&player);};
    fixture={};assert(grant());assert((fixture.sent==std::vector<uint32>{65000,65001,65002,65004}));
    assert(!grant());assert(fixture.sent.size()==4);
    fixture={};fixture.grants={"portable_utilities_v1"};assert(grant());assert((fixture.sent==std::vector<uint32>{65002,65004}));
    fixture={};fixture.grants={"portable_mailbox_v1","portable_repair_v1"};assert(grant());assert((fixture.sent==std::vector<uint32>{65002,65004}));
    // Transfers with every combination of bag/bank, pending-mail and unsaved online ownership.
    for(unsigned mask=0;mask<16;++mask)for(unsigned storage=0;storage<3;++storage){
        fixture={};std::vector<uint32> expected;
        for(unsigned i=0;i<4;++i){auto id=i==3?65004u:65000u+i;
            if(mask&(1u<<i)){
                if(storage==0)fixture.inventory.insert(id);
                if(storage==1)fixture.mail.insert(id);
                if(storage==2)fixture.unsaved.insert(id);
            }else expected.push_back(id);
        }
        grant();assert(fixture.sent==expected);assert(fixture.grants.size()==4);
        // Once recognized as owned, removing an item does not create another one-time gift.
        fixture.inventory.clear();fixture.mail.clear();fixture.unsaved.clear();
        assert(!grant());assert(fixture.sent==expected);
    }
    // Existing players with all three older utilities receive only the new bank.
    fixture={};fixture.grants={"portable_mailbox_v1","portable_repair_v1","portable_auctioneer_v1"};
    assert(grant());assert((fixture.sent==std::vector<uint32>{65004}));assert(!grant());
    // A copied bank in pending mail is recognized even with no local grant history.
    fixture={};fixture.inventory={65000,65001,65002};fixture.mail={65004};
    assert(!grant());assert(fixture.sent.empty());assert(fixture.grants.count("portable_bank_v1"));
    fixture={};fixture.bot=true;assert(!grant());assert(fixture.sent.empty());
    fixture={};fixture.eligible=false;assert(!grant());assert(fixture.sent.empty());
    fixture={};fixture.failedRead=true;assert(!grant());assert(fixture.sent.empty());assert(fixture.grants.empty());
    fixture={};player.id=2;assert(!grant());assert(fixture.sent.empty());
    player.id=1;
    auto mount=[&]{return ManTechPortableUtilityGrant::GrantLevelRewardToCharacter(guid,&player);};
    for(auto level:{1u,39u,40u,59u,60u,80u}){
        fixture={};fixture.level=fixture.liveLevel=level;
        assert(mount()==(level>=40));assert(fixture.sent.size()==(level>=40?1u:0u));assert(!mount());
    }
    fixture={};fixture.level=39;fixture.liveLevel=40;assert(mount());
    fixture={};fixture.level=40;fixture.liveLevel=39;assert(!mount());
    for(unsigned storage=0;storage<3;++storage){
        fixture={};fixture.level=fixture.liveLevel=40;
        if(storage==0)fixture.inventory.insert(65003);
        if(storage==1)fixture.mail.insert(65003);
        if(storage==2)fixture.unsaved.insert(65003);
        assert(!mount());assert(fixture.sent.empty());assert(fixture.grants.count("mantech_black_war_raptor_v1"));
        fixture.inventory.clear();fixture.mail.clear();fixture.unsaved.clear();assert(!mount());
    }
    fixture={};fixture.level=fixture.liveLevel=40;fixture.inventory.insert(18246);assert(mount());
    fixture={};fixture.level=fixture.liveLevel=40;fixture.grants={"portable_utilities_v1"};assert(mount());
    fixture={};fixture.level=fixture.liveLevel=40;fixture.bot=true;assert(!mount());
    fixture={};fixture.level=fixture.liveLevel=40;fixture.eligible=false;assert(!mount());
    fixture={};fixture.level=fixture.liveLevel=40;fixture.failedRead=true;assert(!mount());assert(fixture.grants.empty());
    fixture={};fixture.level=fixture.liveLevel=40;player.id=2;assert(!mount());player.id=1;
    fixture={};fixture.level=40;assert(ManTechPortableUtilityGrant::GrantLevelRewardToCharacter(guid));
    fixture={};fixture.level=39;assert(!ManTechPortableUtilityGrant::GrantLevelRewardToCharacter(guid));
    fixture={};fixture.level=fixture.liveLevel=40;assert(grant());assert((fixture.sent==std::vector<uint32>{65000,65001,65002,65004,65003}));assert(!grant());
    // Account security applies equally to login/level-up and offline backfill.
    // GM mode is irrelevant: rank 1+ accounts never qualify for this reward.
    for(auto security:{0u,1u,2u,3u,4u})for(bool online:{false,true}){
        fixture={};fixture.level=fixture.liveLevel=40;fixture.security=security;
        assert(ManTechPortableUtilityGrant::GrantLevelRewardToCharacter(guid,online?&player:nullptr)==(security==SEC_PLAYER));
        assert(fixture.sent.size()==(security==SEC_PLAYER?1u:0u));
        assert(fixture.grants.size()==(security==SEC_PLAYER?1u:0u));
    }
    for(bool online:{false,true}){
        fixture={};fixture.level=fixture.liveLevel=40;fixture.accountAvailable=false;
        assert(!ManTechPortableUtilityGrant::GrantLevelRewardToCharacter(guid,online?&player:nullptr));
        assert(fixture.sent.empty() && fixture.grants.empty());
        fixture.accountAvailable=true;
        assert(ManTechPortableUtilityGrant::GrantLevelRewardToCharacter(guid,online?&player:nullptr));
    }
    // The existing portable utility policy is independent of the mount gift.
    fixture={};fixture.level=fixture.liveLevel=40;fixture.security=3;
    assert(grant());assert((fixture.sent==std::vector<uint32>{65000,65001,65002,65004}));assert(!grant());
    assert(!fixture.grants.count("mantech_black_war_raptor_v1"));
    std::cout<<"PASS rank-0-only reward: online, offline, all staff ranks, failed lookup and unchanged utilities\n";
    std::cout<<"PASS custom reward: levels, copies, bank/mail/unsaved, original item distinct, bots and one-time delivery\n";
    std::cout<<"PASS actual grant implementation: fresh, legacy, copied, partial, bank/mail/unsaved, repeat, bot, deleted, failed-read and wrong-player cases\n";
}
