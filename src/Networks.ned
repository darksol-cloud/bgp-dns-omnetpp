// Networks.ned - Network topology definitions

package bgpdns;

import bgpdns.EidNode;
import bgpdns.GroundTruth;
import bgpdns.EidChannel;

// ============================================================================
// Toy Line Network (5-10 nodes in a chain)
// ============================================================================
network ToyLineNetwork
{
    parameters:
        int numNodes = default(5);
        @display("bgb=800,200");

    submodules:
        groundTruth: GroundTruth {
            parameters:
                totalNodes = parent.numNodes;
                @display("p=50,50");
        }

        node[numNodes]: EidNode {
            @display("p=100+100*index,100");
        }

    connections:
        for i=0..numNodes-2 {
            node[i].port++ <--> EidChannel <--> node[i+1].port++;
        }
}

// ============================================================================
// Toy Ring Network
// ============================================================================
network ToyRingNetwork
{
    parameters:
        int numNodes = default(6);
        @display("bgb=500,500");

    submodules:
        groundTruth: GroundTruth {
            parameters:
                totalNodes = parent.numNodes;
                @display("p=250,50");
        }

        node[numNodes]: EidNode {
        }

    connections:
        for i=0..numNodes-1 {
            node[i].port++ <--> EidChannel <--> node[(i+1) % numNodes].port++;
        }
}

// ============================================================================
// Toy Star Network (one central hub)
// ============================================================================
network ToyStarNetwork
{
    parameters:
        int numSpokes = default(5);
        @display("bgb=600,600");

    submodules:
        groundTruth: GroundTruth {
            parameters:
                totalNodes = parent.numSpokes + 1;
                @display("p=50,50");
        }

        hub: EidNode {
            parameters:
                nodeId = 0;
                @display("p=300,300;i=device/router_l");
        }

        spoke[numSpokes]: EidNode {
            // nodeId will be set to index by C++ code, we add 1 via ini file if needed
        }

    connections:
        for i=0..numSpokes-1 {
            hub.port++ <--> EidChannel <--> spoke[i].port++;
        }
}

// ============================================================================
// LEO Gateway Network (two clusters with gateway nodes)
// ============================================================================
network LeoGatewayNetwork
{
    parameters:
        int clusterSize = default(10);      // Nodes per cluster
        int numGateways = default(2);       // Gateway nodes between clusters
        @display("bgb=1000,600");

    submodules:
        groundTruth: GroundTruth {
            parameters:
                totalNodes = 2 * parent.clusterSize + parent.numGateways;
                @display("p=500,50");
        }

        // Cluster A nodes (nodeIds 0 to clusterSize-1)
        clusterA[clusterSize]: EidNode {
            @display("p=100+60*index,200");
        }

        // Cluster B nodes (nodeIds clusterSize to 2*clusterSize-1)
        clusterB[clusterSize]: EidNode {
            @display("p=100+60*index,400");
        }

        // Gateway nodes (nodeIds 2*clusterSize to 2*clusterSize+numGateways-1)
        gateway[numGateways]: EidNode {
            @display("p=300+200*index,300;i=device/router_l");
        }

    connections:
        // Intra-cluster A connections (mesh within cluster)
        for i=0..clusterSize-2 {
            clusterA[i].port++ <--> EidChannel <--> clusterA[i+1].port++;
        }

        // Intra-cluster B connections (mesh within cluster)
        for i=0..clusterSize-2 {
            clusterB[i].port++ <--> EidChannel <--> clusterB[i+1].port++;
        }

        // Gateway connections to clusters (each gateway connects to some nodes in each cluster)
        for g=0..numGateways-1, for i=0..2 {  // Each gateway to 3 nodes per cluster
            gateway[g].port++ <--> HighLatencyChannel <--> clusterA[(g*3+i) % clusterSize].port++
                if (g*3+i) < clusterSize;
            gateway[g].port++ <--> HighLatencyChannel <--> clusterB[(g*3+i) % clusterSize].port++
                if (g*3+i) < clusterSize;
        }

        // Inter-gateway connections
        for i=0..numGateways-2 {
            gateway[i].port++ <--> HighLatencyChannel <--> gateway[i+1].port++;
        }
}

