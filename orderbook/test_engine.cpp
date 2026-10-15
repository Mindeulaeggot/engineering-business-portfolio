#include "engine.hpp"
#include <iostream>
#include <random>
#include <functional>
using exchange::Engine;
void check(bool ok){if(!ok)throw std::runtime_error("assertion_failed");}
int main(){int passed=0;auto test=[&](const char* name,std::function<void()> f){try{f();++passed;std::cout<<"PASS "<<name<<'\n';}catch(const std::exception& e){std::cerr<<"FAIL "<<name<<' '<<e.what()<<'\n';std::exit(1);}};
    test("price_time_fifo",[]{Engine e;e.add({"s1","a",'S',100,5});e.add({"s2","b",'S',100,5});auto t=e.add({"b1","c",'B',100,7});check(t.size()==2&&t[0].maker=="s1"&&t[0].qty==5&&t[1].qty==2);});
    test("best_price",[]{Engine e;e.add({"s1","a",'S',102,1});e.add({"s2","b",'S',100,1});auto t=e.add({"b1","c",'B',103,1});check(t[0].maker=="s2"&&t[0].price==100);});
    test("sell_crossing",[]{Engine e;e.add({"b","a",'B',100,2});auto t=e.add({"s","b",'S',90,1});check(t[0].price==100&&e.invariant());});
    test("noncrossing",[]{Engine e;e.add({"b","a",'B',90,2});check(e.add({"s","b",'S',100,2}).empty()&&e.invariant());});
    test("cancel",[]{Engine e;e.add({"b","a",'B',90,2});e.cancel("b");check(e.snapshot()=="halted=0\n");});
    test("unknown_cancel",[]{Engine e;check(e.process("CANCEL missing")=="REJECT unknown_order");});
    test("duplicate_id_after_fill",[]{Engine e;e.add({"s","a",'S',100,1});e.add({"b","b",'B',100,1});check(e.process("ADD s a S 100 1")=="REJECT duplicate_order_id");});
    test("invalid_values",[]{Engine e;check(e.process("ADD b a B -1 1").find("REJECT")==0);check(e.process("ADD b a X 1 1")=="REJECT invalid_order");});
    test("notional_limit",[]{Engine e;check(e.process("ADD b a B 1000000 101")=="REJECT notional_limit");});
    test("replace_loses_priority",[]{Engine e;e.add({"s1","a",'S',100,2});e.add({"s2","b",'S',100,2});e.replace("s1",100,2);auto t=e.add({"b1","c",'B',100,1});check(t[0].maker=="s2");});
    test("invalid_replace_atomic",[]{Engine e;e.add({"b","a",'B',90,2});auto before=e.snapshot();check(e.process("REPLACE b -1 1").find("REJECT")==0&&before==e.snapshot());});
    test("replace_crosses",[]{Engine e;e.add({"s","a",'S',100,2});e.add({"b","b",'B',90,2});auto t=e.replace("b",100,2);check(t.size()==1&&t[0].qty==2);});
    test("self_trade_cancel_resting",[]{Engine e;e.add({"s","a",'S',100,2});check(e.add({"b","a",'B',100,2}).empty()&&e.invariant());});
    test("kill_switch_cancel_allowed",[]{Engine e;e.add({"b","a",'B',90,2});e.kill(true);check(e.process("ADD x b S 100 2")=="REJECT kill_switch_active");e.cancel("b");e.kill(false);check(e.process("ADD x b S 100 2")=="OK");});
    test("malformed_command",[]{Engine e;check(e.process("ADD x a B garbage 1")=="REJECT parse_error");check(e.process("KILL 2")=="REJECT parse_error");});
    test("randomized_deterministic_replay_5000",[]{Engine a,b;std::mt19937 rng(7);std::vector<std::string> journal;
        for(int i=0;i<5000;++i){std::ostringstream cmd;cmd<<"ADD o"<<i<<" a"<<rng()%7<<' '<<(rng()%2?'B':'S')<<' '<<95+rng()%11<<' '<<1+rng()%20;journal.push_back(cmd.str());check(a.process(journal.back()).find("OK")==0);check(a.invariant());}
        for(const auto& cmd:journal)check(b.process(cmd).find("OK")==0);
        check(a.snapshot()==b.snapshot()&&b.invariant());});
    std::cout<<passed<<" tests passed\n";
}

