# Realistic Scenarios: BGP vs DNS Results

This document summarizes the results from experiments 11-13, which evaluate BGP (push) and DNS (pull) protocols in realistic DTN deployment scenarios across the latency spectrum: terrestrial disaster response, lunar exploration, and Mars missions.

---

## Experiment 11: Terrestrial Disaster Response Network

**Goal:** Validate DNS advantage in low-latency, high-mobility environments typical of disaster response operations.

### Scenario Description

A hierarchical mobile network supporting disaster response operations:
- **Command Center**: Central authority coordinating all teams
- **3 Mobile Relays**: Vehicle-mounted repeaters extending coverage
- **6 Field Teams**: First responders publishing services (medical, logistics, communications)
- **10 Drones**: Aerial reconnaissance publishing sensor data

**Network Characteristics:**
- 21 nodes total
- Link delays: 5-30ms (terrestrial wireless)
- Network diameter: ~4 hops, ~65ms worst-case
- Churn: 30s and 60s intervals (moderate mobility)

### Results

#### Network Overhead

| Churn Interval | BGP | DNS | Ratio |
|----------------|-----|-----|-------|
| 30s (high mobility) | 212.8 KB | 16.4 KB | **13× more** |
| 60s (moderate mobility) | 120.1 KB | 12.9 KB | **9× more** |

#### Service Discovery Latency

| Protocol | Discovery Latency |
|----------|-------------------|
| BGP | ~21ms (local FIB lookup after convergence) |
| DNS | ~188ms (query round-trip to authority) |

#### Answer Accuracy Under Mobility

| Churn Interval | BGP Accuracy | DNS Accuracy |
|----------------|--------------|--------------|
| 30s | 100% | 96.7% |
| 60s | 100% | 99.0% |

### Key Findings from Plots

1. **Network Overhead (Top-Left)**
   - BGP generates **13× more traffic** than DNS at 30s churn
   - Every team movement triggers network-wide UPDATE floods
   - DNS overhead stays constant regardless of mobility rate
   - The overhead gap narrows at lower churn (9× at 60s) but remains substantial

2. **Service Discovery Latency (Top-Right)**
   - DNS pays ~188ms per query (round-trip to command center)
   - BGP provides near-instant lookups (~21ms) after initial convergence
   - For disaster response, 188ms latency is acceptable for most operations
   - The 9× latency difference favors BGP for time-critical queries

3. **Answer Accuracy (Bottom-Left)**
   - Both protocols achieve near-perfect accuracy (>96%)
   - BGP maintains 100% through continuous update propagation
   - DNS achieves 96.7-99% with 30s TTL matching churn rate
   - For disaster response, both accuracy levels are operationally acceptable

4. **Protocol Comparison Summary (Bottom-Right)**
   - **Overhead**: DNS wins decisively (normalized ~0.08 vs 1.0)
   - **Latency**: BGP wins (normalized ~0.11 vs 1.0)
   - **Accuracy**: Tie (both near 100%)
   - Overall: **DNS is preferred** for disaster response due to massive overhead savings

### Bottom Line

**DNS wins for terrestrial disaster response.** The 13× overhead reduction outweighs the latency penalty because:
1. 188ms query latency is acceptable for most disaster response operations
2. Mobile teams benefit from not flooding updates on every movement
3. Centralized state at command center simplifies network management
4. Near-perfect accuracy achieved with appropriate TTL tuning

---

## Experiment 12: Lunar Artemis Network

**Goal:** Determine protocol preference for the "contested zone" where Earth-Moon delays create interesting tradeoffs.

### Scenario Description

An Artemis-era lunar exploration network:
- **Earth DSN**: Ground station providing mission support (1.3s away)
- **Lunar Gateway**: Orbital relay and local authority
- **2 Surface Bases**: South Pole habitat and Equatorial relay
- **4 Rovers**: Mobile exploration assets
- **4 Field Assets**: EVA suits and deployed sensors

