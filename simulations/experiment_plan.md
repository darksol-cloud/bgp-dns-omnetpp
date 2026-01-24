# Simulation Plan: BGP vs DNS EID Reachability Comparison

## Objective

Quantitatively compare BGP-like (push) and DNS-like (pull) approaches for distributing DTN EID reachability information across the following dimensions:

1. **Overhead**: Message count and bytes transmitted
2. **Latency**: Time to discover/resolve an EID
3. **Scalability**: How overhead grows with network size and EID count
4. **Churn Resilience**: Protocol behavior under frequent updates/withdrawals
5. **Staleness**: Accuracy of returned information under churn

## Experimental Design

All experiments use `dnsDirectMode=true` for fair comparison (DNS over pre-routed network).

### Experiment 1: Baseline Overhead

**Goal**: Measure steady-state overhead for both protocols with no churn.

| Parameter | Values |
|-----------|--------|
| Network | 10x10 grid (100 nodes) |
| EIDs | 50 |
| Queries | 200 per client |
| Churn | None |
| Repetitions | 10 |

**Metrics**:
- Total messages sent (BGP announces vs DNS queries+responses)
- Total bytes transmitted
- Per-node state size (BGP table vs DNS cache)

**Configurations**: `Exp1_Baseline_Bgp`, `Exp1_Baseline_Dns`

---

### Experiment 2: Scalability - Network Size

**Goal**: Measure how overhead scales with network size.

| Parameter | Values |
|-----------|--------|
| Network | 5x5, 10x10, 15x15, 20x20 grids |
| EIDs | 50 (fixed) |
| Queries | 100 per client |
| Churn | None |
| Repetitions | 5 |

**Metrics**:
- Total messages as function of node count
- Convergence time (BGP) vs first-query latency (DNS)
- Per-node state size

**Configurations**: `Exp2_Scale_Bgp`, `Exp2_Scale_Dns`

---

### Experiment 3: Scalability - EID Count

**Goal**: Measure how overhead scales with number of EIDs.

| Parameter | Values |
|-----------|--------|
| Network | 10x10 grid (fixed) |
| EIDs | 10, 50, 100, 200, 500 |
| Queries | 100 per client |
| Churn | None |
| Repetitions | 5 |

**Metrics**:
- Total messages as function of EID count
- BGP table size vs DNS authority size
- Memory/state overhead

**Configurations**: `Exp3_Eids_Bgp`, `Exp3_Eids_Dns`

---

### Experiment 4: Discovery Latency

**Goal**: Compare time-to-first-answer for both approaches.

| Parameter | Values |
|-----------|--------|
| Network | 10x10 grid |
| EIDs | 50 |
| Client position | Corner (max distance from publisher) |
| Measurement | Time from publish to successful query |
| Repetitions | 10 |

