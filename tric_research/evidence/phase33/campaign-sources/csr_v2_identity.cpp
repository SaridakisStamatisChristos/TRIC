#define tric_detail baseline_detail
#include "previous/scc_decomposition.h"
#undef tric_detail
#include "csr_v2/scc_decomposition.h"
#include <random>
#include <iostream>
using G=std::vector<std::vector<int>>;
int main(){std::mt19937 rng(2026102807);std::size_t checks=0;
for(int n:{0,1,2,3,4,17,65,257})for(int trial=0;trial<1000;++trial){G g(n);for(int i=0;i<n*8;++i){int a=rng()%n,b=rng()%n;g[a].push_back(b);if(i%3==0)g[a].push_back(b);}baseline_detail::SccDecomposition a(g);tric_detail::SccDecomposition b(g);if(a.count!=b.count||a.component!=b.component)return 1;++checks;}
for(bool reversed:{false,true}){G g(200000);for(int i=0;i<199999;++i)g[reversed?i+1:i].push_back(reversed?i:i+1);baseline_detail::SccDecomposition a(g);tric_detail::SccDecomposition b(g);if(a.count!=b.count||a.component!=b.component)return 2;++checks;}
for(G g:{G{{-1}},G{{1}}}){bool rejected=false;try{tric_detail::SccDecomposition b(g);}catch(const std::out_of_range&){rejected=true;}if(!rejected)return 3;++checks;}
std::cout<<"{\"identical_decompositions\":"<<checks-2<<",\"invalid_edges_rejected\":2}\n";}
