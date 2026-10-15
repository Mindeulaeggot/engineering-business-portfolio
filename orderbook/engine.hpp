#pragma once
#include <cstdint>
#include <list>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace exchange {
using Money=std::int64_t;
struct Order {std::string id,account; char side; Money price; int qty;};
struct Trade {std::string maker,taker; Money price; int qty;};
class Engine {
    using Level=std::list<Order>;
    using Book=std::map<Money,Level>;
    struct Ref {char side; Money price; Level::iterator iterator;};
    Book bids,asks;
    std::unordered_map<std::string,Ref> live;
    std::unordered_set<std::string> seen;
    bool halted=false;
    void validate(const Order& o) const {
        if(halted) throw std::runtime_error("kill_switch_active");
        if(o.id.empty()||o.account.empty()||(o.side!='B'&&o.side!='S')) throw std::runtime_error("invalid_order");
        if(o.price<=0||o.price>1000000||o.qty<=0||o.qty>100000) throw std::runtime_error("price_or_quantity_limit");
        if(o.price*o.qty>100000000) throw std::runtime_error("notional_limit");
    }
    void erase(const std::string& id) {
        auto f=live.find(id);
        if(f==live.end()) throw std::runtime_error("unknown_order");
        Ref r=f->second;Book& book=r.side=='B'?bids:asks;
        auto level=book.find(r.price);level->second.erase(r.iterator);
        if(level->second.empty())book.erase(level);
        live.erase(f);
    }
    std::vector<Trade> insert(Order o) {
        std::vector<Trade> trades;
        Book& opposite=o.side=='B'?asks:bids;
        while(o.qty>0&&!opposite.empty()) {
            auto level=o.side=='B'?opposite.begin():std::prev(opposite.end());
            if((o.side=='B'&&level->first>o.price)||(o.side=='S'&&level->first<o.price))break;
            Order& maker=level->second.front();
            // Cancel resting self-match; no fictitious same-account trade.
            if(maker.account==o.account){std::string id=maker.id;erase(id);continue;}
            int qty=std::min(o.qty,maker.qty);
            trades.push_back({maker.id,o.id,maker.price,qty});
            o.qty-=qty;maker.qty-=qty;
            if(maker.qty==0){std::string id=maker.id;erase(id);}
        }
        if(o.qty>0){Book& book=o.side=='B'?bids:asks;auto& level=book[o.price];level.push_back(o);live.emplace(o.id,Ref{o.side,o.price,std::prev(level.end())});}
        return trades;
    }
public:
    std::vector<Trade> add(Order o) {
        validate(o);
        if(seen.count(o.id))throw std::runtime_error("duplicate_order_id");
        seen.insert(o.id);return insert(o);
    }
    void cancel(const std::string& id){erase(id);}
    std::vector<Trade> replace(const std::string& id,Money price,int qty) {
        auto f=live.find(id);if(f==live.end())throw std::runtime_error("unknown_order");
        Order o=*f->second.iterator;o.price=price;o.qty=qty;
        validate(o); // Invalid modification must leave original resting order intact.
        erase(id);return insert(o); // All replacements deliberately lose time priority.
    }
    void kill(bool value){halted=value;}
    std::string snapshot() const {
        std::ostringstream s;s<<"halted="<<halted<<'\n';
        for(auto level=bids.rbegin();level!=bids.rend();++level)for(const auto& o:level->second)s<<o.side<<' '<<o.id<<' '<<o.account<<' '<<o.price<<' '<<o.qty<<'\n';
        for(const auto& level:asks)for(const auto& o:level.second)s<<o.side<<' '<<o.id<<' '<<o.account<<' '<<o.price<<' '<<o.qty<<'\n';
        return s.str();
    }
    bool invariant() const {
        if(!bids.empty()&&!asks.empty()&&bids.rbegin()->first>=asks.begin()->first)return false;
        std::size_t count=0;
        for(const Book* b:{&bids,&asks})for(const auto& level:*b){if(level.second.empty())return false;for(const auto& o:level.second){++count;if(o.qty<=0||o.price!=level.first||!live.count(o.id))return false;}}
        return count==live.size();
    }
    // Text command stream doubles as an append-only replay journal.
    std::string process(const std::string& command) {
        std::istringstream in(command);std::string op,tail;in>>op;
        try {
            std::vector<Trade> trades;
            if(op=="ADD"){Order o{};if(!(in>>o.id>>o.account>>o.side>>o.price>>o.qty)||(in>>tail))throw std::runtime_error("parse_error");trades=add(o);}
            else if(op=="CANCEL"){std::string id;if(!(in>>id)||(in>>tail))throw std::runtime_error("parse_error");cancel(id);}
            else if(op=="REPLACE"){std::string id;Money p;int q;if(!(in>>id>>p>>q)||(in>>tail))throw std::runtime_error("parse_error");trades=replace(id,p,q);}
            else if(op=="KILL"){int value;if(!(in>>value)||(in>>tail)||(value!=0&&value!=1))throw std::runtime_error("parse_error");kill(value==1);}
            else throw std::runtime_error("unknown_command");
            std::ostringstream out;out<<"OK";for(const auto& t:trades)out<<" | TRADE "<<t.maker<<' '<<t.taker<<' '<<t.price<<' '<<t.qty;
            return out.str();
        }catch(const std::runtime_error& e){return std::string("REJECT ")+e.what();}
    }
};
}