**Metrics**:
- BGP: Convergence time (when client's FIB has correct entry)
- DNS: Query latency (RTT to resolver + authority)
- Discovery latency distribution

**Configurations**: `Exp4_Latency_Bgp`, `Exp4_Latency_Dns`

---

### Experiment 5: Churn Resilience

**Goal**: Compare protocol behavior under EID churn (updates/withdrawals).

| Parameter | Values |
|-----------|--------|
| Network | 10x10 grid |
| EIDs | 20 |
| Churn interval | 5s, 10s, 20s, 60s |
| Churn probability | 0.3 |
| Withdraw probability | 0.2 |
| Simulation time | 180s |
| Repetitions | 5 |

**Metrics**:
- Message overhead under churn
- Re-convergence time (BGP)
- Cache invalidation rate (DNS)

**Configurations**: `Exp5_Churn_Bgp`, `Exp5_Churn_Dns`

---

### Experiment 6: Staleness Under Churn

**Goal**: Measure accuracy of returned information when EIDs change.

| Parameter | Values |
|-----------|--------|
| Network | 10x10 grid |
| EIDs | 20 |
| Churn interval | 10s |
| DNS TTL | 15s, 30s, 60s, 120s |
| Queries | 500 |
| Simulation time | 180s |
| Repetitions | 5 |

**Metrics**:
- Stale answer rate (answers that don't match ground truth)
- Correct answer rate
- Staleness as function of TTL (DNS) vs convergence delay (BGP)

**Configurations**: `Exp6_Stale_Bgp`, `Exp6_Stale_Dns`

---

### Experiment 7: Query Pattern Impact (DNS only)

**Goal**: Measure DNS cache effectiveness under different query distributions.

| Parameter | Values |
|-----------|--------|
| Network | 10x10 grid |
| EIDs | 100 |
| Zipf alpha | 0 (uniform), 0.5, 1.0, 1.5, 2.0 |
| Queries | 1000 |
| DNS TTL | 60s |
| Repetitions | 5 |

**Metrics**:
- Cache hit rate
- Total queries to authority
- Effective overhead reduction from caching

**Configurations**: `Exp7_QueryPattern_Dns`

---

## Execution Plan

### Phase 1: Baseline & Latency (Quick validation)
```bash
# Run baseline experiments first to validate setup
./run_experiments.sh 1
./run_experiments.sh 4
```

### Phase 2: Scalability Sweeps
```bash
./run_experiments.sh 2
./run_experiments.sh 3
```

### Phase 3: Churn & Staleness
```bash
./run_experiments.sh 5
./run_experiments.sh 6
```

### Phase 4: DNS-specific Analysis
```bash
./run_experiments.sh 7
```

---

## Key Metrics to Collect

| Metric | Signal/Statistic | Unit |
|--------|------------------|------|
| Messages sent | `bgpAnnouncesSent`, `dnsQueriesSent`, `dnsResponsesSent` | count |
| Bytes sent | `messageBytesSent` | bytes |
| Table size | `bgpTableSize`, `dnsCacheSize` | entries |
| Discovery latency | `discoveryLatency` | seconds |
| Convergence time | `bgpConvergenceTime` | seconds |
| Query latency | `dnsQueryLatency` | seconds |
| Cache hits | `dnsCacheHits` | count |
| Stale answers | `staleAnswers` | count |
| Correct answers | `correctAnswers` | count |

---

## Analysis Scripts

Results will be in `results/` as `.sca` (scalars) and `.vec` (vectors) files.

Use OMNeT++ Analysis Tool or export to CSV:
```bash
opp_scavetool export -o results.csv results/*.sca
opp_scavetool export -o vectors.csv results/*.vec
```

---

## Expected Outcomes

Based on theoretical analysis:

| Dimension | BGP Expected | DNS Expected |
|-----------|--------------|--------------|
| Baseline overhead | High (N*E messages) | Low (Q queries) |
| Scalability (nodes) | O(N*E) | O(Q) |
| Scalability (EIDs) | O(N*E) | O(E) authority only |
| Latency (steady) | Instant (local FIB) | RTT to resolver |
| Latency (fresh EID) | Convergence time | Single query RTT |
| Churn overhead | High (re-propagation) | Low (re-query on miss) |
| Staleness | Low (fast updates) | Depends on TTL |

---

## Deep-Space Experiments (8-10)

These experiments explore protocol behavior under high-latency conditions typical of deep-space networks (lunar, Mars, outer planets).

### Experiment 8: Deep-Space Baseline Latency

**Goal**: Compare discovery and lookup latency as link delay increases from terrestrial to deep-space scenarios.

| Parameter | Values |
|-----------|--------|
| Network | 5x5 grid (25 nodes) - smaller for faster simulation |
| Link delay | 10ms, 100ms, 1s, 5s, 10s, 20s |
| EIDs | 20 |
| Queries | 50 per client (after convergence) |
| Churn | None |
| Repetitions | 3 |

**Link Delay Scenarios**:

| Delay | Real-World Scenario | Network Diameter (8 hops) |
|-------|---------------------|---------------------------|
| 10ms | Terrestrial | 80ms one-way |
| 100ms | Intercontinental/LEO | 800ms one-way |
| 1s | GEO satellite | 8s one-way |
| 5s | Lunar | 40s one-way |
| 10s | Lunar far-side | 80s one-way |
| 20s | Mars (close approach) | 160s one-way |

**Metrics**:
- **Convergence time** (BGP): Time until client FIB has all EIDs
- **First-query latency** (DNS): Time for first successful query
- **Subsequent lookup latency**: Time for queries after convergence/first-query
- **Total campaign time**: Time to complete all 50 queries

**Expected Results**:

| Delay | BGP Convergence | DNS First Query | BGP Lookup | DNS Lookup (no cache) |
|-------|-----------------|-----------------|------------|----------------------|
| 10ms | ~80ms | ~160ms | ~0 | ~160ms |
| 1s | ~8s | ~16s | ~0 | ~16s |
| 20s | ~160s | ~320s | ~0 | ~320s |

**Hypothesis**: BGP's local FIB provides massive advantage for subsequent lookups. At 20s delay, DNS pays 320s per uncached query vs ~0 for BGP.

**Configurations**: `Exp8_DeepSpace_Bgp`, `Exp8_DeepSpace_Dns`

---

### Experiment 9: Deep-Space DNS Caching Impact

**Goal**: Measure how DNS caching mitigates the high-latency penalty.

| Parameter | Values |
|-----------|--------|
| Network | 5×5 grid (25 nodes) |
| Link delay | 1s, 5s, 10s, 20s |
| EIDs | 20 |
| Queries | 100 per client |
| Query distribution | Zipf α=1.0 (realistic skew) |
| DNS TTL | 300s (long, to maximize cache benefit) |
| DNS caching | Enabled vs Disabled |
| Churn | None |
| Repetitions | 3 |

**Metrics**:
- **Cache hit rate**: Percentage of queries served from cache
- **Average query latency**: Mean time per query
- **Total campaign time**: Time to complete all queries
- **Authority load**: Number of queries reaching authority

**Expected Results**:

| Delay | DNS (no cache) Total | DNS (with cache) Total | Speedup |
|-------|----------------------|------------------------|---------|
| 1s | 100 × 16s = 1600s | ~20 queries × 16s = 320s | 5× |
| 20s | 100 × 320s = 32000s | ~20 queries × 320s = 6400s | 5× |

With Zipf α=1.0, expect ~80% cache hit rate after warmup, reducing authority queries by ~5×.

**Hypothesis**: Caching transforms DNS from "pay per query" to "pay per unique EID", making it competitive with BGP for repeated queries even at extreme latencies.

**Configurations**: `Exp9_DeepSpace_DnsCache`, `Exp9_DeepSpace_DnsNoCache`

---

### Experiment 10: Deep-Space Churn Resilience

**Goal**: Compare protocol behavior when EIDs change in high-latency environments.

| Parameter | Values |
|-----------|--------|
| Network | 5x5 grid (25 nodes) |
| Link delay | 5s, 10s, 20s |
| EIDs | 10 |
| Churn interval | 20s, 60s, 120s |
| Churn probability | 0.5 |
| Queries | 50 per client |
| DNS TTL | 60s |
| Simulation time | 800s-2400s (scales with delay) |
| Repetitions | 3 |

**Churn Scenarios**:
- **60s churn**: Frequent changes (challenging for both protocols)
- **120s churn**: Moderate changes
- **300s churn**: Infrequent changes (easier to track)

**Metrics**:
- **Re-convergence time** (BGP): Time to propagate updates across network
- **Answer accuracy**: Percentage of queries returning current information
- **Overhead**: Bytes transmitted for updates/re-queries
- **Staleness window**: Duration during which stale answers are returned

**Expected Results**:

| Delay | Churn | Conv/Churn Ratio | BGP Accuracy | DNS Accuracy (TTL=60s) |
|-------|-------|------------------|--------------|------------------------|
| 5s | 20s | 2.0 | ~100% | ~80% |
| 5s | 60s | 0.67 | ~100% | ~95% |
| 10s | 20s | 4.0 | ~100% | ~80% |
| 10s | 60s | 1.33 | ~100% | ~95% |
| 20s | 20s | 8.0 | ~100% | ~85% |
| 20s | 120s | 1.33 | ~100% | ~97% |

**Key Insight**: At extreme latencies with churn:
- **BGP** maintains 100% accuracy even when convergence > churn interval (updates propagate incrementally)
- **DNS** accuracy degrades when conv/churn ratio exceeds 1-2
- The critical threshold is when `convergence_time > churn_interval`

**Hypothesis**: BGP's incremental update propagation maintains correctness even when global convergence is slow, while DNS's TTL-based cache invalidation struggles when changes outpace propagation.

**Configurations**: `Exp10_DeepSpace_Churn_Bgp`, `Exp10_DeepSpace_Churn_Dns`

---

## Deep-Space Experiment Summary

| Experiment | Focus | Key Question |
|------------|-------|--------------|
| Exp8 | Baseline latency | How does lookup latency scale with link delay? |
| Exp9 | DNS caching | Can caching make DNS competitive at high latencies? |
| Exp10 | Churn at high delay | Which protocol handles churn better when convergence is slow? |

### Expected Conclusions

1. **Exp8**: BGP wins decisively for subsequent lookups (local FIB vs RTT penalty)
2. **Exp9**: DNS caching provides consistent ~12% latency reduction regardless of delay
3. **Exp10**: BGP maintains 100% accuracy even under high conv/churn ratios; DNS degrades when ratio > 1-2

### Simulation Time Estimates

| Experiment | Configs | Runs | Est. Time per Run | Total |
|------------|---------|------|-------------------|-------|
| Exp8 | 12 (6 delays × 2 protocols) | 3 | ~10 min | ~6 hours |
| Exp9 | 8 (4 delays × 2 cache modes) | 3 | ~15 min | ~6 hours |
| Exp10 | 18 (3 delays × 3 churns × 2 protocols) | 3 | ~20 min | ~18 hours |

**Total estimated runtime**: ~30 hours (can be parallelized)

---

## Execution Plan (Updated)

### Phase 5: Deep-Space Experiments
```bash
# Experiment 8: Baseline latency sweep
./run_experiments.sh 8

# Experiment 9: DNS caching impact
./run_experiments.sh 9

# Experiment 10: Churn at high latency
./run_experiments.sh 10
```