// ============================================================================
// Hierarchical DNS-style Network
// ============================================================================
network HierarchicalNetwork
{
    parameters:
        int numDomains = default(4);        // Number of authority domains
        int nodesPerDomain = default(10);   // Nodes per domain
        int numResolvers = default(2);      // Number of resolvers
        @display("bgb=1200,800");

    submodules:
        groundTruth: GroundTruth {
            parameters:
                totalNodes = 1 + parent.numResolvers + parent.numDomains * (1 + parent.nodesPerDomain);
                @display("p=600,50");
        }

        // Root server
        root: EidNode {
            parameters:
                nodeId = 0;
                isRoot = true;
                isAuthority = true;
                authorityDomain = -1;  // Root knows all domains
                @display("p=600,100;i=device/server_l");
        }

        // Resolvers
        resolver[numResolvers]: EidNode {
            parameters:
                isResolver = true;
                @display("p=400+400*index,200;i=device/server");
        }

        // Authority servers (one per domain)
        authority[numDomains]: EidNode {
            parameters:
                isAuthority = true;
                @display("p=150+300*index,350;i=device/server");
        }

        // Regular nodes (grouped by domain)
        domainNode[numDomains * nodesPerDomain]: EidNode {
            @display("p=100+80*index,500");
        }

    connections:
        // Root to resolvers
        for r=0..numResolvers-1 {
            root.port++ <--> EidChannel <--> resolver[r].port++;
        }

        // Root to authorities
        for a=0..numDomains-1 {
            root.port++ <--> EidChannel <--> authority[a].port++;
        }

        // Resolvers to authorities
        for r=0..numResolvers-1, for a=0..numDomains-1 {
            resolver[r].port++ <--> EidChannel <--> authority[a].port++;
        }

        // Domain nodes to their authority and nearest resolver
        for i=0..numDomains*nodesPerDomain-1 {
            domainNode[i].port++ <--> EidChannel <--> authority[i / nodesPerDomain].port++;
            domainNode[i].port++ <--> EidChannel <--> resolver[i % numResolvers].port++;
        }
}

// ============================================================================
// Grid Network (for scalability testing)
// ============================================================================
network GridNetwork
{
    parameters:
        int gridWidth = default(10);
        int gridHeight = default(10);
        @display("bgb=1200,1200");

    submodules:
        groundTruth: GroundTruth {
            parameters:
                totalNodes = parent.gridWidth * parent.gridHeight;
                @display("p=50,50");
        }

        node[gridWidth * gridHeight]: EidNode {
        }

    connections:
        // Horizontal connections
        for y=0..gridHeight-1, for x=0..gridWidth-2 {
            node[y*gridWidth + x].port++ <--> EidChannel <--> node[y*gridWidth + x + 1].port++;
        }

        // Vertical connections
        for y=0..gridHeight-2, for x=0..gridWidth-1 {
            node[y*gridWidth + x].port++ <--> EidChannel <--> node[(y+1)*gridWidth + x].port++;
        }
}

// ============================================================================
// Fair Comparison Network
// For comparing BGP vs DNS at the same abstraction level
// Both protocols operate over the SAME physical topology
// DNS additionally has logical "direct" connections to authority/resolver
// ============================================================================
network FairComparisonNetwork
{
    parameters:
        int numNodes = default(25);           // Total nodes in the network
        int gridWidth = default(5);           // For grid-like arrangement
        int gridHeight = default(5);
        int authorityNode = default(12);      // Central authority node
        int resolverNode = default(11);       // Resolver near authority
        @display("bgb=1000,1000");

    submodules:
        groundTruth: GroundTruth {
            parameters:
                totalNodes = parent.numNodes;
                @display("p=50,50");
        }

        // All nodes participate in the network
        // For BGP: all nodes run BGP protocol
        // For DNS: only some nodes have special roles, but all can be clients
        node[numNodes]: EidNode {
        }

    connections:
        // Grid connections (physical topology - same for both protocols)
        for y=0..gridHeight-1, for x=0..gridWidth-2 {
            node[y*gridWidth + x].port++ <--> EidChannel <--> node[y*gridWidth + x + 1].port++;
        }
        for y=0..gridHeight-2, for x=0..gridWidth-1 {
            node[y*gridWidth + x].port++ <--> EidChannel <--> node[(y+1)*gridWidth + x].port++;
        }
}