**Network Characteristics:**
- 12 nodes total
- Link delays: 5ms-1.3s (lunar surface to Earth-Moon)
- Network diameter: 3 hops lunar-local (~315ms), 5 hops Earth-involved (~1.8s)
- Churn: 120s intervals (slower operations)

### Results

#### Network Overhead

| Protocol | Total Bytes |
|----------|-------------|
| BGP | 23.8 KB |
| DNS | 6.3 KB |

**Ratio: BGP uses 3.8× more bandwidth**

#### Latency by Query Type

| Query Type | BGP | DNS |
|------------|-----|-----|
| Lunar-Local | ~50ms (FIB lookup) | ~600ms (query RTT) |
| Earth-Involved | ~50ms (FIB lookup) | ~2.8s (Earth RTT) |

The dashed red line in the plot shows the 2.6s Earth-Moon round-trip threshold, highlighting where DNS becomes problematic.

#### Amortized Latency Cost

The "Amortized Latency Cost" plot shows the critical crossover analysis:
- **BGP**: Flat line at ~1.6s (one-time convergence cost)
- **DNS**: Linear growth at ~0.6s per query
- **Break-even point**: ~2.7 queries

This means BGP becomes more efficient after approximately **3 queries** for frequently-accessed services.

#### Answer Accuracy

| Protocol | Accuracy |
|----------|----------|
| BGP | 100% |
| DNS | 100% |

Both protocols achieve perfect accuracy with the 120s churn interval and 60s DNS TTL.

### Key Findings from Plots

1. **Network Overhead (Top-Left)**
   - BGP uses 23.8 KB vs DNS's 6.3 KB (3.8× ratio)
   - Lower ratio than terrestrial because fewer nodes and slower churn
   - DNS overhead remains efficient even with Earth-Moon topology

2. **Latency by Query Type (Top-Right)**
   - For **lunar-local queries**: DNS pays 600ms vs BGP's 50ms (12× slower)
   - For **Earth-involved queries**: DNS pays 2.8s vs BGP's 50ms (56× slower)
   - The 2.8s DNS query time for Earth services is operationally challenging
   - Astronauts querying Earth-based services face significant delays with DNS

3. **Amortized Latency Cost (Bottom-Left)**
   - Break-even occurs at ~2.7 queries
   - For workloads with more than 3 queries, BGP amortizes its convergence cost
   - DNS's per-query cost accumulates linearly without bound
   - At 50 queries: BGP = 1.6s total, DNS = 30s total

4. **Answer Accuracy (Bottom-Right)**
   - Both protocols achieve 100% accuracy
   - The 120s churn interval is slow enough for both to maintain consistency
   - Accuracy is not a differentiator in this scenario

### The Lunar Verdict: Contested but BGP-Leaning

The lunar scenario represents the **crossover point** between DNS and BGP dominance:

| Aspect | Winner | Rationale |
|--------|--------|-----------|
| Overhead | DNS | 3.8× less bandwidth |
| Lunar-local latency | BGP | 12× faster (50ms vs 600ms) |
| Earth-involved latency | BGP | 56× faster (50ms vs 2.8s) |
| Accuracy | Tie | Both 100% |
| Amortized cost | BGP | Wins after ~3 queries |

**Recommendation for Lunar Networks:**
- **Hybrid approach**: Use DNS for infrequent lunar-local queries, BGP for Earth-involved and frequently-accessed services
- If choosing one protocol: **BGP is preferred** because Earth-involved queries are critical for mission operations and the break-even point is reached quickly

---

## Experiment 13: Mars Exploration Network

**Goal:** Confirm BGP dominance in extreme high-latency deep-space environments.

### Scenario Description

A 2030s Mars exploration network:
- **Earth DSN**: Mission control (12-minute one-way delay)
- **Mars Relay Orbiter**: Local authority and orbital relay
- **2 Surface Habitats**: Jezero and Olympus bases
- **4 Rovers**: Mobile exploration assets
- **2 Instruments**: Deployed science packages

