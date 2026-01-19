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
./bgp-dns -u Cmdenv -c Exp1_Baseline_Bgp -n ../src
./bgp-dns -u Cmdenv -c Exp1_Baseline_Dns -n ../src
./bgp-dns -u Cmdenv -c Exp4_Latency_Bgp -n ../src
./bgp-dns -u Cmdenv -c Exp4_Latency_Dns -n ../src
```

### Phase 2: Scalability Sweeps
```bash
./bgp-dns -u Cmdenv -c Exp2_Scale_Bgp -n ../src
./bgp-dns -u Cmdenv -c Exp2_Scale_Dns -n ../src
./bgp-dns -u Cmdenv -c Exp3_Eids_Bgp -n ../src
./bgp-dns -u Cmdenv -c Exp3_Eids_Dns -n ../src
```

### Phase 3: Churn & Staleness
```bash
./bgp-dns -u Cmdenv -c Exp5_Churn_Bgp -n ../src
./bgp-dns -u Cmdenv -c Exp5_Churn_Dns -n ../src
./bgp-dns -u Cmdenv -c Exp6_Stale_Bgp -n ../src
./bgp-dns -u Cmdenv -c Exp6_Stale_Dns -n ../src
```

### Phase 4: DNS-specific Analysis
```bash
./bgp-dns -u Cmdenv -c Exp7_QueryPattern_Dns -n ../src
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
scavetool export -o results.csv results/*.sca
scavetool export -o vectors.csv results/*.vec
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
