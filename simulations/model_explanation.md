# Methods: BGP-like vs DNS-like Protocol Models for DTN EID Reachability Distribution

This document provides a comprehensive technical description of the simulation models, protocols, and metrics used to evaluate proactive (BGP-like) versus reactive (DNS-like) approaches for distributing Endpoint Identifier (EID) reachability information in Delay-Tolerant Networks (DTNs).

---

## 1. Problem Formulation

### 1.1 System Model

We consider a DTN consisting of $N$ nodes interconnected by links with propagation delay $d_{ij}$ between nodes $i$ and $j$. Each node may host Bundle Protocol (BP) agents identified by unique EIDs. The fundamental problem is: **how should nodes discover the Convergence-Layer Adapter (CLA) endpoint responsible for a given EID?**

Let $\mathcal{E} = \{e_1, e_2, \ldots, e_M\}$ denote the set of EIDs in the network. For each EID $e_k$, there exists exactly one authoritative endpoint:

$$\text{endpoint}(e_k) = \langle \text{nodeId}, \text{claProtocol}, \text{port} \rangle$$

The goal is to enable any node $i$ to resolve $\text{endpoint}(e_k)$ with:
- **Correctness**: The resolved endpoint matches the current authoritative binding
- **Timeliness**: Resolution completes within acceptable latency bounds
- **Efficiency**: Minimal network overhead and state distribution

### 1.2 Protocol Paradigms

We compare two fundamental paradigms:

**Proactive (Push) Model — BGP-like:**
- EID bindings are flooded to all nodes upon publication
- Each node maintains a local routing table with all known EIDs
- Resolution is instantaneous (local table lookup)
- Cost: $O(N \cdot M)$ distributed state; $O(N \cdot M \cdot C)$ messages under churn

**Reactive (Pull) Model — DNS-like:**
- EID bindings are stored at authoritative servers
- Nodes query on-demand with optional caching
- Resolution requires network round-trip(s)
- Cost: $O(M)$ centralized state; $O(Q)$ messages where $Q$ = query count

---

## 2. Network Model

### 2.1 Topology

The primary experimental topology is a two-dimensional grid network:

$$G = (V, E) \text{ where } |V| = w \times h$$

Nodes are indexed $v_{i,j}$ for $i \in [0, w-1], j \in [0, h-1]$, with edges connecting adjacent nodes:

$$E = \{(v_{i,j}, v_{i',j'}) : |i-i'| + |j-j'| = 1\}$$

The network diameter (maximum shortest path) for a $w \times h$ grid is:

$$D = (w-1) + (h-1) = w + h - 2$$

For a 10×10 grid: $D = 18$ hops.

### 2.2 Channel Model

All links are modeled as delay channels with configurable propagation delay $d$:

$$\text{latency}(m) = d \cdot \text{hopCount}(m)$$

Default parameters:
- Standard links: $d = 10$ ms
- Deep-space links: $d \in \{1, 5, 10, 20\}$ s

The channel model abstracts transmission time, focusing on propagation delay as appropriate for control-plane traffic with small message sizes.

### 2.3 Node Architecture

Each node implements both protocols (selectively enabled):

```
EidNode:
├── BGP Module (bgpEnabled)
│   ├── bgpTable: map<int, BgpEntry>
│   └── publishedVersions: map<int, int>
├── DNS Module (dnsEnabled)
│   ├── dnsCache: map<int, DnsCacheEntry>      [if isResolver]
│   ├── dnsAuthorityDb: map<int, DnsAuthRecord> [if isAuthority]
│   └── pendingQueries: map<int, PendingQuery>
└── Role Flags
    ├── isPublisher, isClient
    ├── isResolver, isAuthority
    └── resolverNodeId, authorityNodeId
```

---

## 3. BGP-like Protocol Model

### 3.1 Data Structures

**Routing Table Entry:**
```cpp
struct BgpEntry {
    int eid;              // Endpoint Identifier
    int originId;         // Publishing node ID
    int nextHop;          // Gate index for forwarding
    int nextHopNodeId;    // Next-hop node ID
    int pathLength;       // Distance (hop count)
    int version;          // Update sequence number
    EndpointInfo endpoint; // CLA binding
    simtime_t lastUpdateTime;
    vector<int> path;     // Full path vector (loop detection)
};
```

The routing table is indexed by EID: $\text{bgpTable}: \mathbb{Z}^+ \to \text{BgpEntry}$

### 3.2 Message Types

| Message | Fields | Size (bytes) |
|---------|--------|--------------|
| `BgpAnnounce` | eid, originId, pathLength, version, endpoint, originTime, path[] | $64 + 4|\text{path}|$ |
| `BgpWithdraw` | eid, originId, version, originTime | 32 |

