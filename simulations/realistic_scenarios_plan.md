# Realistic Use Case Scenarios: Terrestrial, Lunar, and Mars DTN

## Objective

Design three realistic DTN deployment scenarios to evaluate BGP vs DNS protocol performance across the latency spectrum. The goal is to determine:

1. **Terrestrial**: Confirm DNS advantage in low-latency environments
2. **Lunar**: Determine which protocol is preferable (contested territory)
3. **Mars**: Confirm BGP advantage in high-latency environments

---

## Scenario 1: Terrestrial Disaster Response Network

### Use Case Description

A disaster response network deployed after a natural disaster (earthquake, hurricane). First responders, mobile command centers, drone relays, and field hospitals need to discover and communicate with each other. Nodes are mobile, joining and leaving the network as teams move through the affected area.

### Network Topology

```
                    [Command Center]
                         |
            +------------+------------+
            |            |            |
       [Relay-1]    [Relay-2]    [Relay-3]
          /\           /\           /\
         /  \         /  \         /  \
     [Team] [Team] [Team] [Team] [Team] [Team]
        |      |      |      |      |      |
      [Drone][Drone][Drone][Drone][Drone][Drone]
```

**Topology Type**: Hierarchical mesh (3-tier)
- **Tier 1**: 1 Command Center (central authority/resolver)
- **Tier 2**: 3 Mobile Relay Vehicles (intermediate routers)
- **Tier 3**: 6 Field Teams (publishers + clients)
- **Tier 4**: 12 Drones/Sensors (publishers only)

**Total Nodes**: 22

### Link Characteristics

| Link Type | Delay | Notes |
|-----------|-------|-------|
| Command ↔ Relay | 10ms | Stable backhaul |
| Relay ↔ Team | 20ms | Wireless mesh |
| Team ↔ Drone | 5ms | Short-range radio |
| Relay ↔ Relay | 30ms | Cross-links for redundancy |

**Network Diameter**: ~4 hops, ~65ms worst-case one-way

### Churn Model

- **Join/Leave**: Teams and drones move in/out of coverage
- **Churn Interval**: 30-60s (moderate mobility)
- **Churn Probability**: 0.2 (20% of publishers change per interval)
- **Service Discovery**: Teams need to find medical units, supply caches, other teams

### EID Model

- **EIDs**: 20 services (medical, logistics, communications, reconnaissance)
- **Publishers**: Each team/drone publishes 1-3 services
- **Clients**: Teams query for services they need
- **Query Pattern**: Zipf α=1.2 (some services more popular than others)

### Expected Outcome

**DNS should win** because:
- Low latency means DNS query RTT is acceptable (~130ms)
- Churn causes BGP to flood updates frequently
- Mobile nodes benefit from DNS's centralized state

### Metrics Focus

- Overhead under churn (bytes/messages)
- Discovery latency for new services
- Accuracy of service location under mobility

---

## Scenario 2: Lunar Surface Network (Artemis-era)

### Use Case Description

A lunar exploration network supporting the Artemis program. The network connects:
- Earth ground stations (DSN)
- Lunar Gateway (orbital relay)
- Lunar surface assets (habitats, rovers, astronauts)

The key challenge: Earth-Moon delay is ~1.3s one-way, but surface-to-surface is near-instantaneous.

### Network Topology

```
        [Earth DSN]
             |
         1.3s delay
             |
      [Lunar Gateway]
           / \
    250ms /   \ 250ms
         /     \
   [South Pole    [Equatorial
    Habitat]       Relay]
      /|\           /\
     / | \         /  \
[Rover1][Rover2] [Rover3][Lander]
    |      |        |       |
 [EVA-1][EVA-2]  [EVA-3] [Drone]
```

**Topology Type**: Hierarchical with Earth gateway
- **Tier 0**: 1 Earth DSN node (root authority for Earth-based services)
- **Tier 1**: 1 Lunar Gateway (orbital relay, local authority for lunar services)
- **Tier 2**: 2 Surface bases (South Pole habitat, Equatorial relay)
- **Tier 3**: 4 Mobile assets (rovers, landers)
- **Tier 4**: 4 Field assets (EVA suits, drones)

**Total Nodes**: 12

### Link Characteristics

| Link Type | Delay | Notes |
|-----------|-------|-------|
| Earth ↔ Gateway | 1.3s | Earth-Moon light delay |
| Gateway ↔ Surface Base | 250ms | Orbital relay (including processing) |
| Surface Base ↔ Rover | 10ms | Direct line-of-sight |
| Rover ↔ EVA | 5ms | Short-range suit radio |
| Surface Base ↔ Surface Base | 50ms | Cross-link (when visible) |