// ============================================================================
// Generic Configurable Network (topology from file or parameters)
// ============================================================================
network ConfigurableNetwork
{
    parameters:
        int numNodes = default(100);
        string topologyFile = default("");  // Optional: read from file
        double connectionProbability = default(0.1);  // For random topology
        bool useScaleFree = default(false);  // Use scale-free (Barabasi-Albert) model
        int scaleFreeM = default(3);  // Edges per new node in BA model
        @display("bgb=2000,2000");

    submodules:
        groundTruth: GroundTruth {
            parameters:
                totalNodes = parent.numNodes;
                @display("p=50,50");
        }

        node[numNodes]: EidNode {
        }

    // Connections are established programmatically in C++ based on parameters
    // This is a placeholder - actual connections set up in initialize()
}

// ============================================================================
// REALISTIC SCENARIO NETWORKS
// ============================================================================

// ============================================================================
// Terrestrial Disaster Response Network (Experiment 11)
// 22 nodes: Command Center, 3 Relays, 6 Teams, 12 Drones
// Hierarchy: Command -> Relays -> Teams -> Drones
// ============================================================================
network TerrestrialDisasterNetwork
{
    parameters:
        @display("bgb=1400,800");

    submodules:
        groundTruth: GroundTruth {
            parameters:
                totalNodes = 22;
                @display("p=50,50");
        }

        // Tier 1: Command Center (node 0) - central authority/resolver
        command: EidNode {
            parameters:
                nodeId = 0;
                @display("p=700,100;i=device/server_l");
        }

        // Tier 2: Mobile Relay Vehicles (nodes 1-3)
        relay[3]: EidNode {
            @display("p=300+400*index,250;i=device/router_l");
        }

        // Tier 3: Field Teams (nodes 4-9)
        team[6]: EidNode {
            @display("p=150+220*index,450;i=device/laptop");
        }

        // Tier 4: Drones/Sensors (nodes 10-21)
        drone[12]: EidNode {
            @display("p=100+110*index,650;i=device/device");
        }

    connections:
        // Command to Relays (10ms stable backhaul)
        command.port++ <--> EidChannel { delay = 10ms; } <--> relay[0].port++;
        command.port++ <--> EidChannel { delay = 10ms; } <--> relay[1].port++;
        command.port++ <--> EidChannel { delay = 10ms; } <--> relay[2].port++;

        // Relay cross-links (30ms for redundancy)
        relay[0].port++ <--> EidChannel { delay = 30ms; } <--> relay[1].port++;
        relay[1].port++ <--> EidChannel { delay = 30ms; } <--> relay[2].port++;

        // Relays to Teams (20ms wireless mesh)
        // Relay 0 -> Teams 0,1
        relay[0].port++ <--> TerrestrialWirelessChannel <--> team[0].port++;
        relay[0].port++ <--> TerrestrialWirelessChannel <--> team[1].port++;
        // Relay 1 -> Teams 2,3
        relay[1].port++ <--> TerrestrialWirelessChannel <--> team[2].port++;
        relay[1].port++ <--> TerrestrialWirelessChannel <--> team[3].port++;
        // Relay 2 -> Teams 4,5
        relay[2].port++ <--> TerrestrialWirelessChannel <--> team[4].port++;
        relay[2].port++ <--> TerrestrialWirelessChannel <--> team[5].port++;

        // Teams to Drones (5ms short-range radio)
        // Each team has 2 drones
        team[0].port++ <--> ShortRangeChannel <--> drone[0].port++;
        team[0].port++ <--> ShortRangeChannel <--> drone[1].port++;
        team[1].port++ <--> ShortRangeChannel <--> drone[2].port++;
        team[1].port++ <--> ShortRangeChannel <--> drone[3].port++;
        team[2].port++ <--> ShortRangeChannel <--> drone[4].port++;
        team[2].port++ <--> ShortRangeChannel <--> drone[5].port++;
        team[3].port++ <--> ShortRangeChannel <--> drone[6].port++;
        team[3].port++ <--> ShortRangeChannel <--> drone[7].port++;
        team[4].port++ <--> ShortRangeChannel <--> drone[8].port++;
        team[4].port++ <--> ShortRangeChannel <--> drone[9].port++;
        team[5].port++ <--> ShortRangeChannel <--> drone[10].port++;
        team[5].port++ <--> ShortRangeChannel <--> drone[11].port++;

        // Inter-team links (nearby teams can communicate)
        team[0].port++ <--> TerrestrialWirelessChannel <--> team[1].port++;
        team[2].port++ <--> TerrestrialWirelessChannel <--> team[3].port++;
        team[4].port++ <--> TerrestrialWirelessChannel <--> team[5].port++;
}