### 3.3 Publication Algorithm

When node $p$ publishes EID $e$ with endpoint $\epsilon$:

1. **Local Table Update:**
   $$\text{bgpTable}[e] \leftarrow \langle e, p, \text{self}, p, 0, v, \epsilon, t_{\text{now}}, [p] \rangle$$

2. **Version Tracking:**
   $$v \leftarrow \text{publishedVersions}[e] + 1$$

3. **Announcement Construction:**
   $$m \leftarrow \text{BgpAnnounce}(e, p, 0, v, \epsilon, t_{\text{now}}, [p])$$

4. **Flooding:**
   $$\forall g \in \text{neighborGates}: \text{send}(m, g)$$

### 3.4 Announcement Processing

Upon receiving announcement $m$ at node $n$ from gate $g_{\text{in}}$:

**Step 1: Loop Detection**
$$\text{if } n \in m.\text{path} \Rightarrow \text{discard}(m)$$

**Step 2: Path Extension**
$$\text{path}' \leftarrow m.\text{path} \cup \{n\}$$
$$\text{pathLength}' \leftarrow m.\text{pathLength} + 1$$

**Step 3: Acceptance Decision**

Let $\text{existing} = \text{bgpTable}[m.\text{eid}]$. Accept if any condition holds:

$$\text{accept}(m) = \begin{cases}
\text{true} & \text{if } \nexists \text{existing} \\
\text{true} & \text{if } m.\text{originId} = \text{existing}.\text{originId} \land m.\text{version} > \text{existing}.\text{version} \\
\text{true} & \text{if } \text{pathLength}' < \text{existing}.\text{pathLength} \\
\text{true} & \text{if } \text{pathLength}' = \text{existing}.\text{pathLength} \land m.\text{originId} < \text{existing}.\text{originId} \\
\text{false} & \text{otherwise}
\end{cases}$$

**Step 4: Table Update and Forwarding**

If accepted:
$$\text{bgpTable}[e] \leftarrow \langle e, m.\text{originId}, g_{\text{in}}, \text{sender}, \text{pathLength}', m.\text{version}, m.\text{endpoint}, t_{\text{now}}, \text{path}' \rangle$$

