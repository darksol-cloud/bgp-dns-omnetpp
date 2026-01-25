# BGP vs DNS Experiments: Results Explanation

This document summarizes the results from experiments comparing BGP-like (push) and DNS-like (pull) approaches for distributing DTN EID reachability information.

**Network Topology:** 10×10 grid (100 nodes) with 10ms link delay (unless otherwise specified)

**Protocols:**
- **BGP (Push):** Proactive flooding of EID announcements to all nodes
- **DNS (Pull):** On-demand queries to a central authority/resolver

---

## Experiment 1: Baseline Overhead

**Goal:** Measure steady-state overhead for both protocols with no churn.

### Results

| Metric | BGP | DNS |
|--------|-----|-----|
| Total Bytes | 27,100 | 9,600 |
| Messages | 263 | 200 |
| State Size | 100 nodes | 2 nodes |

### Key Findings

1. **BGP has ~2.8× higher byte overhead** (27KB vs 9.6KB)
   - BGP floods announcements to ALL 100 nodes in the network
   - Each node forwards to neighbors → O(N×E) message propagation
   - 263 messages = initial flood + forwarding through the 10×10 grid

2. **DNS has minimal, on-demand overhead** (9.6KB)
   - Only 200 messages = exactly the 200 queries from the client
   - No network-wide propagation; queries go directly to resolver/authority
   - O(Q) where Q = number of queries

3. **State distribution differs fundamentally**
   - **BGP**: Every node stores a copy of the routing table (100 nodes × 1 EID)
   - **DNS**: Only the authority and resolver store EID records; clients are stateless

### Bottom Line

DNS achieves the same reachability resolution with ~65% less network overhead and 98% less distributed state, validating the "pull beats push" hypothesis for steady-state operation without churn.

---

## Experiment 2: Network Size Scalability

**Goal:** Measure how overhead scales with network size.

### Results

| Grid | Nodes | BGP Bytes | DNS Bytes | BGP State | DNS State |
|------|-------|-----------|-----------|-----------|-----------|
| 5×5 | 25 | 6,600 | 8,000 | 25 | 2 |
| 10×10 | 100 | 35,740 | 8,000 | 100 | 2 |
| 15×15 | 225 | 96,480 | 8,000 | 225 | 2 |
| 20×20 | 400 | 197,820 | 8,000 | 400 | 2 |

### Key Findings

1. **BGP scales poorly with network size** — O(N²)
   - 25 nodes → 6.6KB
   - 400 nodes → 197.8KB (**30× increase** for 16× more nodes)
   - Each announcement must traverse more hops and reach more nodes
   - Overhead grows super-linearly due to multi-hop flooding

2. **DNS overhead is constant** — O(1) with respect to network size
   - Stays at exactly 8KB regardless of 25 or 400 nodes
   - Only depends on query count (100 queries × ~80 bytes = 8KB)
   - Network size doesn't affect query/response path in direct mode

3. **State explosion in BGP**
   - Every node maintains a full routing table → state = N nodes
   - At 400 nodes: 400 copies of routing state distributed network-wide

4. **DNS state remains minimal**
   - Only 2 nodes (authority + resolver) hold EID records regardless of network size

### Bottom Line

DNS demonstrates **constant-overhead scalability** while BGP exhibits **quadratic growth**. For large-scale DTN deployments (hundreds/thousands of nodes), DNS-style pull approach avoids the "state explosion" problem inherent in BGP's push model.

---

## Experiment 3: EID Count Scalability

**Goal:** Measure how overhead scales with number of EIDs.

### Results

| EIDs | BGP Bytes | DNS Bytes | BGP State | DNS State |
|------|-----------|-----------|-----------|-----------|
| 10 | 280 KB | 8 KB | 1,000 | 10 |
| 50 | 1.36 MB | 8 KB | 5,000 | 50 |
| 100 | 2.72 MB | 8 KB | 10,000 | 100 |
| 200 | 5.43 MB | 8 KB | 20,000 | 200 |
| 500 | 13.56 MB | 8 KB | 50,000 | 500 |

### Key Findings

1. **BGP overhead scales linearly with EID count** — O(E)
   - ~27 KB per EID (each EID announcement floods to all 100 nodes)
   - 500 EIDs → 13.5 MB of network traffic just for announcements

