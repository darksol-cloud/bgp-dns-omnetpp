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