// ============================================================================
// Lunar Artemis Network (Experiment 12)
// 12 nodes: Earth DSN, Lunar Gateway, 2 Surface Bases, 4 Rovers, 4 EVA/Drones
// Key: 1.3s Earth-Moon delay, low latency on lunar surface
// ============================================================================
network LunarArtemisNetwork
{
    parameters:
        @display("bgb=1200,900");

    submodules:
        groundTruth: GroundTruth {
            parameters:
                totalNodes = 12;
                @display("p=50,50");
        }

        // Tier 0: Earth DSN (node 0) - Earth-based services
        earthDsn: EidNode {
            parameters:
                nodeId = 0;
                @display("p=600,50;i=device/antennatower_l");
        }

        // Tier 1: Lunar Gateway (node 1) - orbital relay, lunar authority
        gateway: EidNode {
            parameters:
                nodeId = 1;
                @display("p=600,200;i=device/satellite_l");
        }

        // Tier 2: Surface Bases (nodes 2-3)
        // South Pole Habitat
        southPoleBase: EidNode {
            parameters:
                nodeId = 2;
                @display("p=300,400;i=device/server_l");
        }
        // Equatorial Relay
        equatorialRelay: EidNode {
            parameters:
                nodeId = 3;
                @display("p=900,400;i=device/router_l");
        }

        // Tier 3: Rovers (nodes 4-7)
        rover[4]: EidNode {
            @display("p=150+200*index,600;i=device/car");
        }

        // Tier 4: EVA suits and drones (nodes 8-11)
        fieldAsset[4]: EidNode {
            @display("p=150+200*index,750;i=device/palm");
        }

    connections:
        // Earth-Moon link (1.3s delay)
        earthDsn.port++ <--> LunarChannel <--> gateway.port++;

        // Gateway to surface bases (250ms orbital relay)
        gateway.port++ <--> LunarOrbitalChannel <--> southPoleBase.port++;
        gateway.port++ <--> LunarOrbitalChannel <--> equatorialRelay.port++;

        // Surface base cross-link (50ms when visible)
        southPoleBase.port++ <--> EidChannel { delay = 50ms; } <--> equatorialRelay.port++;

        // South Pole Base to Rovers 0,1 (10ms line-of-sight)
        southPoleBase.port++ <--> LunarSurfaceChannel <--> rover[0].port++;
        southPoleBase.port++ <--> LunarSurfaceChannel <--> rover[1].port++;

        // Equatorial Relay to Rovers 2,3
        equatorialRelay.port++ <--> LunarSurfaceChannel <--> rover[2].port++;
        equatorialRelay.port++ <--> LunarSurfaceChannel <--> rover[3].port++;

        // Rovers to Field Assets (5ms short-range)
        rover[0].port++ <--> ShortRangeChannel <--> fieldAsset[0].port++;
        rover[1].port++ <--> ShortRangeChannel <--> fieldAsset[1].port++;
        rover[2].port++ <--> ShortRangeChannel <--> fieldAsset[2].port++;
        rover[3].port++ <--> ShortRangeChannel <--> fieldAsset[3].port++;

        // Rover mesh links (rovers can relay for each other)
        rover[0].port++ <--> LunarSurfaceChannel <--> rover[1].port++;
        rover[2].port++ <--> LunarSurfaceChannel <--> rover[3].port++;
}