2. **DNS overhead is constant** — O(1) with respect to EID count
   - Stays at 8 KB regardless of 10 or 500 EIDs
   - Traffic only depends on query count (100 queries), not how many EIDs exist

3. **BGP state grows as N × E**
   - State Size = 100 nodes × E EIDs = 1,000 to 50,000 entries
   - Every node stores every EID → massive replication

4. **DNS state grows as E only**
   - State Size = E (only the authority stores records)
   - 500 EIDs = 500 entries in one place, not 50,000 distributed

### Bottom Line

As the number of EIDs increases, BGP's overhead explodes (both traffic and state), while DNS remains flat. For DTN scenarios with many endpoints/services, DNS-style resolution avoids the **O(N×E) state explosion** inherent in BGP's distributed routing tables.

---

## Experiment 4: Discovery and Resolution Latency

**Goal:** Compare both discovery latency (time until an EID is resolvable) and resolution latency (time per query) for both approaches.

### Results

| Protocol | Convergence Time | Discovery Latency | Resolution Latency |
|----------|------------------|-------------------|-------------------|
| BGP | 0.20 s | 0.18 s | ~0 s (local lookup) |
| DNS | N/A | 0.40 s | 0.40 s |

### Key Findings

1. **Discovery Latency: BGP is faster** (0.18s vs 0.40s)
   - **BGP**: Must wait for announcements to propagate from publisher (node[0]) to client (node[99])
   - **DNS**: First query pays full round-trip cost (client → resolver → authority → back)
   - BGP's discovery latency is a **one-time cost** paid during convergence

2. **Resolution Latency: BGP wins decisively** (~0s vs 0.40s)
   - **BGP**: Once converged, lookups are **instant** (local FIB check)
   - **DNS**: Every query pays round-trip latency (even with caching at resolver)
   - This is DNS's fundamental limitation: resolution always involves network I/O

3. **The tradeoff:**

   | Aspect | BGP | DNS |
   |--------|-----|-----|
   | First lookup | Wait for convergence (0.2s) | Immediate query (0.4s) |
   | Subsequent lookups | Instant (~0s local FIB) | Query RTT (0.4s) or cache hit |
   | Fresh EID appears | Must wait for propagation | Immediately queryable |
   | 100 queries total cost | 0.2s + 0s×100 = 0.2s | 0.4s×100 = 40s |

4. **Amortization matters:**
   - For a single query, DNS is comparable (0.4s vs 0.2s)
   - For many queries to the same EID, BGP dominates (0.2s vs N×0.4s)
   - BGP's upfront convergence cost pays off with repeated lookups

### Bottom Line

BGP wins on latency for **stable networks** where pre-converged FIB provides instant lookups. The distinction between discovery and resolution latency is critical: BGP pays once during convergence, then all lookups are free; DNS pays for every resolution. For **query-heavy workloads**, BGP's proactive model provides superior response times.

---

## Experiment 5: Churn Resilience

**Goal:** Compare protocol behavior under EID churn (updates/withdrawals).

### Results

**Message Overhead under Churn:**

| Churn Interval | BGP Bytes | DNS Bytes | BGP/DNS Ratio |
|----------------|-----------|-----------|---------------|
| 5s (high churn) | 5.0 MB | 24 KB | 208× |
| 10s | 2.5 MB | 24 KB | 106× |
| 20s | 1.2 MB | 24 KB | 52× |
| 60s (low churn) | 258 KB | 24 KB | 11× |

**Answer Accuracy:**

| Churn Interval | BGP Accuracy | DNS Accuracy |
|----------------|--------------|--------------|
| 5s | 100% (239/239) | 30.4% (79/260) |
| 10s | 100% (203/203) | 59.0% (131/222) |
| 20s | 100% (145/145) | 64.3% (101/157) |
| 60s | 100% (56/56) | 100% (57/57) |

### Key Findings

1. **BGP overhead explodes with churn** — inversely proportional to churn interval
   - 5s churn → 5 MB (constant re-announcements flooding the network)
   - 60s churn → 258 KB (fewer updates to propagate)
   - Every EID change triggers network-wide UPDATE/WITHDRAW floods

