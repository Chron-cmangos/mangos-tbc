#include "Network/AsyncSocket.hpp"
#include <cstdlib>
#include <iostream>

#define CHECK(x) do { if (!(x)) { std::cerr << __LINE__ << ": " #x " failed\n"; std::abort(); } } while (false)
class TestSocket : public MaNGOS::AsyncSocket<TestSocket>
{
public:
    explicit TestSocket(boost::asio::io_context& io) : AsyncSocket(io) {}
    bool OnOpen() override { return true; }
    bool ProcessIncomingData() override { return false; }
};

struct Pair
{
    boost::asio::io_context io;
    boost::asio::ip::tcp::acceptor acceptor{io, {boost::asio::ip::address_v4::loopback(),0}};
    boost::asio::ip::tcp::socket client{io};
    std::shared_ptr<TestSocket> server=std::make_shared<TestSocket>(io);
    Pair() { client.connect(acceptor.local_endpoint()); acceptor.accept(server->GetAsioSocket()); }
};

int main()
{
    {
        Pair pair;
        std::string expected,received(200, '\0');
        int completed=0;
        for(int i=0;i<100;++i)
        {
            std::string message=std::to_string(i/10)+std::to_string(i%10);
            expected+=message;
            pair.server->Write(message.data(),message.size(),[&](auto error,std::size_t bytes){CHECK(!error && bytes==2);++completed;});
            message.assign(2,'X'); // Pending writes must own their input immediately.
        }
        CHECK(ManTech::MemoryLedger::Read(ManTech::MemoryKind::Network).bytes==12800);
        bool read=false;
        boost::asio::async_read(pair.client,boost::asio::buffer(received),[&](auto error,std::size_t bytes){CHECK(!error && bytes==200);read=true;});
        pair.io.run();
        CHECK(read && completed==100 && received==expected);
        CHECK(ManTech::MemoryLedger::Read(ManTech::MemoryKind::Network).bytes==0);
    }
    {
        Pair pair;
        std::weak_ptr<TestSocket> weak=pair.server;
        auto self=pair.server;
        int aborted=0;
        pair.server->Write("a",1,[self](auto error,std::size_t){CHECK(!error);self->Close();});
        for(int i=0;i<10;++i)
            pair.server->Write("b",1,[self,&aborted](auto error,std::size_t){CHECK(error==boost::asio::error::operation_aborted);++aborted;});
        self.reset();pair.server.reset();
        pair.io.run();
        CHECK(aborted==10 && weak.expired());
        CHECK(ManTech::MemoryLedger::Read(ManTech::MemoryKind::Network).bytes==0);
    }
    {
        Pair pair;
        std::string oversized(9*1024*1024,'x');
        bool rejected=false;
        pair.server->Write(oversized.data(),oversized.size(),[&](auto error,std::size_t){CHECK(error==boost::asio::error::no_buffer_space);rejected=true;});
        pair.io.run();
        CHECK(rejected && pair.server->IsClosed());
        CHECK(ManTech::MemoryLedger::Read(ManTech::MemoryKind::Network).bytes==0);
    }
    std::cout << "Actual AsyncSocket: ordered delivery, owned payloads, pre-post budget and close/callback cleanup passed\n";
}