$$m' \leftarrow m \text{ with updated path, pathLength}$$
$$\forall g \in \text{neighborGates} \setminus \{g_{\text{in}}\}: \text{send}(m', g)$$

### 3.5 Withdrawal Processing

Withdrawal $w$ for EID $e$ is processed only if:
1. $w.\text{originId}$ matches the current entry's origin
2. $w.\text{version} \geq \text{existing}.\text{version}$

Upon acceptance:
$$\text{bgpTable}.\text{erase}(e)$$
$$\forall g \in \text{neighborGates} \setminus \{g_{\text{in}}\}: \text{send}(w, g)$$

### 3.6 Convergence Analysis

**Theorem (BGP Convergence Time):** For a grid network with diameter $D$ and link delay $d$, the convergence time for a single EID publication is:

$$T_{\text{conv}}^{\text{BGP}} = D \cdot d$$

*Proof:* The announcement propagates via shortest paths. The last node to receive the announcement is at distance $D$ hops from the publisher. Each hop incurs delay $d$. □

For a 10×10 grid with $d = 10$ ms: $T_{\text{conv}}^{\text{BGP}} = 18 \times 0.01 = 0.18$ s

### 3.7 State Complexity

**Per-node state:** $O(M)$ where $M$ = number of EIDs

**Network-wide state:** $O(N \cdot M)$ — full replication

**Message complexity per publication:** $O(N \cdot |E|)$ where $|E|$ = number of edges

For grid: $|E| \approx 2N$, so $O(N)$ messages per EID publication.

---

## 4. DNS-like Protocol Model

### 4.1 Data Structures

**Authority Record:**
```cpp
struct DnsAuthorityRecord {
    int eid;
    int publisherId;
    EndpointInfo endpoint;
    int ttl;                  // Time-to-live (seconds)
    int version;
    simtime_t lastChangedTime; // For staleness detection
};
```

**Cache Entry:**
```cpp
struct DnsCacheEntry {
    int eid;
    EndpointInfo endpoint;
    int ttl;
    simtime_t expiryTime;     // = insertTime + ttl
    simtime_t recordTime;     // Authority's lastChangedTime
    bool authoritative;

    bool isExpired() { return simTime() >= expiryTime; }
};
```

### 4.2 Message Types

| Message | Fields | Size (bytes) |
|---------|--------|--------------|
| `DnsQuery` | eid, queryId, clientId, hopCount, queryTime | 48 |
| `DnsResponse` | eid, queryId, found, endpoint, ttl, cacheHit, authoritative, recordTime, hopCount | 80 |
| `DnsRegister` | eid, publisherId, endpoint, ttl, version | 72 |
| `DnsDeregister` | eid, publisherId, version | 24 |

### 4.3 Registration (Publication)

When publisher $p$ registers EID $e$ at authority $a$:

**If $p = a$ (local authority):**
$$\text{dnsAuthorityDb}[e] \leftarrow \langle e, p, \epsilon, \tau, v, t_{\text{now}} \rangle$$

**If $p \neq a$ (remote authority):**
$$\text{send}(\text{DnsRegister}(e, p, \epsilon, \tau, v), a)$$

Authority assignment uses modular hashing:
$$a = (e \mod |\mathcal{A}|) + a_{\text{first}}$$

where $\mathcal{A}$ is the set of authority nodes.

### 4.4 Query Resolution

**Client-initiated query for EID $e$:**

1. **Local Cache Check:**
   $$\text{if } e \in \text{dnsCache} \land \neg\text{dnsCache}[e].\text{isExpired}() \Rightarrow \text{return cache hit}$$

2. **Cache Miss → Forward to Resolver:**
   $$q \leftarrow \text{DnsQuery}(e, \text{nextQueryId}++, n, 0, t_{\text{now}})$$
   $$\text{send}(q, \text{resolverNodeId})$$

**Resolver processing:**

1. **Cache Check:**
   $$\text{if } e \in \text{dnsCache} \land \neg\text{dnsCache}[e].\text{isExpired}() \Rightarrow \text{respond from cache}$$

2. **Cache Miss → Forward to Authority:**
   $$\text{send}(q, \text{authorityNodeId})$$

**Authority processing:**
$$\text{if } e \in \text{dnsAuthorityDb}:$$
$$\quad r \leftarrow \text{DnsResponse}(e, q.\text{queryId}, \text{true}, \text{record}.\epsilon, \text{record}.\tau, \ldots)$$
$$\text{else}:$$
$$\quad r \leftarrow \text{DnsResponse}(e, q.\text{queryId}, \text{false}, \emptyset, \ldots)$$

### 4.5 Caching Mechanism

**Cache Insertion:**
$$\text{dnsCache}[e] \leftarrow \langle e, \epsilon, \tau, t_{\text{now}} + \tau, t_{\text{record}}, \text{auth} \rangle$$

**Cache Eviction (when $|\text{dnsCache}| \geq \text{maxSize}$):**

1. Remove all expired entries
2. If still over capacity, remove entry with earliest expiry:
   $$e_{\text{victim}} = \arg\min_{e \in \text{dnsCache}} \text{dnsCache}[e].\text{expiryTime}$$

**Cache Hit Rate:**
$$\text{hitRate} = \frac{\sum \text{cacheHits}}{\sum \text{cacheHits} + \sum \text{cacheMisses}}$$

### 4.6 Direct Mode (Fair Comparison)

For fair comparison on identical physical topology, DNS operates in "direct mode" where queries bypass physical routing:

1. Query logically traverses: Client → Resolver → Authority → Resolver → Client
2. Latency modeled as configurable RTT based on network diameter:

   $$\text{RTT}_{\text{DNS}} = 2 \cdot D \cdot d$$

This models DNS running over an already-routed IP underlay, isolating the protocol comparison from routing convergence.

### 4.7 Latency Analysis

**Query latency (cache miss):**
$$L_{\text{query}} = \text{RTT}_{\text{client} \to \text{resolver}} + \text{RTT}_{\text{resolver} \to \text{authority}}$$

For direct mode with resolver at network center:
$$L_{\text{query}} \approx 2 \cdot D \cdot d$$

**Effective latency with caching:**
$$L_{\text{effective}} = h \cdot 0 + (1-h) \cdot L_{\text{query}}$$

where $h$ = cache hit rate.

### 4.8 State Complexity

**Authority state:** $O(M)$ — one record per EID

**Resolver cache:** $O(\min(M, C))$ where $C$ = cache capacity

**Network-wide state:** $O(M + R \cdot C)$ where $R$ = number of resolvers

Typically $R \ll N$, so **$O(M)$** — centralized state.

---

## 5. Staleness and Accuracy Model

### 5.1 Ground Truth Database

The simulation maintains authoritative ground truth:

```cpp
struct GroundTruthRecord {
    int eid;
    int publisherId;
    EndpointInfo endpoint;
    simtime_t publishTime;
    simtime_t lastChangeTime;
    int version;
    bool isActive;
};
```

### 5.2 BGP Accuracy

A node's BGP entry for EID $e$ is **correct** if:

$$\text{correct}_{\text{BGP}}(n, e) = \begin{cases}
\text{bgpTable}[e].\text{endpoint} = \text{GT}[e].\text{endpoint} & \text{if GT}[e].\text{isActive} \\
e \notin \text{bgpTable} & \text{if } \neg\text{GT}[e].\text{isActive}
\end{cases}$$

**Network-wide BGP accuracy:**
$$\text{Accuracy}_{\text{BGP}}(e) = \frac{|\{n : \text{correct}_{\text{BGP}}(n, e)\}|}{N}$$

### 5.3 DNS Staleness

A DNS response is **stale** if the cached/returned record predates the last authoritative change:

$$\text{stale}(r) = r.\text{recordTime} < \text{GT}[r.\text{eid}].\text{lastChangeTime}$$

**DNS accuracy per query:**
$$\text{correct}_{\text{DNS}}(r) = r.\text{found} \land \neg\text{stale}(r) \land r.\text{endpoint} = \text{GT}[r.\text{eid}].\text{endpoint}$$

### 5.4 Churn Impact Analysis

Under churn with interval $\Delta_{\text{churn}}$:

**BGP:** Each change triggers network-wide flood
$$\text{Messages}_{\text{BGP}} = O\left(\frac{T}{\Delta_{\text{churn}}} \cdot N\right)$$

**DNS:** Changes are local to authority; staleness depends on TTL
$$P(\text{stale}) \approx \frac{\Delta_{\text{churn}}}{\tau} \text{ for } \tau > \Delta_{\text{churn}}$$

where $\tau$ = TTL.

---

## 6. Convergence Detection

### 6.1 Definition

**Convergence** for EID $e$ occurs when ≥99% of nodes have correct information:

$$\text{converged}(e, t) = \frac{|\{n : \text{correct}(n, e, t)\}|}{N} \geq 0.99$$

### 6.2 Convergence Time

$$T_{\text{conv}}(e) = \min\{t : \text{converged}(e, t)\} - T_{\text{publish}}(e)$$

### 6.3 Initial vs Churn Convergence

We distinguish:

- **Initial convergence:** First publication of an EID
- **Churn convergence:** Subsequent updates/withdrawals

$$T_{\text{conv}}^{\text{initial}}(e) = T_{\text{conv}}(e) \text{ for first publish}$$
$$T_{\text{conv}}^{\text{churn}}(e) = T_{\text{conv}}(e) \text{ for updates after initial}$$

This separation is critical for deep-space analysis where:
$$\frac{T_{\text{conv}}}{\Delta_{\text{churn}}} > 1 \Rightarrow \text{perpetual inconsistency}$$

---

## 7. Query Distribution Model

### 7.1 Zipf Distribution

Query patterns follow Zipf's law:

$$P(\text{query for EID } e_k) \propto \frac{1}{k^\alpha}$$

where $k$ is the rank (1 = most popular) and $\alpha$ is the skewness parameter.

| $\alpha$ | Distribution | Typical Use Case |
|----------|--------------|------------------|
| 0.0 | Uniform | Random/uniform access |
| 0.5 | Slightly skewed | Light locality |
| 1.0 | Moderately skewed | Web traffic (Zipf's law) |
| 1.5 | Highly skewed | Strong locality |
| 2.0 | Very highly skewed | Extreme hot-spot |

### 7.2 Cache Effectiveness

For Zipf-distributed queries, cache hit rate increases with $\alpha$:

$$h(\alpha) \approx 1 - \frac{M^{1-\alpha}}{C^{1-\alpha}} \text{ for } \alpha \neq 1$$

where $M$ = EID count, $C$ = cache size.

---

## 8. Metrics Summary

### 8.1 Overhead Metrics

| Metric | Formula | Unit |
|--------|---------|------|
| Total bytes sent | $\sum_{n} \sum_{m} |m|$ | bytes |
| Total messages | $\sum_{n} \text{msgCount}(n)$ | count |
| Per-EID overhead | $\frac{\text{totalBytes}}{M}$ | bytes/EID |

### 8.2 Latency Metrics

| Metric | Definition | Unit |
|--------|------------|------|
| Discovery latency | Time from publish to first correct resolution | seconds |
| Convergence time | Time until 99% nodes correct | seconds |
| Query latency | Round-trip time for DNS query | seconds |
| Resolution latency | Time to resolve once discoverable | seconds |

### 8.3 Accuracy Metrics

| Metric | Formula | Range |
|--------|---------|-------|
| BGP accuracy | $\frac{\text{correct nodes}}{N}$ | [0, 1] |
| DNS accuracy | $\frac{\text{correct responses}}{\text{total responses}}$ | [0, 1] |
| Stale rate | $\frac{\text{stale responses}}{\text{total responses}}$ | [0, 1] |
| Cache hit rate | $\frac{\text{hits}}{\text{hits} + \text{misses}}$ | [0, 1] |

### 8.4 State Metrics

| Metric | BGP | DNS |
|--------|-----|-----|
| Per-node state | $|\text{bgpTable}|$ | $|\text{dnsCache}|$ |
| Network state | $N \cdot |\text{bgpTable}|$ | $|\text{authorityDb}| + \sum_r |\text{cache}_r|$ |

---

## 9. Experimental Parameters

### 9.1 Network Configuration

| Parameter | Symbol | Values |
|-----------|--------|--------|
| Grid dimensions | $w \times h$ | 5×5, 10×10, 15×15, 20×20 |
| Node count | $N$ | 25, 100, 225, 400 |
| Link delay | $d$ | 10 ms (terrestrial), 1-20 s (deep-space) |
| Network diameter | $D$ | $w + h - 2$ |

### 9.2 Protocol Parameters

| Parameter | BGP | DNS |
|-----------|-----|-----|
| Max path length | 100 | — |
| Path vector | enabled | — |
| TTL | — | 15-120 s |
| Cache size | — | 10,000 entries |
| Query timeout | — | 5 s |
| Max hierarchy depth | — | 5 |

### 9.3 Workload Parameters

| Parameter | Values | Description |
|-----------|--------|-------------|
| EID count ($M$) | 10-500 | Number of published EIDs |
| Query count ($Q$) | 100-1000 | Queries per client |
| Query interval | 0.3-0.5 s | Time between queries |
| Churn interval ($\Delta$) | 5-120 s | Time between EID changes |
| Churn probability | 0.1-0.5 | Probability of change per interval |
| Zipf alpha ($\alpha$) | 0.0-2.0 | Query distribution skewness |

### 9.4 Simulation Parameters

| Parameter | Value |
|-----------|-------|
| Warmup period | 2-5 s |
| Simulation time | 60-2400 s |
| Repetitions | 2-10 |
| Convergence threshold | 99% |
| Snapshot interval | 0.1-10 s |

---

## 10. Implementation Notes

### 10.1 Simulation Framework

The models are implemented in OMNeT++ 6.x using:
- NED language for network topology definition
- C++ for protocol logic (EidNode module)
- MSG files for message definitions

### 10.2 Random Number Generation

Each repetition uses independent seed:
```ini
seed-set = ${repetition}
```

Zipf distribution sampling uses inverse transform method.

### 10.3 Statistics Collection

Metrics collected via OMNeT++ signals:
- Scalar statistics: sum, mean, min, max, stddev
- Vector statistics: time-series recording
- Histogram statistics: distribution analysis

### 10.4 Limitations and Assumptions

1. **No packet loss:** All messages are delivered (DTN assumption: store-and-forward)
2. **No transmission delay:** Only propagation delay modeled (small control messages)
3. **Single authority per EID:** No authority replication
4. **Synchronous clocks:** No clock drift between nodes
5. **Static topology:** No link failures during experiments (except churn experiments)
6. **Instantaneous processing:** Negligible computational delay

---

## 11. Complexity Summary

| Aspect | BGP-like (Push) | DNS-like (Pull) |
|--------|-----------------|-----------------|
| **State per node** | $O(M)$ | $O(1)$ client, $O(C)$ resolver |
| **Network state** | $O(N \cdot M)$ | $O(M)$ |
| **Publication cost** | $O(N)$ messages | $O(1)$ messages |
| **Query cost** | $O(1)$ (local) | $O(D)$ hops |
| **Churn cost** | $O(N)$ per change | $O(1)$ per change |
| **Convergence time** | $O(D \cdot d)$ | N/A (on-demand) |
| **Discovery latency** | $D \cdot d$ | $2 \cdot D \cdot d$ |
| **Resolution latency** | ~0 (local lookup) | $2 \cdot D \cdot d$ |

---

## References

1. Rekhter, Y., Li, T., & Hares, S. (2006). A Border Gateway Protocol 4 (BGP-4). RFC 4271.
2. Mockapetris, P. (1987). Domain Names - Implementation and Specification. RFC 1035.
3. Fall, K. (2003). A Delay-Tolerant Network Architecture for Challenged Internets. SIGCOMM.
4. Breslau, L., et al. (1999). Web Caching and Zipf-like Distributions. INFOCOM.