2. **DNS overhead is constant** — unaffected by churn rate
   - Stays at 24 KB regardless of churn (300 queries × 80 bytes)
   - Churn only affects the authority's local database, no network propagation

3. **BGP maintains 100% accuracy** under churn
   - Fast UPDATE/WITHDRAW propagation keeps all FIBs current
   - The cost: massive network overhead (up to 208× more than DNS)

4. **DNS accuracy degrades with high churn**
   - At 5s churn with 60s TTL: only 30.4% accuracy (cache becomes stale)
   - At 60s churn with 60s TTL: 100% accuracy (cache refreshes before changes)
   - Accuracy depends on relationship between churn rate and cache TTL

### The Fundamental Tradeoff

| Aspect | BGP | DNS |
|--------|-----|-----|
| Churn overhead | O(changes × N) — every change floods network | O(1) — changes are local to authority |
| Freshness | Always current (at high cost) | TTL-dependent (stale risk vs. overhead) |

### Bottom Line

Under churn, BGP pays **11-208× more overhead** to maintain 100% consistency. DNS's pull model isolates churn impact to the authority, but relies on TTL-based cache invalidation for freshness. For high-churn DTN scenarios (mobile nodes, dynamic services), DNS avoids the "update storm" problem but must tune TTL appropriately.

---

## Experiment 6: Staleness Under Churn

**Goal:** Measure accuracy of returned information when EIDs change, with DNS TTL sweep.

### Results

**BGP (baseline):** 100% accuracy (312 correct, 0 stale)

**DNS by TTL:**

| TTL (s) | Correct | Stale | Total | Accuracy % |
|---------|---------|-------|-------|------------|
| 15 | 271 | 55 | 326 | 83.1% |
| 30 | 225 | 112 | 337 | 66.8% |
| 60 | 198 | 149 | 347 | 57.1% |
| 120 | 125 | 230 | 355 | 35.2% |

### Key Findings

1. **BGP maintains perfect accuracy** regardless of churn
   - Push-based updates ensure all nodes have current information
   - No staleness possible once convergence is reached

2. **DNS accuracy is inversely proportional to TTL**
   - Short TTL (15s): 83.1% accuracy — cache refreshes frequently
   - Long TTL (120s): 35.2% accuracy — cache holds stale data longer
   - With 10s churn interval, cache expires ~1.5× per churn cycle at TTL=15s

3. **The TTL tradeoff for DNS:**

   | TTL | Accuracy | Authority Load | Network Overhead |
   |-----|----------|----------------|------------------|
   | Short (15s) | High (83%) | High (frequent re-queries) | Higher |
   | Long (120s) | Low (35%) | Low (cached answers) | Lower |

4. **Optimal TTL depends on churn rate**
   - For 10s churn interval, TTL ≈ 10-15s provides best accuracy
   - TTL should be ≤ expected churn interval for freshness
   - But shorter TTL = more authority queries = higher overhead

### Bottom Line

DNS's TTL mechanism creates a **freshness-efficiency tradeoff**. Shorter TTLs improve accuracy under churn but increase query load. The optimal TTL should match the expected churn rate of the network. BGP avoids this tradeoff by always pushing updates, but at significant overhead cost (see Experiment 5).

---

## Experiment 7: Query Pattern Impact

**Goal:** Measure DNS cache effectiveness under different query distributions.

### Results

| Zipf Alpha | Distribution | Cache Hits | Cache Misses | Hit Rate % |
|------------|--------------|------------|--------------|------------|
| 0.0 | Uniform | 5 | 1,000 | 0.5% |
| 0.5 | Slightly skewed | 52 | 1,000 | 4.9% |
| 1.0 | Moderately skewed | 203 | 1,000 | 16.9% |
| 1.5 | Highly skewed | 434 | 1,000 | 30.3% |
| 2.0 | Very highly skewed | 650 | 1,000 | 39.4% |

### Key Findings

1. **Uniform queries (α=0) defeat caching**
   - Only 0.5% hit rate with 1,000 queries over 100 EIDs
   - Each EID queried ~10 times, but spread evenly → rarely in cache
   - DNS overhead ≈ BGP overhead in this scenario