**Network Characteristics:**
- 10 nodes total
- Link delays: 1s-720s (Mars surface to Earth-Mars)
- Network diameter: 4 hops Mars-local (~96s), 6 hops Earth-involved (~14+ minutes)
- Churn: 300s intervals (deliberate operations)

### Results

#### BGP Convergence vs DNS Query Time

| Metric | BGP | DNS |
|--------|-----|-----|
| One-time cost | **2.0 min** (convergence) | N/A |
| Per-query cost (Mars-local) | ~0s (local FIB) | **4.0 min** |
| Per-query cost (Earth-involved) | ~0s (local FIB) | **~25 min** |

The first plot shows the stark contrast:
- **BGP**: 2.0 minute one-time convergence, then instant lookups
- **DNS**: 4.0 minutes per Mars-local query, ~25 minutes for Earth queries

#### Cumulative Query Time

The "Cumulative Query Time" plot demonstrates why DNS fails at Mars distances:
- **BGP**: Flat line at 2.0 min (one-time convergence, all subsequent lookups instant)
- **DNS**: Linear growth at 4.0 min per query
- At 10 queries: BGP = 2.0 min total, DNS = 40 min total
- At 30 queries: BGP = 2.0 min total, DNS = 120 min (2 hours!) total
- The shaded region shows where "DNS becomes prohibitive"

#### Latency by Query Destination

| Destination | BGP | DNS |
|-------------|-----|-----|
| Mars-Local | ~12s (network propagation) | ~240s (4 min query RTT) |
| Earth-Involved | ~12s (pre-propagated) | ~1480s (~25 min query RTT) |

BGP pre-propagates all EID information, so lookups are instant regardless of where the service is located. DNS must query on-demand, paying the full round-trip cost each time.

#### Network Overhead

| Protocol | Total Bytes |
|----------|-------------|
| BGP | 18.0 KB |
| DNS | 5.3 KB |

**Ratio: BGP uses 3.4× more bandwidth**

### Key Findings from Plots

1. **BGP Convergence vs DNS Query Time (Top-Left)**
   - BGP pays a 2.0 minute convergence cost upfront
   - After convergence, all BGP lookups are instant (local FIB)
   - DNS pays 4.0 minutes per Mars-local query
   - For Earth-involved queries, DNS would require ~25 minute round-trips
   - This makes DNS **completely impractical** for interactive Mars operations

2. **Cumulative Query Time (Top-Right)**
   - BGP shows a flat line at 2.0 min (convergence paid once)
   - DNS shows linear growth at 4.0 min per query
   - The divergence grows rapidly: by 10 queries, DNS costs 20× more time
   - For a typical Mars mission with hundreds of service lookups, DNS adds hours of cumulative delay
   - BGP's "pay once, use forever" model is essential for deep-space

3. **Latency by Query Destination (Bottom-Left)**
   - BGP provides consistent ~12s lookups regardless of service location (pre-propagated)
   - DNS pays 4 min for Mars-local, ~25 min for Earth-involved queries
   - The 20× to 125× latency penalty makes DNS operationally unusable

4. **Network Overhead (Bottom-Right)**
   - BGP uses 18.0 KB vs DNS's 5.3 KB (3.4× ratio)
   - The overhead difference is **irrelevant** at Mars distances
   - Bandwidth is less constrained than latency for deep-space missions
   - Spending 3.4× more bytes for instant lookups is an excellent tradeoff

### The Mars Verdict: BGP Dominates Completely

| Aspect | Winner | Margin |
|--------|--------|--------|
| Query latency | BGP | **20-125×** faster |
| Cumulative cost | BGP | 2 min vs hours for typical workloads |
| Break-even | BGP | After just **1 query** |
| Overhead | DNS | 3.4× (irrelevant at Mars distances) |
| Accuracy | Tie | Both 100% |

**BGP is the only viable option for Mars networks.** DNS's per-query latency model fundamentally breaks down when round-trips take minutes. The overhead savings from DNS are meaningless when every lookup adds 4-25 minutes of delay.

---

## Cross-Scenario Comparison

