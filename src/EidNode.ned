// EidNode.ned - Main node module for EID distribution simulation
// Supports both BGP-like (push) and DNS-like (pull) approaches

package bgpdns;

simple EidNode
{
    parameters:
        // Node identity
        int nodeId = default(-1);  // Auto-assigned if -1

        // Role parameters
        bool isPublisher = default(false);      // Can originate/register EIDs
        bool isClient = default(false);         // Can query/resolve EIDs
        bool bgpEnabled = default(true);        // Participates in BGP-like distribution
        bool dnsEnabled = default(true);        // Participates in DNS-like resolution

        // DNS-specific roles
        bool isResolver = default(false);       // Acts as DNS resolver
        bool isAuthority = default(false);      // Acts as authoritative DNS server
        bool isRoot = default(false);           // Acts as DNS root server
        int authorityDomain = default(-1);      // Which domain this authority serves (-1 = all)
        int resolverNodeId = default(-1);       // Which resolver this node uses (-1 = self or nearest)
        int authorityNodeId = default(-1);      // Which authority this publisher uses

        // BGP parameters
        double bgpKeepaliveInterval @unit(s) = default(30s);
        double bgpHoldTime @unit(s) = default(90s);
        bool bgpPathVector = default(true);     // Use path vector (vs distance vector only)
        int bgpMaxPathLength = default(100);    // Maximum acceptable path length

        // DNS parameters
        int dnsTtl @unit(s) = default(300s);    // Default TTL for DNS records
        int dnsCacheSize = default(10000);      // Maximum cache entries
        double dnsQueryTimeout @unit(s) = default(5s);
        int dnsMaxHierarchyDepth = default(5);  // Maximum referral chain depth

        // Publisher parameters (if isPublisher)
        string publishEids = default("");       // Comma-separated list of EIDs to publish
        double publishStartTime @unit(s) = default(1s);
        double publishInterval @unit(s) = default(0s);  // 0 = publish once
        string claProtocol = default("tcpcl");
        int claPort = default(4556);

        // Client parameters (if isClient)
        string queryEids = default("");         // Comma-separated list of EIDs to query (empty = random)
        double queryStartTime @unit(s) = default(10s);
        double queryInterval @unit(s) = default(1s);
        int queryCount = default(100);          // Number of queries to generate
        double queryZipfAlpha = default(0.0);   // 0 = uniform, >0 = Zipf distribution

        // Churn parameters
        double churnInterval @unit(s) = default(0s);    // 0 = no churn
        double churnProbability = default(0.1);         // Probability of update/withdraw per interval
        double withdrawProbability = default(0.3);      // Of churn events, fraction that are withdraws

        // Processing overhead simulation
        double processingDelayPerOp @unit(s) = default(0.0001s);  // Per table operation

        // Statistics
        @signal[bgpAnnouncesSent](type=long);
        @signal[bgpAnnouncesReceived](type=long);
        @signal[bgpWithdrawsSent](type=long);
        @signal[bgpWithdrawsReceived](type=long);
        @signal[bgpTableSize](type=long);
        @signal[bgpConvergenceTime](type=simtime_t);

        @signal[dnsQueriesSent](type=long);
        @signal[dnsQueriesReceived](type=long);
        @signal[dnsResponsesSent](type=long);
        @signal[dnsResponsesReceived](type=long);
        @signal[dnsRegistrationsSent](type=long);
        @signal[dnsCacheSize](type=long);
        @signal[dnsCacheHits](type=long);
        @signal[dnsCacheMisses](type=long);
        @signal[dnsQueryLatency](type=simtime_t);

        @signal[messageBytesSent](type=long);
        @signal[messageBytesReceived](type=long);
        @signal[tableOperations](type=long);

        @signal[discoveryLatency](type=simtime_t);
        @signal[staleAnswers](type=long);
        @signal[correctAnswers](type=long);

        @statistic[bgpAnnouncesSent](record=count,sum,vector);
        @statistic[bgpAnnouncesReceived](record=count,sum,vector);
        @statistic[bgpWithdrawsSent](record=count,sum,vector);
        @statistic[bgpWithdrawsReceived](record=count,sum,vector);
        @statistic[bgpTableSize](record=last,max,timeavg,vector);
        @statistic[bgpConvergenceTime](record=mean,max,histogram,vector);

        @statistic[dnsQueriesSent](record=count,sum,vector);
        @statistic[dnsQueriesReceived](record=count,sum,vector);
        @statistic[dnsResponsesSent](record=count,sum,vector);
        @statistic[dnsResponsesReceived](record=count,sum,vector);
        @statistic[dnsRegistrationsSent](record=count,sum,vector);
        @statistic[dnsCacheSize](record=last,max,timeavg,vector);
        @statistic[dnsCacheHits](record=count,sum,vector);
        @statistic[dnsCacheMisses](record=count,sum,vector);
        @statistic[dnsQueryLatency](record=mean,min,max,histogram,vector);

        @statistic[messageBytesSent](record=sum,vector);
        @statistic[messageBytesReceived](record=sum,vector);
        @statistic[tableOperations](record=sum,vector);

        @statistic[discoveryLatency](record=mean,min,max,histogram,vector);
        @statistic[staleAnswers](record=count,sum);
        @statistic[correctAnswers](record=count,sum);

        @display("i=device/router");

    gates:
        inout port[];  // Bidirectional ports to neighbors
}