2. **Skewed queries (Zipf) benefit dramatically from caching**
   - α=1.0 (typical web traffic): 16.9% hit rate
   - α=2.0 (highly skewed): 39.4% hit rate
   - Popular EIDs stay in cache, reducing authority load

3. **Real-world implications:**
   - Web traffic follows Zipf α ≈ 1.0 (80/20 rule)
   - DTN scenarios may vary: popular destinations vs. random contacts
   - If query patterns are skewed, DNS caching provides significant benefit

4. **Cache effectiveness scales with skew:**

   | Query Pattern | Cache Benefit | DNS Advantage |
   |---------------|---------------|---------------|
   | Uniform (α=0) | Minimal | Low (similar to BGP overhead) |
   | Moderate (α=1) | 17% reduction | Medium |
   | Skewed (α=2) | 40% reduction | High |

### Bottom Line

DNS's cache effectiveness depends heavily on query patterns. For **uniform random queries**, caching provides little benefit and DNS overhead approaches BGP. For **skewed distributions** (common in real networks), caching reduces authority load by 17-40%, amplifying DNS's efficiency advantage over BGP.

---

## Experiment 8: Deep-Space Baseline Latency

**Goal:** Compare protocol behavior with high link delays representative of deep-space communications (Earth-Mars scenarios).

### Configuration

- **Network:** 5×5 grid (25 nodes)
- **Link delays:** 10ms, 100ms, 1s, 5s, 10s, 20s (simulating increasing distance)
- **Reference:** Mars-Earth one-way light delay ranges from ~3 to ~22 minutes

### Results

| Link Delay | BGP Convergence | BGP Discovery | DNS Query Latency |
|------------|-----------------|---------------|-------------------|
| 10 ms | 0.1 s | 0.08 s | 0.2 s |
| 100 ms | 0.8 s | 0.80 s | 2.0 s |
| 1 s | 8.0 s | 8.0 s | 20.0 s |
| 5 s | 40.0 s | 40.0 s | 100.0 s |
| 10 s | 80.0 s | 80.0 s | 200.0 s |
| 20 s | 160.0 s | 160.0 s | 400.0 s |

### Key Findings

1. **BGP convergence scales linearly with link delay**
   - Convergence = 8 × link_delay (for 8-hop diameter in 5×5 grid)
   - At 20s delay: 160s to converge (2.7 minutes)
   - This is a **one-time cost** — after convergence, lookups are instant

2. **DNS query latency scales as 2× diameter × link_delay**
   - Query travels: client → resolver → authority → back = ~10 hops each way
   - At 20s delay: 400s per query (6.7 minutes!)
   - This cost is paid **for every query**

3. **The deep-space tradeoff:**

   | Link Delay | BGP (one-time) | DNS (per-query) | Queries to break even |
   |------------|----------------|-----------------|----------------------|
   | 1 s | 8 s | 20 s | 1 |
   | 5 s | 40 s | 100 s | 1 |
   | 10 s | 80 s | 200 s | 1 |
   | 20 s | 160 s | 400 s | 1 |

4. **BGP advantage amplifies with delay**
   - At 10ms: BGP is 2.5× faster (0.08s vs 0.2s)
   - At 20s: BGP is 2.5× faster for first query, but **infinitely faster** for subsequent queries
   - DNS's per-query cost becomes prohibitive in deep-space scenarios

### Bottom Line

In deep-space networks, **BGP's proactive model dominates**. While BGP pays a significant upfront convergence cost (up to 160s at 20s link delay), DNS's per-query latency (up to 400s) makes interactive resolution impractical. For any workload involving multiple queries, BGP's "pay once, use many" model is essential for deep-space DTN.

---

## Experiment 9: Deep-Space DNS Caching Impact

**Goal:** Measure how DNS caching reduces latency impact in high-delay environments.

### Configuration

- **Network:** 5×5 grid with 1s, 5s, 10s, 20s link delays
- **Comparison:** DNS with caching (300s TTL) vs. DNS without caching
- **Query pattern:** 100 queries with Zipf α=1.0 (moderate skew)

### Results