// ============================================================================
// Mars Exploration Network (Experiment 13)
// 10 nodes: Earth DSN, Mars Relay Orbiter, 2 Habitats, 4 Rovers, 2 Instruments
// Key: 12-minute Earth-Mars delay, significant surface delays
// ============================================================================
network MarsExplorationNetwork
{
    parameters:
        @display("bgb=1200,900");

    submodules:
        groundTruth: GroundTruth {
            parameters:
                totalNodes = 10;
                @display("p=50,50");
        }

        // Tier 0: Earth DSN (node 0) - mission control
        earthDsn: EidNode {
            parameters:
                nodeId = 0;
                @display("p=600,50;i=device/antennatower_l");
        }

        // Tier 1: Mars Relay Orbiter (node 1) - local authority
        marsOrbiter: EidNode {
            parameters:
                nodeId = 1;
                @display("p=600,200;i=device/satellite_l");
        }

        // Tier 2: Surface Habitats (nodes 2-3)
        // Jezero Habitat (main base)
        jezeroHabitat: EidNode {
            parameters:
                nodeId = 2;
                @display("p=300,400;i=device/server_l");
        }
        // Olympus Outpost (remote base)
        olympusOutpost: EidNode {
            parameters:
                nodeId = 3;
                @display("p=900,400;i=device/router_l");
        }

        // Tier 3: Rovers (nodes 4-7)
        rover[4]: EidNode {
            @display("p=150+200*index,600;i=device/car");
        }

        // Tier 4: Deployed Instruments (nodes 8-9)
        instrument[2]: EidNode {
            @display("p=250+400*index,750;i=device/device");
        }

    connections:
        // Earth-Mars link (720s = 12 minutes delay)
        earthDsn.port++ <--> MarsInterplanetaryChannel <--> marsOrbiter.port++;

        // Orbiter to surface habitats (60s orbital relay)
        marsOrbiter.port++ <--> MarsOrbitalChannel <--> jezeroHabitat.port++;
        marsOrbiter.port++ <--> MarsOrbitalChannel <--> olympusOutpost.port++;

        // Habitat cross-link (30s long-distance surface link)
        jezeroHabitat.port++ <--> EidChannel { delay = 30s; } <--> olympusOutpost.port++;

        // Jezero Habitat to Rovers 0,1 (5s surface relay)
        jezeroHabitat.port++ <--> MarsSurfaceChannel <--> rover[0].port++;
        jezeroHabitat.port++ <--> MarsSurfaceChannel <--> rover[1].port++;

        // Olympus Outpost to Rovers 2,3
        olympusOutpost.port++ <--> MarsSurfaceChannel <--> rover[2].port++;
        olympusOutpost.port++ <--> MarsSurfaceChannel <--> rover[3].port++;

        // Rovers to Instruments (1s local deployment)
        rover[0].port++ <--> MarsLocalChannel <--> instrument[0].port++;
        rover[2].port++ <--> MarsLocalChannel <--> instrument[1].port++;

        // Rover mesh links (rovers can relay)
        rover[0].port++ <--> MarsSurfaceChannel <--> rover[1].port++;
        rover[2].port++ <--> MarsSurfaceChannel <--> rover[3].port++;
}
