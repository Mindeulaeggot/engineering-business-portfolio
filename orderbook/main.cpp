#include "engine.hpp"
#include <fstream>
#include <iostream>

int main(int argc,char** argv){
    if(argc!=2){std::cerr<<"Usage: orderbook <commands.txt>\n";return 2;}
    std::ifstream input(argv[1]);if(!input){std::cerr<<"Cannot read command journal\n";return 2;}
    exchange::Engine engine;std::string line;std::size_t n=0;
    while(std::getline(input,line)){if(line.empty()||line[0]=='#')continue;
        std::cout<<++n<<' '<<line<<" => "<<engine.process(line)<<'\n';
        if(!engine.invariant()){std::cerr<<"Book invariant violated\n";return 1;}
    }
    std::cout<<"FINAL SNAPSHOT\n"<<engine.snapshot();return 0;
}

