# BGP-DNS EID Distribution Simulation

An OMNeT++ simulation model (with no INET dependency) that quantitatively compares two control-plane strategies for distributing DTN EID reachability information:

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