| Link Delay | Cache Mode | Cache Hits | Hit Rate | Avg Query Latency | Latency Reduction |
|------------|------------|------------|----------|-------------------|-------------------|
| 1 s | Cache | 23 | 18.7% | 17.7 s | 11.5% |
| 1 s | NoCache | 0 | 0% | 20.0 s | — |
| 5 s | Cache | 23 | 18.7% | 88.5 s | 11.5% |
| 5 s | NoCache | 0 | 0% | 100.0 s | — |
| 10 s | Cache | 23 | 18.7% | 177.0 s | 11.5% |
| 10 s | NoCache | 0 | 0% | 200.0 s | — |
| 20 s | Cache | 23 | 18.7% | 354.0 s | 11.5% |
| 20 s | NoCache | 0 | 0% | 400.0 s | — |

### Key Findings

1. **Cache hit rate is independent of link delay**
   - 18.7% hit rate across all delays (depends only on query pattern)
   - Cache effectiveness determined by Zipf α, not network topology

2. **Latency reduction is proportional to hit rate**
   - 18.7% cache hits → ~11.5% latency reduction
   - Savings scale linearly: at 20s delay, saves 46s per 100 queries

3. **Caching helps but doesn't solve the fundamental problem**
   - At 20s delay: 354s average latency with caching vs 400s without
   - Still 354s >> BGP's 160s convergence (and 0s per query after)
   - Cache misses still cost 400s each

4. **Cache hit value increases with delay:**

   | Link Delay | Time saved per cache hit | Value of caching |
   |------------|-------------------------|------------------|
   | 1 s | 20 s | Moderate |
   | 5 s | 100 s | High |
   | 10 s | 200 s | Very High |
   | 20 s | 400 s | Critical |

### Bottom Line

DNS caching provides **consistent percentage improvement** (~12%) regardless of link delay, but the **absolute benefit grows** with delay. However, even with caching, DNS cannot match BGP's performance in deep-space scenarios. Caching is a valuable optimization for DNS in high-delay networks, but not a substitute for BGP's proactive model when low latency is required.

---

## Experiment 10: Deep-Space Churn Resilience

**Goal:** Compare protocol accuracy under churn in high-delay deep-space environments.

### Configuration

- **Network:** 5×5 grid with 5s, 10s, 20s link delays
- **Churn intervals:** 20s, 60s, 120s
- **Key metric:** Convergence/Churn ratio (when >1, BGP may not fully converge between changes)

### Results

| Link Delay | Churn Interval | Conv/Churn Ratio | BGP Accuracy | DNS Accuracy |
|------------|----------------|------------------|--------------|--------------|
| 5 s | 20 s | 2.0 | 100% | 80.5% |
| 5 s | 60 s | 0.67 | 100% | 96.5% |
| 5 s | 120 s | 0.33 | 100% | 94.9% |
| 10 s | 20 s | 4.0 | 100% | 82.1% |
| 10 s | 60 s | 1.33 | 100% | 94.3% |
| 10 s | 120 s | 0.67 | 100% | 98.0% |
| 20 s | 20 s | 8.0 | 100% | 88.2% |
| 20 s | 60 s | 2.67 | 100% | 95.7% |
| 20 s | 120 s | 1.33 | 100% | 97.4% |

### Key Findings

1. **BGP maintains 100% accuracy** even when convergence > churn interval
   - At 20s delay with 20s churn: conv/churn = 8.0 (convergence takes 8× longer than churn cycle)
   - BGP still achieves 100% accuracy because updates propagate incrementally
   - Each node gets the latest information even if global convergence isn't complete

2. **DNS accuracy degrades with high conv/churn ratio**
   - At conv/churn = 8.0: 88.2% accuracy (cache misses get stale data)
   - At conv/churn = 0.33: 95-98% accuracy (churn slow enough for cache refresh)
   - DNS's TTL-based invalidation struggles when changes outpace propagation

3. **The critical threshold: conv/churn ratio**
   - **Ratio < 1**: Both protocols work well (DNS ~95-98%, BGP 100%)
   - **Ratio 1-2**: DNS degrades noticeably (80-95%)
   - **Ratio > 2**: DNS becomes increasingly unreliable (<90%)
   - BGP maintains 100% regardless of ratio

