// EidMessages.msg - Message definitions for BGP-like and DNS-like EID distribution
// No INET dependency - pure OMNeT++ abstract model

cplusplus {{
#include <string>
#include <vector>
}}

// ============================================================================
// Common Structures
// ============================================================================

// Endpoint attributes (simplified SVCB-like structure)
struct EndpointInfo
{
    int targetNodeId;           // The responsible BP agent node
    string claProtocol;         // "tcpcl", "udpcl", "quic", "ltp"
    int port;                   // CLA port
    string hint;                // Additional endpoint hints
}

// ============================================================================
// BGP-like Messages (Push Model)
// ============================================================================

// BGP Announce message - propagates EID reachability
packet BgpAnnounce
{
    int eid;                    // The EID being announced
    int originId;               // Original publisher node ID
    int pathLength;             // Path vector length (hop count)
    int version;                // Version number for updates/churn
    EndpointInfo endpoint;      // Target endpoint info
    simtime_t originTime;       // When the announcement was originated
    int path[];                 // Path vector (list of node IDs traversed)

    // Nominal message size for overhead calculation
    int byteSize = 64;          // Base size in bytes
}

// BGP Withdraw message - removes EID reachability
packet BgpWithdraw
{
    int eid;                    // The EID being withdrawn
    int originId;               // Original publisher node ID
    int version;                // Version to identify which announcement to withdraw
    simtime_t originTime;       // When withdrawal was originated

    int byteSize = 32;          // Base size in bytes
}

// BGP Keepalive (optional - for session management)
packet BgpKeepalive
{
    int senderId;
    int byteSize = 8;
}

// ============================================================================
// DNS-like Messages (Pull Model)
// ============================================================================

// DNS Query message
packet DnsQuery
{
    int eid;                    // The EID being queried
    int queryId;                // Unique query identifier
    int clientId;               // Original client node ID
    int hopCount;               // How many hops this query has traversed
    simtime_t queryTime;        // When query was initiated

    int byteSize = 48;          // Base size in bytes
}

// DNS Response message
packet DnsResponse
{
    int eid;                    // The EID being resolved
    int queryId;                // Matching query identifier
    bool found;                 // Whether the EID was found
    EndpointInfo endpoint;      // Target endpoint info (if found)
    int ttl;                    // Time-to-live in seconds
    bool cacheHit;              // Whether this was a cache hit
    bool authoritative;         // Whether this is from authoritative source
    simtime_t recordTime;       // When the record was last updated
    int hopCount;               // Response path length

    int byteSize = 80;          // Base size in bytes
}

// DNS Registration message (publisher -> authority)
packet DnsRegister
{
    int eid;                    // The EID being registered
    int publisherId;            // Publisher node ID
    EndpointInfo endpoint;      // Target endpoint info
    int ttl;                    // Requested TTL
    int version;                // Version for updates

    int byteSize = 72;          // Base size in bytes
}

// DNS Deregistration message
packet DnsDeregister
{
    int eid;                    // The EID being deregistered
    int publisherId;            // Publisher node ID
    int version;                // Version

    int byteSize = 24;          // Base size in bytes
}

// DNS Referral message (for hierarchical resolution)
packet DnsReferral
{
    int eid;                    // The EID being queried
    int queryId;                // Matching query identifier
    int referToNodeId;          // Node to query next
    int level;                  // Hierarchy level

    int byteSize = 32;          // Base size in bytes
}

// ============================================================================
// Internal/Control Messages
// ============================================================================

// Self-message for scheduled events
packet SelfMessage
{
    int eventType;              // 0=publish, 1=withdraw, 2=query, 3=update, 4=churn
    int eid;                    // Associated EID (if applicable)
    int targetNode;             // Target node (if applicable)
}

// Metrics snapshot request (from metrics collector)
packet MetricsRequest
{
    int requestId;
}

// Metrics snapshot response
packet MetricsResponse
{
    int requestId;
    int nodeId;
    int bgpTableSize;
    int dnsCacheSize;
    int dnsAuthoritySize;
    long messagesSent;
    long messagesReceived;
    long bytesSent;
    long bytesReceived;
    long tableOperations;
}

// Link status message (for disruption simulation)
packet LinkStatus
{
    int linkId;
    bool isUp;
    simtime_t changeTime;
}
