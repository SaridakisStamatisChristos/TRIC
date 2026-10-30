# PyReachability

[![CI](https://github.com/reneveloso/PyReachability/actions/workflows/ci.yml/badge.svg)](https://github.com/reneveloso/PyReachability/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pyreachability)](https://pypi.org/project/pyreachability/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21251749.svg)](https://doi.org/10.5281/zenodo.21251749)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Fast graph reachability methods with a C++17 core and an ergonomic Python API.**

A *reachability query* asks: given a directed graph and two vertices `u` and `v`, is there
a directed path from `u` to `v`? PyReachability packages a representative, best-in-class set
of reachability **indexing methods** under a single, common interface — so you can build an
index once and answer millions of queries fast, and swap methods to fit your graph's
size/memory/query-time trade-off.

The library has a high-performance **C++17 core** exposed through **Cython** (C++ mode), an
**extensible method catalog** (each method is a plug-in implementing one interface), and a
reproducible, catalog-driven benchmark harness (`benchmarks/run_benchmark.py`).

> **Status:** v0.1.0 — **25 methods** implemented and verified against the BFS/DFS oracle.
> The static half is **all 22 static plain-reachability indexes of the CSUR 2025 survey
> (Table 1)** plus the two baselines, spanning every static index class — traversal and
> transitive-closure baselines, interval/tree-cover labeling, the 2-hop family,
> approximate transitive closure, and chain covers. Plus **one dynamic method**,
> `FelinePK` — seeded from a graph, then maintained under edge/vertex insertions and
> deletions — from outside the survey; see
> [`docs/methods.md`](docs/methods.md#beyond-the-survey-dynamic-methods-from-other-sources)
> for its provenance. See the [Roadmap](#roadmap) for what's next.

---

## Installation

From PyPI (wheels for Linux/macOS/Windows, Python 3.9–3.13):

```bash
pip install pyreachability
```

From source (a C++17 compiler and CMake ≥ 3.15 are required to build):

```bash
git clone https://github.com/reneveloso/PyReachability.git
cd PyReachability
pip install .
```

For development (editable install + test extras):

```bash
pip install -e ".[test]"
```

Pre-built wheels on PyPI (`pip install pyreachability`, no compiler needed) are planned for a
later milestone.

## Quickstart

```python
import numpy as np
from pyreachability import Graph
from pyreachability.static import BFSDFS

# Build a graph from a NumPy edge list: edges 0->1, 1->2, 2->0 (a cycle), 3 isolated.
src = np.array([0, 1, 2], dtype=np.int32)
dst = np.array([1, 2, 0], dtype=np.int32)
g = Graph.from_edges(src, dst, num_nodes=4)

# Pick a method, build its index, then query.
idx = BFSDFS()
idx.build(g)

idx.query(0, 2)        # True  (0 -> 1 -> 2)
idx.query(0, 3)        # False (3 is unreachable)
idx.query(3, 3)        # True  (reachability is reflexive)

# Batch queries: (M, 2) int array -> (M,) bool array.
pairs = np.array([[0, 2], [2, 0], [0, 3]], dtype=np.int32)
idx.query_batch(pairs) # array([ True,  True, False])
```

`from_edges` also accepts a single `(E, 2)` array of `[u, v]` rows:

```python
edges = np.array([[0, 1], [1, 2], [2, 0]], dtype=np.int32)
g = Graph.from_edges(edges, num_nodes=4)
```

Load a graph from a file (`.gz` is decompressed transparently):

```python
g = Graph.from_file("graph.txt", fmt="edgelist")        # one "u v" edge per line
g = Graph.from_file("graph.scc.gra.gz", fmt="gra")      # GRAIL/GREACH adjacency format
```

Export the edges back out (inverse of `from_edges`, reconstructed from CSR):

```python
src, dst = g.to_edges()
```

Discover available methods dynamically through the catalog:

```python
from pyreachability import catalog
catalog.methods()          # ['3hop', 'bfl', 'bfsdfs', 'chaincover', 'dl', 'dual', 'feline', 'feline-pk', 'ferrari', 'grail', 'gripp', 'hl', 'ip', 'optchain', 'oreach', 'pathhop', 'pathtree', 'pll', 'preach', 'sspi', 'tc', 'tfl', 'tol', 'treecover', 'twohop']
Method = catalog.get("bfsdfs")
idx = Method()
```

`catalog.methods()` mixes both halves; ask for one explicitly when that matters
(e.g. a benchmark whose build-once cost has no dynamic counterpart):

```python
catalog.methods(kind="static")     # the 24 build-once-then-read-only methods
catalog.methods(kind="dynamic")    # ['feline-pk']
```

Dynamic methods live in their own subpackage — the import says which half you are in:

```python
from pyreachability.dynamic import FelinePK
```

A runnable version of this walkthrough lives in [`examples/quickstart.py`](examples/quickstart.py).

## Methods

Every method implements the same [`ReachabilityIndex`](src/pyreachability/base.py) interface
(`build` / `query` / `query_batch` / `index_size_bytes`) and is registered in the catalog.
A method only enters the library if it has a peer-reviewed publication.

Each **Reference** cell names the source and links (`[N]`) to its full citation in
[References](#references).

| Method | Family | Status | Reference |
|---|---|---|---|
| `BFSDFS` | online traversal (baseline / oracle) | ✅ implemented | CLRS, *Introduction to Algorithms* [[1]](#ref-1) |
| `TC` | transitive closure (bitset) | ✅ implemented | Warshall, JACM 1962 [[2]](#ref-2) |
| `TreeCover` | tree / interval cover | ✅ implemented | Agrawal, Borgida, Jagadish, SIGMOD 1989 [[3]](#ref-3) |
| `GRAIL` | tree-cover, interval-label pruning | ✅ implemented | Yıldırım, Chaoji, Zaki, PVLDB 2010 [[4]](#ref-4) |
| `FELINE` | refined online search (2 topological orders) | ✅ implemented | Veloso, Cerf, Meira Jr., Zaki, EDBT 2014 [[5]](#ref-5) |
| `PLL` | 2-hop labeling | ✅ implemented | Yano, Akiba, Iwata, Yoshida, CIKM 2013 [[6]](#ref-6) |
| `BFL` | approximate TC (Bloom filters) | ✅ implemented | Su, Zhu, Wei, Yu, TKDE 2017 [[7]](#ref-7) |
| `ChainCover` | chain-decomposition TC compression | ✅ implemented | Jagadish, ACM TODS 1990 [[8]](#ref-8) |
| `PReaCH` | contraction hierarchies + bidirectional search | ✅ implemented | Merz & Sanders, ESA 2014 [[9]](#ref-9) |
| `TwoHop` | 2-hop labeling (near-minimum greedy cover) | ✅ implemented | Cohen, Halperin, Kaplan, Zwick, SICOMP 2003 [[10]](#ref-10) |
| `TFLabel` | 2-hop labeling via topological folding | ✅ implemented | Cheng, Huang, Wu, Fu, SIGMOD 2013 [[11]](#ref-11) |
| `TOL` | 2-hop labeling, contribution-score order | ✅ implemented | Zhu, Lin, Wang, Xiao, SIGMOD 2014 [[12]](#ref-12) |
| `HL` | hierarchical 2-hop (recursive backbone) | ✅ implemented | Jin & Wang, PVLDB 2013 [[13]](#ref-13) |
| `OReach` | constant-time observations + guided fallback | ✅ implemented | Hanauer, Schulz, Trummer, ACM JEA 2022 [[14]](#ref-14) |
| `ThreeHop` | 3-hop: chains as highways (TC-contour compression) | ✅ implemented | Jin, Xiang, Ruan, Fuhry, SIGMOD 2009 [[15]](#ref-15) |
| `PathHop` | path-hop: trees as highways (residual-TC compression) | ✅ implemented | Cai & Poon, CIKM 2010 [[16]](#ref-16) |
| `Ferrari` | budgeted exact/approx intervals + guided search | ✅ implemented | Seufert, Anand, Bedathur, Weikum, ICDE 2013 [[17]](#ref-17) |
| `DualLabeling` | tree intervals + transitive link table (sparse graphs) | ✅ implemented | Wang, He, Yang, Yu, Yu, ICDE 2006 [[18]](#ref-18) |
| `TreeSSPI` | tree-cover + predecessor index + guided search | ✅ implemented | Chen, Gupta, Kurul, VLDB 2005 [[19]](#ref-19) |
| `GRIPP` | pre/postorder order-tree instances + hop technique | ✅ implemented | Trißl & Leser, SIGMOD 2007 [[20]](#ref-20) |
| `PathTree` | path-tree cover (3-tuple labels) + residual TC | ✅ implemented | Jin, Ruan, Xiang, Wang, ACM TODS 2011 [[21]](#ref-21) |
| `IP` | independent-permutation labels (approx TC) + guided search | ✅ implemented | Wei, Yu, Lu, Jin, PVLDB 2014 [[22]](#ref-22) |
| `OptimalChainCover` | minimum-chain decomposition (Dilworth) + chain labels | ✅ implemented | Chen & Chen, ICDE 2008 [[23]](#ref-23) |
| `DL` | distribution labeling (2-hop, equivalent to PLL) | ✅ implemented | Jin & Wang, PVLDB 2013 [[13]](#ref-13) |

Together these cover all 22 static plain-reachability indexes of the CSUR 2025 survey's
Table 1, plus the two baselines — see [`docs/methods.md`](docs/methods.md) for the
source-backed coverage map (including why the four dynamic-only rows are deferred).

See [`docs/architecture.md`](docs/architecture.md) for how the pieces fit together and how to
add a new method to the catalog, [`docs/fidelity.md`](docs/fidelity.md) for how faithfully each
method follows its source publication, and [`docs/AI_GUIDE.md`](docs/AI_GUIDE.md) for contributor
conventions, the method inclusion policy, and verified references.

## Roadmap

The library is built in milestones, each producing working, tested software:

1. **Foundation** ✅ — build system, CSR graph, SCC condensation, catalog, `BFSDFS` oracle,
   property-based tests, CI.
2. **Representative methods** ✅ — `GRAIL`, `TC`, `TreeCover`, `FELINE`, `PLL` (one+ per index
   class of the survey, plus the baselines).
3. **Benchmark harness + datasets** ✅ — `benchmarks/run_benchmark.py` compares build time,
   index size, and query time across all methods vs the BFS/DFS oracle on standard DAGs
   (`bash benchmarks/fetch_datasets.sh`).
4. **Comprehensive catalog** ✅ — **all 22 static plain-reachability indexes of the CSUR 2025
   survey** (Table 1) plus the two baselines: 24 methods implemented. The method list is
   taken from a peer-reviewed survey, not chosen ad hoc — see
   [`docs/methods.md`](docs/methods.md) for the coverage map.
5. **First public release** ✅ — PyPI wheels, Zenodo DOI, GitHub Release. Docs site follows
   in v0.2.0.
6. **The dynamic half** ✅ — indexes that are *maintained* under updates rather than rebuilt:
   the `DynamicReachabilityIndex` contract (capabilities declared as data, since the published
   methods do not form a clean incremental/fully-dynamic hierarchy), `catalog.methods(kind=...)`,
   a C++ substrate under `src/cpp/dynamic/`, and its first inhabitant, `FelinePK`. A dynamic
   index maintains its own SCC condensation instead of condensing once and freezing.

Still ahead: the survey's four dynamic-only Table 1 rows — DAGGER, U2-hop, DBL, and HOPI (the
row CSUR 2025 lists as "Ralf et al.") — all fully dynamic except DBL, which is insertion-only;
and label-constrained / path-constrained reachability (edge-labeled graphs, the survey's
Table 2). See [`docs/methods.md`](docs/methods.md) for per-method citations and caveats,
including the two that affect DAGGER: it is an arXiv preprint, and its reference code is GPL v3
against this project's MIT licence, so it must be written from the paper rather than ported.

## Benchmarks

```bash
bash benchmarks/fetch_datasets.sh                     # standard SIGMOD'08 DAGs -> benchmarks/data/
python benchmarks/run_benchmark.py benchmarks/data/*.gra --csv results.csv
```

The harness builds every catalog method on each graph and reports construction time, index size,
and average query time on random pairs, checking each method against the BFS/DFS oracle. Methods
with super-linear construction are capped to smaller graphs (shown as `skip`); a tiny all-methods
graph can be generated with `python benchmarks/make_synthetic.py`.

## Development

```bash
pip install -e ".[test]"     # build + install with test deps
pytest -v                    # Python test suite (incl. property-based tests)

# C++ unit tests (doctest):
cmake -S . -B build-cpp -DCMAKE_BUILD_TYPE=Debug
cmake --build build-cpp --target cpp_tests
./build-cpp/cpp_tests
```

CI runs the suite on Ubuntu for every push to `main`; the full Linux/macOS/Windows ×
Python 3.9–3.13 matrix runs on pull requests and manual dispatches.

## Citing

If you use PyReachability in academic work, please cite it via [`CITATION.cff`](CITATION.cff)
(GitHub renders a "Cite this repository" button). The accompanying *Software Impacts* article
reference will be added on publication.

## References

Every catalog method follows a peer-reviewed publication. The [Methods](#methods) table
links each method to its entry below.

<a id="ref-1"></a>[1] T. H. Cormen, C. E. Leiserson, R. L. Rivest, and C. Stein. *Introduction to Algorithms*, 3rd ed. MIT Press, 2009.

<a id="ref-2"></a>[2] S. Warshall. A theorem on Boolean matrices. *Journal of the ACM*, 9(1):11–12, 1962. doi:10.1145/321105.321107

<a id="ref-3"></a>[3] R. Agrawal, A. Borgida, and H. V. Jagadish. Efficient management of transitive relationships in large data and knowledge bases. In *ACM SIGMOD*, pp. 253–262, 1989. doi:10.1145/67544.66950

<a id="ref-4"></a>[4] H. Yıldırım, V. Chaoji, and M. J. Zaki. GRAIL: Scalable reachability index for large graphs. *PVLDB*, 3(1):276–284, 2010. doi:10.14778/1920841.1920879

<a id="ref-5"></a>[5] R. R. Veloso, L. Cerf, W. Meira Jr., and M. J. Zaki. Reachability queries in very large graphs: A fast refined online search approach. In *EDBT*, pp. 511–522, 2014. doi:10.5441/002/edbt.2014.46

<a id="ref-6"></a>[6] Y. Yano, T. Akiba, Y. Iwata, and Y. Yoshida. Fast and scalable reachability queries on graphs by pruned labeling with landmarks and paths. In *CIKM*, pp. 1601–1606, 2013. doi:10.1145/2505515.2505724

<a id="ref-7"></a>[7] J. Su, Q. Zhu, H. Wei, and J. X. Yu. Reachability querying: Can it be even faster? *IEEE TKDE*, 29(3):683–697, 2017. doi:10.1109/TKDE.2016.2631160

<a id="ref-8"></a>[8] H. V. Jagadish. A compression technique to materialize transitive closure. *ACM TODS*, 15(4):558–598, 1990. doi:10.1145/99935.99944

<a id="ref-9"></a>[9] F. Merz and P. Sanders. PReaCH: A fast lightweight reachability index using pruning and contraction hierarchies. In *ESA*, LNCS 8737, pp. 701–712, 2014. doi:10.1007/978-3-662-44777-2_58

<a id="ref-10"></a>[10] E. Cohen, E. Halperin, H. Kaplan, and U. Zwick. Reachability and distance queries via 2-hop labels. *SIAM Journal on Computing*, 32(5):1338–1355, 2003. doi:10.1137/S0097539702403098

<a id="ref-11"></a>[11] J. Cheng, S. Huang, H. Wu, and A. W.-C. Fu. TF-Label: A topological-folding labeling scheme for reachability querying in a large graph. In *ACM SIGMOD*, pp. 193–204, 2013. doi:10.1145/2463676.2465286

<a id="ref-12"></a>[12] A. D. Zhu, W. Lin, S. Wang, and X. Xiao. Reachability queries on large dynamic graphs: A total order approach. In *ACM SIGMOD*, pp. 1323–1334, 2014. doi:10.1145/2588555.2612181

<a id="ref-13"></a>[13] R. Jin and G. Wang. Simple, fast, and scalable reachability oracle. *PVLDB*, 6(14):1978–1989, 2013. doi:10.14778/2556549.2556578 *(introduces both HL and DL)*

<a id="ref-14"></a>[14] K. Hanauer, C. Schulz, and J. Trummer. O'Reach: Even faster reachability in large graphs. *ACM Journal of Experimental Algorithmics*, 27:1–27, 2022. doi:10.1145/3556540

<a id="ref-15"></a>[15] R. Jin, Y. Xiang, N. Ruan, and D. Fuhry. 3-HOP: A high-compression indexing scheme for reachability query. In *ACM SIGMOD*, pp. 813–826, 2009. doi:10.1145/1559845.1559930

<a id="ref-16"></a>[16] J. Cai and C. K. Poon. Path-Hop: Efficiently indexing large graphs for reachability queries. In *CIKM*, pp. 119–128, 2010. doi:10.1145/1871437.1871457

<a id="ref-17"></a>[17] S. Seufert, A. Anand, S. Bedathur, and G. Weikum. FERRARI: Flexible and efficient reachability range assignment for graph indexing. In *IEEE ICDE*, pp. 1009–1020, 2013. doi:10.1109/ICDE.2013.6544893

<a id="ref-18"></a>[18] H. Wang, H. He, J. Yang, P. S. Yu, and J. X. Yu. Dual labeling: Answering graph reachability queries in constant time. In *IEEE ICDE*, p. 75, 2006. doi:10.1109/ICDE.2006.53

<a id="ref-19"></a>[19] L. Chen, A. Gupta, and M. E. Kurul. Stack-based algorithms for pattern matching on DAGs. In *VLDB*, pp. 493–504, 2005.

<a id="ref-20"></a>[20] S. Trißl and U. Leser. Fast and practical indexing and querying of very large graphs. In *ACM SIGMOD*, pp. 845–856, 2007. doi:10.1145/1247480.1247573

<a id="ref-21"></a>[21] R. Jin, N. Ruan, Y. Xiang, and H. Wang. Path-Tree: An efficient reachability indexing scheme for large directed graphs. *ACM TODS*, 36(1):7:1–7:44, 2011. doi:10.1145/1929934.1929941

<a id="ref-22"></a>[22] H. Wei, J. X. Yu, C. Lu, and R. Jin. Reachability querying: An independent permutation labeling approach. *PVLDB*, 7(12):1191–1202, 2014. doi:10.14778/2732977.2732992

<a id="ref-23"></a>[23] Y. Chen and Y. Chen. An efficient algorithm for answering graph reachability queries. In *IEEE ICDE*, pp. 893–902, 2008. doi:10.1109/ICDE.2008.4497498

## License

[MIT](LICENSE) © Renê Rodrigues Veloso