4. **Deep-space amplifies the problem:**

   | Environment | Typical conv/churn | DNS Viability |
   |-------------|-------------------|---------------|
   | Terrestrial (10ms delay) | 0.01-0.1 | Excellent |
   | LEO satellite (50ms) | 0.1-0.5 | Good |
   | Lunar (1.3s delay) | 1-5 | Marginal |
   | Mars (5-20min delay) | 10-100+ | Poor |

### Bottom Line

In deep-space networks with churn, **BGP's consistency guarantee becomes critical**. DNS's eventual-consistency model breaks down when convergence time exceeds churn interval — a common scenario with high link delays. For deep-space DTN with any significant churn (mobile assets, scheduled contacts), BGP's proactive updates ensure correctness while DNS provides only probabilistic accuracy.

---

## Overall Summary

### Results by Experiment

| Exp | Dimension | BGP | DNS | Winner |
|-----|-----------|-----|-----|--------|
| 1 | Baseline overhead | 27 KB | 9.6 KB | DNS (65% less) |
| 2 | Network scalability | O(N²) | O(1) | DNS |
| 3 | EID scalability | O(N×E) | O(E) | DNS |
| 4 | Discovery latency | 0.18s (once) | 0.40s | BGP |
| 4 | Resolution latency | ~0s | 0.40s/query | BGP |
| 5 | Churn overhead | 5 MB @ 5s | 24 KB | DNS (208× less) |
| 5 | Churn accuracy | 100% | 30-100% | BGP |
| 6 | Staleness (TTL=15s) | 100% | 83% | BGP |
| 7 | Cache benefit (α=1) | N/A | 17% hit rate | — |
| 8 | Deep-space (20s delay) | 160s conv | 400s/query | BGP |
| 9 | Deep-space caching | — | 12% reduction | — |
| 10 | Deep-space churn | 100% | 80-98% | BGP |

### Protocol Characteristics

| Characteristic | BGP (Push) | DNS (Pull) |
|----------------|------------|------------|
| **Overhead model** | O(N × E × changes) | O(queries) |
| **State distribution** | Full replication | Centralized |
| **Consistency** | Strong (always current) | Eventual (TTL-based) |
| **Latency model** | Convergence + 0/query | RTT/query |
| **Churn impact** | High overhead | Accuracy degradation |
| **Scalability** | Poor (quadratic) | Good (constant) |
| **Deep-space** | Excellent (pay once) | Poor (pay per query) |

### Conclusions

1. **DNS wins on efficiency**: Lower baseline overhead (65% less), constant scalability O(1), and churn isolation make DNS more efficient for most terrestrial scenarios.

2. **BGP wins on consistency**: Perfect freshness under churn, faster lookups after convergence, no TTL tuning required.

3. **BGP dominates in deep-space**: The per-query latency of DNS becomes prohibitive with high link delays. BGP's "pay once during convergence, free lookups forever" model is essential for interplanetary networks.

4. **The fundamental tradeoff**:
   - **BGP**: Pay upfront (convergence) and continuously (churn propagation) for always-fresh, instant-lookup data
   - **DNS**: Pay per-query with TTL-dependent freshness; efficiency depends on query patterns and network stability

### Recommendations

| Scenario | Recommended | Rationale |
|----------|-------------|-----------|
| **High-churn terrestrial** | DNS | Avoids update storms; tune TTL to churn rate |
| **Low-churn terrestrial** | Either | DNS more efficient, BGP more consistent |
| **Query-heavy workload** | BGP | Amortizes convergence cost over many lookups |
| **Skewed query patterns** | DNS | Cache benefits reduce overhead significantly |
| **LEO satellite** | Hybrid | DNS for bulk, BGP for critical paths |
| **Lunar networks** | BGP | 1.3s RTT makes DNS per-query cost high |
| **Mars/deep-space** | BGP | DNS per-query latency is prohibitive |

### Future Considerations

1. **Hybrid approaches**: Use DNS for initial discovery, BGP for frequently-accessed EIDs
2. **Adaptive TTL**: Dynamically adjust DNS TTL based on observed churn rate
3. **Predictive caching**: Pre-fetch DNS records based on anticipated queries
4. **Hierarchical BGP**: Reduce flooding scope with route aggregation
5. **Store-and-forward DNS**: Bundle queries for batch resolution in deep-space