**Network Diameter**:
- Lunar-only: ~3 hops, ~315ms worst-case
- Earth-involved: ~5 hops, ~1.8s worst-case

### Churn Model

- **Orbital occlusion**: Gateway loses Earth contact periodically
- **Surface mobility**: Rovers move, EVAs have limited duration
- **Churn Interval**: 120s (slower than terrestrial)
- **Churn Probability**: 0.15
- **Scheduled contacts**: Some links have predictable up/down times

### EID Model

- **EIDs**: 15 services split between Earth and Moon
  - Earth-based: 5 (mission control, science support, communications relay)
  - Lunar-based: 10 (life support status, rover telemetry, EVA tracking, science instruments)
- **Publishers**: Surface assets publish local services; Earth publishes support services
- **Clients**: All nodes query for services
- **Query Pattern**: Zipf α=1.0 (moderate skew toward critical services)

### Key Research Questions

1. Should lunar services use DNS (lower overhead) or BGP (faster local lookup)?
2. Should Earth services use BGP (pre-propagate to Moon) or DNS (query on demand)?
3. Is a **hybrid approach** optimal? (DNS for lunar-local, BGP for Earth-Moon)

### Expected Outcome

**Contested** - This is the interesting case:
- For **lunar-local queries**: DNS might win (low local latency, ~315ms RTT acceptable)
- For **Earth-involved queries**: BGP likely wins (1.8s RTT per DNS query is painful)
- **Hybrid hypothesis**: Use DNS within lunar network, BGP for Earth-Moon synchronization

### Metrics Focus

- Separate metrics for lunar-local vs Earth-involved queries
- Overhead during orbital occlusion events
- Service discovery latency by query destination

---

## Scenario 3: Mars Exploration Network (2030s)

### Use Case Description

A Mars exploration network supporting a crewed mission. The network connects:
- Earth ground stations
- Mars Relay Orbiters (MRO, future relays)
- Mars surface assets (habitats, rovers, drones)

The key challenge: Earth-Mars delay ranges from 3 to 22 minutes depending on orbital positions. We'll model the average case (~12 minutes one-way).

### Network Topology

```
        [Earth DSN]
             |
        12min delay
             |
      [Mars Relay Orbiter]
           / \
     1min /   \ 1min
         /     \
   [Jezero        [Olympus
    Habitat]       Outpost]
      /|\           /\
     / | \         /  \
[Rover1][Rover2] [Rover3][Drone-Swarm]
    |               |
 [Science      [Resource
  Package]      Scanner]
```

**Topology Type**: Deep hierarchical with extreme Earth delay
- **Tier 0**: 1 Earth DSN node (mission control, but very far)
- **Tier 1**: 1 Mars Relay Orbiter (local authority, orbital relay)
- **Tier 2**: 2 Surface habitats (regional hubs)
- **Tier 3**: 4 Mobile assets (rovers, drone swarms)
- **Tier 4**: 2 Deployed instruments (science packages)

**Total Nodes**: 10

### Link Characteristics

| Link Type | Delay | Notes |
|-----------|-------|-------|
| Earth ↔ MRO | 720s (12 min) | Average Earth-Mars delay |
| MRO ↔ Surface Habitat | 60s | Orbital pass + processing |
| Habitat ↔ Rover | 5s | Surface relay (terrain, distance) |
| Rover ↔ Instrument | 1s | Local deployment |
| Habitat ↔ Habitat | 30s | Long-distance surface link |

**Network Diameter**:
- Mars-only: ~4 hops, ~96s worst-case
- Earth-involved: ~6 hops, ~14+ minutes worst-case

### Churn Model

- **Orbital windows**: MRO has limited contact windows with each surface site
- **Dust storms**: Can disrupt surface links for extended periods
- **Rover mobility**: Slow but continuous movement
- **Churn Interval**: 300s (very slow, deliberate operations)
- **Churn Probability**: 0.1 (low churn, high reliability needed)

### EID Model

- **EIDs**: 12 critical services
  - Earth-based: 3 (mission control, navigation updates, emergency support)
  - Mars-based: 9 (life support, rover control, science data, resource maps)
- **Publishers**: Each major asset publishes its capabilities
- **Clients**: All nodes need to discover services
- **Query Pattern**: Zipf α=0.8 (flatter distribution - all services are important)

### Expected Outcome

**BGP should win decisively** because:
- DNS query RTT for Mars-only: ~3 minutes (unacceptable for interactive use)
- DNS query RTT for Earth-involved: ~28 minutes (completely impractical)
- BGP convergence pays once, then all lookups are instant
- Even with 300s churn, BGP overhead is acceptable for the consistency benefit