### Protocol Performance Across Latency Spectrum

| Scenario | Latency Range | Overhead Winner | Latency Winner | Overall Winner |
|----------|---------------|-----------------|----------------|----------------|
| Terrestrial | 5-30ms | DNS (13×) | BGP (9×) | **DNS** |
| Lunar | 5ms-1.3s | DNS (3.8×) | BGP (12-56×) | **BGP** (marginal) |
| Mars | 1s-12min | DNS (3.4×) | BGP (20-125×) | **BGP** (decisive) |

### The Latency Threshold

Our experiments reveal a clear pattern:

1. **Below ~100ms RTT** (Terrestrial): DNS preferred
   - Overhead savings (13×) dominate
   - Query latency acceptable for operations (~188ms)
   - Mobility benefits from centralized state

2. **100ms - 3s RTT** (Lunar): Contested, BGP-leaning
   - Overhead advantage shrinks (3.8×)
   - Earth-involved queries strongly favor BGP (56× faster)
   - Break-even at ~3 queries
   - Hybrid approach may be optimal

3. **Above ~3s RTT** (Deep-space): BGP required
   - Overhead becomes irrelevant
   - DNS per-query cost is prohibitive (4+ minutes)
   - Break-even after just 1 query
   - Only BGP's proactive model is viable

### Recommendations by Deployment Type

| Deployment | Recommended Protocol | Key Rationale |
|------------|---------------------|---------------|
| Disaster response | DNS | 13× overhead savings, 188ms latency acceptable |
| LEO satellites | DNS/Hybrid | Low latency, high churn benefits DNS |
| Lunar surface | Hybrid | DNS for infrequent local queries, BGP for Earth services |
| Lunar-Earth ops | BGP | Earth queries require pre-propagation |
| Mars surface | BGP | Only viable option at 4-min query delays |
| Deep-space probes | BGP | Per-query DNS is impossible |

---

## Conclusions

### Hypothesis Validation

1. **H1: DNS wins when query_RTT < 1s** - **CONFIRMED**
   - Terrestrial (65ms RTT): DNS clearly preferred
   - The overhead savings dominate when latency is acceptable

2. **H2: BGP wins when query_RTT > convergence_time / num_queries** - **CONFIRMED**
   - Mars scenario: BGP wins after just 1 query (2 min vs 4 min)
   - Lunar scenario: BGP wins after ~3 queries (1.6s vs 0.6s/query)

3. **H3: Lunar is the crossover point** - **CONFIRMED**
   - Lunar shows competitive metrics for both protocols
   - The 1.3s Earth-Moon delay creates genuine tradeoffs
   - Break-even at ~3 queries makes the choice workload-dependent

4. **H4: Hybrid (DNS local, BGP interplanetary) optimal for Lunar** - **PARTIALLY CONFIRMED**
   - For infrequent lunar-local queries, DNS is viable (600ms acceptable)
   - For Earth-involved queries, BGP is necessary (2.8s penalty too high)
   - A hybrid approach could combine benefits

### Final Summary

The experiments validate the fundamental tradeoff between push (BGP) and pull (DNS) architectures:

- **BGP** pays upfront during convergence but provides instant lookups forever
- **DNS** pays per-query but with minimal background overhead

As propagation delay increases, DNS's per-query cost becomes prohibitive while BGP's one-time convergence cost amortizes across all lookups. The crossover occurs around the lunar distance (~1.3s one-way), making this the most interesting design space for future DTN research.

**Key Quantitative Findings:**

| Scenario | BGP Convergence | DNS per Query | Break-even |
|----------|-----------------|---------------|------------|
| Terrestrial | ~instant | 188ms | Never (DNS always better for overhead) |
| Lunar | 1.6s | 600ms-2.8s | ~3 queries |
| Mars | 2.0 min | 4-25 min | 1 query |

For practical deployments:
- **Terrestrial DTN**: Use DNS for efficiency
- **Cislunar space**: Consider hybrid approaches based on query patterns
- **Deep-space**: Use BGP exclusively
