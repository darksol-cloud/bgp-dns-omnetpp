# BGP-DNS EID Distribution Simulation

A pure OMNeT++ simulation (no INET dependency) that quantitatively compares two control-plane strategies for distributing DTN EID reachability information:

1. **BGP-like approach (push)**: Continuously disseminates EID reachability state through neighbor-to-neighbor updates
2. **DNS-like approach (pull)**: Resolves EID → endpoint mapping on demand via hierarchical/cached queries

## Purpose

This simulation evaluates the trade-off between push and pull approaches for DTN control-plane information distribution, focusing on:

- **Overhead**: Message count, data bytes, processing operations, state storage
- **Performance**: Discovery latency, convergence time, staleness/accuracy
- **Scalability**: Behavior with increasing network size and EID count

## Project Structure

```
bgp-dns/
├── src/
│   ├── package.ned           # Package definition
│   ├── EidNode.ned           # Main node module definition
│   ├── GroundTruth.ned       # Metrics collection module
│   ├── EidChannel.ned        # Channel definitions
│   ├── Networks.ned          # Network topology definitions
│   ├── EidMessages.msg       # Message type definitions
│   ├── EidNode.h/cc          # Node implementation
│   └── GroundTruth.h/cc      # Ground truth and metrics
├── simulations/
│   ├── omnetpp.ini           # Simulation configurations
│   └── results/              # Output files (scalar, vector)
├── Makefile                  # Build configuration (auto-generated)
└── README.md                 # This file
```

## Building

### Using OMNeT++ IDE

1. Import the project into the OMNeT++ IDE
2. Build using Project > Build All (or Ctrl+B)

### Using Command Line

```bash
cd bgp-dns
source ../../setenv  # Source OMNeT++ environment

# Generate Makefile using opp_makemake (if needed)
opp_makemake -f --deep -O out -I.

# Build
make
```

## Running Simulations

### Quick Start - Toy Examples

```bash
cd simulations

# Run a simple 5-node line network with BGP (command line)
../out/clang-release/bgp-dns -u Cmdenv -c ToyLine_BgpOnly -n ../src

# Run with Qt GUI
../out/clang-release/bgp-dns -u Qtenv -c ToyLine_BgpOnly -n ../src

# Run DNS-only variant
../out/clang-release/bgp-dns -u Cmdenv -c ToyLine_DnsOnly -n ../src

# Run a single repetition
../out/clang-release/bgp-dns -u Cmdenv -c ToyLine_BgpOnly -r 0 -n ../src
```

### Available Configurations

#### Toy Examples (debugging/demonstration)
- `ToyLine_BgpOnly` - 5-node chain, BGP propagation
- `ToyLine_DnsOnly` - 5-node chain, DNS resolution
- `ToyLine_Both` - Both approaches simultaneously
- `ToyLine_MultipleEids` - Multiple EIDs in chain
- `ToyRing_Bgp` - 6-node ring topology
- `ToyStar_Bgp` - Hub-and-spoke topology
- `ToyChurn` - Churn events demonstration

#### Medium-Scale (sanity checks)
- `Medium_Grid_Bgp` - 10x10 grid with BGP
- `Medium_Grid_Dns` - 10x10 grid with DNS
- `Medium_Leo` - LEO gateway scenario (2 clusters)
- `Medium_Hierarchical_Dns` - Hierarchical DNS structure

#### Large-Scale (scalability analysis)
- `Large_Grid_Bgp_10x10` through `Large_Grid_Bgp_50x50` - BGP at various scales
- `Large_Grid_Dns_10x10` through `Large_Grid_Dns_30x30` - DNS at various scales

#### Parameter Sweeps
- `Sweep_ChurnRate_Bgp` / `Sweep_ChurnRate_Dns` - Impact of churn
- `Sweep_DnsTtl` - Impact of DNS TTL on staleness
- `Sweep_EidCount_Bgp` / `Sweep_EidCount_Dns` - Scaling with EID count
- `Sweep_QueryDistribution` - Uniform vs Zipf query patterns

#### Comparative
- `Compare_BgpVsDns_Latency_Bgp` / `Compare_BgpVsDns_Latency_Dns` - Discovery latency
- `Compare_Overhead_Bgp` / `Compare_Overhead_Dns` - Message/byte overhead
- `Compare_Staleness_Bgp` / `Compare_Staleness_Dns` - Staleness under churn

#### Disruption
- `Disruption_LinkFailure_Bgp` / `Disruption_LinkFailure_Dns` - Link failure behavior

## Key Parameters

### Node Role Parameters
- `isPublisher` - Node can originate/register EIDs
- `isClient` - Node can query/resolve EIDs
- `bgpEnabled` - Participates in BGP-like distribution
- `dnsEnabled` - Participates in DNS-like resolution
- `isResolver` - Acts as DNS resolver (caches responses)
- `isAuthority` - Acts as authoritative DNS server

### BGP Parameters
- `bgpKeepaliveInterval` - Keepalive message interval
- `bgpPathVector` - Use path vector (vs distance vector)
- `bgpMaxPathLength` - Maximum acceptable path length

### DNS Parameters
- `dnsTtl` - Default TTL for DNS records (seconds)
- `dnsCacheSize` - Maximum cache entries per resolver
- `dnsQueryTimeout` - Query timeout
- `dnsMaxHierarchyDepth` - Maximum referral chain depth

### Publisher Parameters
- `publishEids` - Comma-separated list (supports ranges: "1-10,20,30")
- `publishStartTime` - When to start publishing
- `publishInterval` - Interval between publishing EIDs

