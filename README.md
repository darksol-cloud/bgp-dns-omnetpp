# BGP-DNS EID Distribution Simulation

An OMNeT++ simulation model (with no INET dependency) that quantitatively compares two control-plane strategies for distributing DTN EID reachability information:

1. **BGP-like approach (push)**: Continuously disseminates EID reachability state through neighbor-to-neighbor updates
2. **DNS-like approach (pull)**: Resolves EID → endpoint mapping on demand via hierarchical/cached queries

## Purpose

This simulation evaluates the trade-off between push and pull approaches for DTN control-plane information distribution, focusing on:

- **Overhead**: Message count, data bytes, processing operations, state storage
- **Performance**: Discovery latency, convergence time, staleness/accuracy
- **Scalability**: Behavior with increasing network size and EID count
- **Churn Resilience**: Protocol behavior under frequent updates/withdrawals

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
│   ├── omnetpp.ini           # Basic simulation configurations
│   ├── experiments.ini       # Experiment configurations (Exp 1-5)
│   ├── run_experiments.sh    # Experiment execution script
│   ├── experiment_plots.py   # Python analysis and plotting script
│   ├── experiment_plan.md               # Detailed experiment plan
│   ├── experiment_explanation.md  # Results explanation
│   └── results/              # Output files (scalar, vector, CSV)
├── Makefile                  # Build configuration
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

## Protocol Models

### BGP-like Push Model

- Publisher announces EIDs to all neighbors
- Announcements flood through the network (path-vector style)
- Every node maintains a local FIB (Forwarding Information Base)
- Updates/withdrawals propagate network-wide on any change
- **Complexity**: O(N × E) state, O(N × E) messages per change

### DNS-like Pull Model

- Publisher registers EIDs with a central authority
- Clients query resolver/authority on demand
- Resolver caches responses with TTL-based expiration
- Only queried EIDs incur network traffic
- **Complexity**: O(E) state (authority only), O(Q) messages for Q queries

### Fair Comparison Design

Both protocols operate over the same physical grid topology. DNS uses `dnsDirectMode=true` which simulates DNS running over a pre-routed IP network (using `sendDirect()` with RTT-based delays), avoiding the need to implement IP routing within the simulation.

## Experiments

Five experiments compare the protocols across different dimensions:

| Experiment | Goal | Key Parameter |
|------------|------|---------------|
| Exp 1: Baseline | Steady-state overhead | 100 nodes, 50 EIDs, 200 queries |
| Exp 2: Network Scale | Overhead vs network size | 25 → 400 nodes |
| Exp 3: EID Scale | Overhead vs EID count | 10 → 500 EIDs |
| Exp 4: Latency | Discovery time comparison | Time-to-first-answer |
| Exp 5: Churn | Behavior under updates | 5s → 60s churn interval |

### Running Experiments

```bash
cd simulations
source ../../setenv

# Run all experiments (1-5)
./run_experiments.sh

# Run a specific experiment (e.g., experiment 1)
./run_experiments.sh 1

# Export results to CSV only
./run_experiments.sh export
```

### Analyzing Results

```bash
# Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install pandas matplotlib numpy

# Generate plots and tables
python3 experiment_plots.py

# Plots saved to plots/ directory
```

## Key Results Summary

| Dimension | BGP | DNS | Winner |
|-----------|-----|-----|--------|
| Baseline overhead | 27 KB | 9.6 KB | DNS |
| Network scalability | O(N²) | O(1) | DNS |
| EID scalability | O(N×E) | O(E) | DNS |
| Discovery latency | 0.18s (once) | 0.20s (per query) | Tie |
| Churn overhead (5s) | 5 MB | 24 KB | DNS |
| Freshness under churn | 100% | TTL-dependent | BGP |

### Key Findings

1. **Baseline (Exp 1)**: DNS achieves same functionality with ~65% less network overhead
2. **Network Scale (Exp 2)**: BGP grows O(N²), DNS stays constant regardless of network size
3. **EID Scale (Exp 3)**: BGP state explodes as N×E; DNS keeps state centralized at O(E)
4. **Latency (Exp 4)**: Similar discovery times, but different timing models (upfront vs per-query)
5. **Churn (Exp 5)**: BGP pays 20-200× more overhead to maintain consistency under churn

**Conclusion**: DNS-style pull model is more efficient for overhead and scalability, while BGP-style push model provides better consistency guarantees at higher network cost.

## Running Individual Configurations

```bash
cd simulations

# Run a specific experiment configuration
../out/clang-release/bgp-dns -u Cmdenv -c Exp1_Baseline_Bgp -n ../src -f experiments.ini

# Run with GUI
../out/clang-release/bgp-dns -u Qtenv -c Exp1_Baseline_Dns -n ../src -f experiments.ini

# Quick comparison on small network
../out/clang-release/bgp-dns -u Cmdenv -c Exp_QuickCompare -n ../src -f experiments.ini
```

## Metrics Collected

| Metric | Signal | Description |
|--------|--------|-------------|
| Messages sent | `bgpAnnouncesSent`, `dnsQueriesSent` | Protocol message counts |
| Bytes transferred | `messageBytesReceived` | Network overhead |
| State size | `bgpTableSize`, `dnsCacheSize` | Memory/storage overhead |
| Discovery latency | `discoveryLatency` | Time to resolve EID |
| Convergence time | `avgConvergenceTime` | BGP network-wide convergence |
| Answer accuracy | `correctAnswers`, `staleAnswers` | Freshness under churn |

## References

- [BGP Extension for DTN EIDs](https://ieeexplore.ieee.org/document/11229835) - Feldmann et al., WiSEE 2025
- [ipn.arpa DNS Draft](https://datatracker.ietf.org/doc/html/draft-ek-dtn-ipn-arpa-00) - Erik Kline

## License

This simulation model is provided for research and educational purposes.