### Metrics Focus

- Absolute query latency (is DNS usable at all?)
- Overhead per lookup (amortized over mission duration)
- Accuracy during orbital blackouts

---

## Experiment Design Summary

### Experiment 11: Terrestrial Disaster Response

| Parameter | Value |
|-----------|-------|
| Network | Custom hierarchical (22 nodes) |
| Link delays | 5-30ms (see topology) |
| EIDs | 20 |
| Churn interval | 30s, 60s |
| Simulation time | 600s |
| DNS TTL | 30s |
| Repetitions | 5 |

**Configurations**: `Exp11_Terrestrial_Bgp`, `Exp11_Terrestrial_Dns`

### Experiment 12: Lunar Artemis Network

| Parameter | Value |
|-----------|-------|
| Network | Custom hierarchical (12 nodes) |
| Link delays | 5ms-1.3s (see topology) |
| EIDs | 15 (5 Earth, 10 lunar) |
| Churn interval | 120s |
| Simulation time | 1200s |
| DNS TTL | 60s |
| Repetitions | 5 |

**Configurations**: `Exp12_Lunar_Bgp`, `Exp12_Lunar_Dns`

**Sub-experiments**:
- 12a: Lunar-local queries only (client and service both on Moon)
- 12b: Earth-involved queries (client on Moon, service on Earth or vice versa)
- 12c: Mixed workload (realistic distribution)

### Experiment 13: Mars Exploration Network

| Parameter | Value |
|-----------|-------|
| Network | Custom hierarchical (10 nodes) |
| Link delays | 1s-720s (see topology) |
| EIDs | 12 (3 Earth, 9 Mars) |
| Churn interval | 300s |
| Simulation time | 3600s (1 hour mission segment) |
| DNS TTL | 120s |
| Repetitions | 5 |

**Configurations**: `Exp13_Mars_Bgp`, `Exp13_Mars_Dns`

**Sub-experiments**:
- 13a: Mars-local queries only
- 13b: Earth-involved queries
- 13c: Orbital blackout resilience (MRO contact loss simulation)

---

## Implementation Requirements

### New Network Topologies Needed

1. **TerrestrialDisasterNetwork** - 22-node hierarchical mesh
2. **LunarArtemisNetwork** - 12-node Earth-Moon hierarchical
3. **MarsExplorationNetwork** - 10-node deep-space hierarchical

### New Channel Types Needed

- **LunarChannel**: 1.3s delay (Earth-Moon)
- **MarsOrbitalChannel**: 60s delay (MRO to surface)
- **MarsInterplanetaryChannel**: 720s delay (Earth-Mars)

### Metrics Extensions

- Track query destination (local vs remote)
- Measure per-hop latency contribution
- Record blackout/occlusion events

---

## Expected Results Matrix

| Scenario | Overhead | Latency | Accuracy | Winner |
|----------|----------|---------|----------|--------|
| Terrestrial (30ms) | DNS ✓ | DNS ✓ | Tie | **DNS** |
| Lunar-local (315ms) | DNS ✓ | DNS ≈ | DNS ≈ | **DNS?** |
| Lunar-Earth (1.8s) | DNS ✓ | BGP ✓ | BGP ✓ | **BGP?** |
| Lunar-mixed | ? | ? | ? | **TBD** |
| Mars-local (96s) | DNS ✓ | BGP ✓ | BGP ✓ | **BGP** |
| Mars-Earth (14min) | DNS ✓ | BGP ✓ | BGP ✓ | **BGP** |

### Key Hypotheses to Test

1. **H1**: DNS wins when `query_RTT < 1s` (terrestrial, lunar-local)
2. **H2**: BGP wins when `query_RTT > convergence_time / num_queries` (Mars)
3. **H3**: Lunar is the crossover point where the protocols are competitive
4. **H4**: A hybrid approach (DNS local, BGP interplanetary) may be optimal for Lunar

---

## Implementation Status

1. [x] Implement the three network topologies in Networks.ned
2. [x] Add new channel types for lunar/Mars delays (EidChannel.ned)
3. [x] Create experiment configurations in experiments.ini
4. [x] Update run_experiments.sh (use `./run_experiments.sh realistic`)
5. [ ] Run experiments and collect results
6. [ ] Analyze crossover point for Lunar scenario

## Running the Experiments

```bash
# Run all realistic scenarios
./run_experiments.sh realistic

# Run individual experiments
./run_experiments.sh 11   # Terrestrial
./run_experiments.sh 12   # Lunar
./run_experiments.sh 13   # Mars
```