### Client Parameters
- `queryEids` - EIDs to query (empty = random from ground truth)
- `queryStartTime` - When to start querying
- `queryInterval` - Interval between queries
- `queryCount` - Number of queries to generate
- `queryZipfAlpha` - Query distribution (0=uniform, >0=Zipf)

### Churn Parameters
- `churnInterval` - Interval between churn events
- `churnProbability` - Probability of churn per interval
- `withdrawProbability` - Fraction of churns that are withdrawals

### Message Sizes (bytes)
| Message Type | Default Size |
|-------------|--------------|
| BgpAnnounce | 64 |
| BgpWithdraw | 32 |
| DnsQuery | 48 |
| DnsResponse | 80 |
| DnsRegister | 72 |
| DnsDeregister | 24 |

## Metrics Collected

### Performance Metrics
- `discoveryLatency` - Time from publish/query to discovery
- `bgpConvergenceTime` - Time for BGP tables to converge
- `dnsQueryLatency` - DNS query response time

### Accuracy Metrics
- `correctAnswers` - Number of correct query responses
- `staleAnswers` - Number of stale (outdated) responses
- `globalAccuracy` - Fraction of nodes with correct state
- `globalCoverage` - Fraction of nodes knowing each EID

### Overhead Metrics
- `bgpAnnouncesSent/Received` - BGP announcement counts
- `bgpWithdrawsSent/Received` - BGP withdrawal counts
- `dnsQueriesSent/Received` - DNS query counts
- `dnsResponsesSent/Received` - DNS response counts
- `messageBytesSent/Received` - Total bytes transferred
- `bgpTableSize` - Entries in BGP routing table
- `dnsCacheSize` - Entries in DNS cache
- `tableOperations` - Total table operations (proxy for CPU)

### Global Metrics (from GroundTruth module)
- `globalConvergenceTime` - Network-wide convergence time
- `globalStaleRate` - Fraction of stale cache entries
- `avgBgpTableSize` - Average BGP table size across nodes
- `avgDnsCacheSize` - Average DNS cache size
- `totalTableOperations` - Sum of all table operations

## Results Analysis

Results are stored in `simulations/results/` as OMNeT++ result files.

### Using opp_scavetool (Command Line)

```bash
cd simulations

# List available result files
ls results/

# Query all scalars from a result file
opp_scavetool query results/ToyLine_BgpOnly-#0.sca

# Query specific metrics (ground truth module)
opp_scavetool query -f "module=~*groundTruth*" results/*.sca

# Query with pattern matching
opp_scavetool query -f "name=~*Latency*" results/*.sca

# Export scalars to CSV
opp_scavetool export -F CSV-S -x allowMixed=true results/*.sca -o scalars.csv

# Export specific metrics
opp_scavetool export -F CSV-S -f "module=~*groundTruth*" results/*.sca -o groundtruth.csv
```

### Key Metrics to Compare

**For BGP vs DNS overhead:**
```bash
# BGP message counts
opp_scavetool query -f "name=~bgpAnnounces*" results/*.sca

# DNS message counts
opp_scavetool query -f "name=~dnsQueries*" results/*.sca

# Bytes transferred
opp_scavetool query -f "name=~messageBytes*" results/*.sca
```

**For convergence/latency:**
```bash
# Discovery latency
opp_scavetool query -f "name=~discoveryLatency*" results/*.sca

# Convergence time
opp_scavetool query -f "name=~*Convergence*" results/*.sca
```

**For accuracy:**
```bash
# Correct vs stale answers
opp_scavetool query -f "name=~*Answers*" results/*.sca

# Global accuracy
opp_scavetool query -f "name=~globalAccuracy*" results/*.sca
```

### Using OMNeT++ IDE Analysis Tool

1. Open the OMNeT++ IDE
2. Go to File > Open File and select a `.sca` or `.vec` file
3. Use the Analysis Tool to create charts and browse results interactively

## Network Topologies

### Built-in Topologies
1. **ToyLineNetwork** - Linear chain (configurable length)
2. **ToyRingNetwork** - Ring topology
3. **ToyStarNetwork** - Hub and spoke
4. **LeoGatewayNetwork** - Two clusters connected by gateways
5. **HierarchicalNetwork** - DNS-style hierarchy (root, resolvers, authorities)
6. **GridNetwork** - 2D grid (configurable width/height)
7. **ConfigurableNetwork** - Programmatic topology generation

### Channel Types
- **EidChannel** - Standard delay channel (10ms delay)
- **HighLatencyChannel** - Satellite-like (250ms delay)
- **LossyChannel** - For disruption scenarios (50ms delay)
- **DisruptionChannel** - For DTN scenarios (100ms delay)

## Conceptual Comparison

| Aspect | BGP-like (Push) | DNS-like (Pull) |
|--------|-----------------|-----------------|
| Mechanism | Proactive dissemination | On-demand resolution |
| State | Distributed FIB | Centralized + cached |
| Updates | Immediate propagation | TTL-based invalidation |
| Overhead | Continuous | On-demand |
| Convergence | Network-wide | Per-query |
| Staleness | Low (fast updates) | TTL-dependent |
| Disruption | Medium (depends on connectivity) | High (stateless queries) |

## Extending the Simulation

### Adding New Topologies
1. Define network in `Networks.ned`
2. Specify node roles and connections
3. Add configuration in `omnetpp.ini`

### Adding New Metrics
1. Add signal in `EidNode.ned` or `GroundTruth.ned`
2. Register signal in `initialize()`
3. Emit signal at appropriate points
4. Add `@statistic` declaration

### Modifying Message Sizes
Adjust `byteSize` in `EidMessages.msg` or override in `omnetpp.ini`:
```ini
**.BgpAnnounce.byteSize = 128
```

## License

LGPL - See LICENSE file for details.
