#include <cassert>
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <memory>
#include <set>
#include <string>
#include <vector>
#include <iostream>
using uint32 = uint32_t;
#define ENABLE_PLAYERBOTS
#define _UNIXTIME_ "UNIX_TIMESTAMP()"
enum { SEC_PLAYER = 0 };
enum { HIGHGUID_PLAYER, MAIL_NORMAL, MAIL_STATIONERY_GM, MAIL_CHECK_MASK_NONE };
struct ObjectGuid {
    uint32 id; ObjectGuid(uint32, uint32 value):id(value){}
    uint32 GetCounter() const{return id;}
    bool operator!=(ObjectGuid other) const{return id!=other.id;}
};
struct Fixture {
    bool bot=false, eligible=true, failedRead=false;
    uint32 level=1, liveLevel=1, security=SEC_PLAYER;
    bool accountAvailable=true;
    std::set<std::string> grants;
    std::set<uint32> inventory, mail, unsaved;
    std::vector<uint32> sent;
} fixture;
struct Field { uint32 value; uint32 GetUInt32() const{return value;} };
struct Result {
    Field fields[3]; Field* Fetch(){return fields;} bool NextRow(){return false;}
};
struct Database {
    void BeginTransaction(){}
    bool CommitTransactionDirect(){return true;}
    std::unique_ptr<Result> Query(char const*){return nullptr;}
    std::unique_ptr<Result> PQuery(char const* query, ...) {
        va_list args; va_start(args,query); auto guid=va_arg(args,uint32);assert(guid==1);
        if(std::string(query).find("SELECT account")==0){
            va_end(args);if(!fixture.eligible)return nullptr;
            return std::unique_ptr<Result>(new Result{{{fixture.bot?99u:1u},{fixture.level},{0}}});
        }
        assert(std::string(query).find("SELECT EXISTS")==0);
        std::string key=va_arg(args,char const*);auto item=va_arg(args,uint32);va_end(args);
        if(fixture.failedRead)return nullptr;
        bool legacy=(item==65000 || item==65001) && fixture.grants.count("portable_utilities_v1");
        return std::unique_ptr<Result>(new Result{{{uint32(fixture.grants.count(key)||legacy)},
            {uint32(fixture.inventory.count(item))},{uint32(fixture.mail.count(item))}}});
    }
    void PExecute(char const* query, ...) {
        assert(std::string(query).find("INSERT IGNORE INTO mantech_character_grants")==0);
        va_list args;va_start(args,query);assert(va_arg(args,uint32)==1);
        fixture.grants.insert(va_arg(args,char const*));va_end(args);
    }
} CharacterDatabase;
struct LoginDatabaseMock {
    std::unique_ptr<Result> PQuery(char const* query, uint32 accountId) {
        assert(std::string(query)=="SELECT gmlevel FROM account WHERE id='%u'");
        assert(accountId==1);
        if(!fixture.accountAvailable)return nullptr;
        return std::unique_ptr<Result>(new Result{{{fixture.security},{0},{0}}});
    }
} LoginDatabase;
struct Player {
    uint32 GetLevel() const{return fixture.liveLevel;}
    uint32 id=1; ObjectGuid GetObjectGuid() const{return {HIGHGUID_PLAYER,id};}
    bool HasItemCount(uint32 id,uint32 count,bool bank) const {
        assert(count==1 && bank);return fixture.unsaved.count(id)!=0;
    }
};
struct Config {bool IsInRandomAccountList(uint32 id){return id==99;}} sPlayerbotAIConfig;
struct Logger {template<class... T>void outError(char const*,T...){} template<class... T>void outString(char const*,T...){} } sLog;
struct Item {uint32 id;static Item* CreateItem(uint32 id,uint32 count,Player*){assert(count==1);return new Item{id};}};
struct MailReceiver {MailReceiver(Player*,ObjectGuid){} };
struct MailSender {MailSender(int,uint32,int){} };
struct MailDraft {
    Item* item=nullptr;std::string key;
    MailDraft(char const*){}
    MailDraft& AddItem(Item* p){item=p;return *this;}
    MailDraft& SetGrantKey(char const* k){key=k;return *this;}
    void SendMailTo(MailReceiver,MailSender,int){
        assert(item && !fixture.grants.count(key));fixture.grants.insert(key);
        fixture.mail.insert(item->id);fixture.sent.push_back(item->id);delete item;
    }
};
namespace ManTechPortableUtilityGrant {
    bool GrantToCharacter(ObjectGuid,Player* = nullptr);
    bool GrantLevelRewardToCharacter(ObjectGuid,Player* = nullptr);
    void BackfillExistingCharacters();
}
