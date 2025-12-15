// EidNode.h - Main node module header for EID distribution simulation

#ifndef __BGPDNS_EIDNODE_H
#define __BGPDNS_EIDNODE_H

#include <omnetpp.h>
#include <map>
#include <set>
#include <vector>
#include <queue>
#include <string>
#include <random>

#include "EidMessages_m.h"

using namespace omnetpp;

// Forward declaration
class GroundTruth;

// ============================================================================
// Data Structures
// ============================================================================

// BGP table entry
struct BgpEntry {
    int eid;
    int originId;
    int nextHop;            // Gate index to next hop
    int nextHopNodeId;      // Node ID of next hop
    int pathLength;
    int version;
    EndpointInfo endpoint;
    simtime_t lastUpdateTime;
    std::vector<int> path;  // Full path vector

    bool isValid() const { return originId >= 0; }
};

// DNS cache entry
struct DnsCacheEntry {
    int eid;
    EndpointInfo endpoint;
    int ttl;                // Original TTL
    simtime_t expiryTime;   // When cache entry expires
    simtime_t recordTime;   // When record was created at authority
    bool authoritative;

    bool isExpired() const { return simTime() >= expiryTime; }
};

// DNS authority record
struct DnsAuthorityRecord {
    int eid;
    int publisherId;
    EndpointInfo endpoint;
    int ttl;
    int version;
    simtime_t lastChangedTime;
};

// Pending DNS query tracking
struct PendingQuery {
    int queryId;
    int eid;
    int clientId;
    int requestingGate;     // Gate to send response back
    simtime_t queryTime;
    int hopCount;
    bool isLocalClient;     // True if this node originated the query
};

// ============================================================================
// EidNode Module Class
// ============================================================================

class EidNode : public cSimpleModule
{
  protected:
    // Identity
    int nodeId;

    // Role flags
    bool isPublisher;
    bool isClient;
    bool bgpEnabled;
    bool dnsEnabled;
    bool isResolver;
    bool isAuthority;
    bool isRoot;
    int authorityDomain;
    int resolverNodeId;
    int authorityNodeId;

    // BGP parameters
    double bgpKeepaliveInterval;
    double bgpHoldTime;
    bool bgpPathVector;
    int bgpMaxPathLength;

    // DNS parameters
    int dnsTtl;
    int dnsCacheSize;
    double dnsQueryTimeout;
    int dnsMaxHierarchyDepth;

    // Publisher parameters
    std::vector<int> publishEids;
    double publishStartTime;
    double publishInterval;
    std::string claProtocol;
    int claPort;

    // Client parameters
    std::vector<int> queryEids;
    double queryStartTime;
    double queryInterval;
    int queryCount;
    double queryZipfAlpha;
    int queriesSent;

    // Churn parameters
    double churnInterval;
    double churnProbability;
    double withdrawProbability;

    // Processing delay
    double processingDelayPerOp;

    // ========================================
    // State Tables
    // ========================================

    // BGP routing table: eid -> entry
    std::map<int, BgpEntry> bgpTable;

    // DNS cache (resolver): eid -> cache entry
    std::map<int, DnsCacheEntry> dnsCache;

    // DNS authority records: eid -> record
    std::map<int, DnsAuthorityRecord> dnsAuthorityDb;

    // Pending DNS queries: queryId -> pending info
    std::map<int, PendingQuery> pendingQueries;

    // Published EIDs and their versions (for churn)
    std::map<int, int> publishedVersions;

    // Neighbor tracking
    std::vector<int> neighborGates;    // Gate indices to neighbors
    std::map<int, int> gateToNodeId;   // Gate index -> neighbor node ID

    // ========================================
    // Self-messages for scheduling
    // ========================================
    cMessage *publishTimer;
    cMessage *queryTimer;
    cMessage *churnTimer;
    cMessage *keepaliveTimer;

    // ========================================
    // Statistics
    // ========================================
    // Signals
    simsignal_t bgpAnnouncesSentSignal;
    simsignal_t bgpAnnouncesReceivedSignal;
    simsignal_t bgpWithdrawsSentSignal;
    simsignal_t bgpWithdrawsReceivedSignal;
    simsignal_t bgpTableSizeSignal;
    simsignal_t bgpConvergenceTimeSignal;

    simsignal_t dnsQueriesSentSignal;
    simsignal_t dnsQueriesReceivedSignal;
    simsignal_t dnsResponsesSentSignal;
    simsignal_t dnsResponsesReceivedSignal;
    simsignal_t dnsRegistrationsSentSignal;
    simsignal_t dnsCacheSizeSignal;
    simsignal_t dnsCacheHitsSignal;
    simsignal_t dnsCacheMissesSignal;
    simsignal_t dnsQueryLatencySignal;

    simsignal_t messageBytesSentSignal;
    simsignal_t messageBytesReceivedSignal;
    simsignal_t tableOperationsSignal;

    simsignal_t discoveryLatencySignal;
    simsignal_t staleAnswersSignal;
    simsignal_t correctAnswersSignal;

    // Counters
    long tableOperationCount;
    int nextQueryId;

    // Ground truth reference
    GroundTruth *groundTruth;

    // Random number generator
    std::mt19937 rng;

    // ========================================
    // Initialization and Lifecycle
    // ========================================
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
    virtual void finish() override;

    void parseParameters();
    void initializeNeighbors();
    void scheduleInitialEvents();

    // ========================================
    // BGP-like Push Implementation
    // ========================================
    void handleBgpAnnounce(BgpAnnounce *msg, int arrivalGate);
    void handleBgpWithdraw(BgpWithdraw *msg, int arrivalGate);
    void handleBgpKeepalive(BgpKeepalive *msg);

    void bgpPublishEid(int eid);
    void bgpWithdrawEid(int eid);
    void bgpUpdateEid(int eid);
    void bgpForwardAnnounce(BgpAnnounce *msg, int excludeGate);
    void bgpForwardWithdraw(BgpWithdraw *msg, int excludeGate);

    bool bgpShouldAccept(const BgpAnnounce *msg, int candidatePathLen);
    void bgpRecordTableChange(int eid, simtime_t originTime);

    // ========================================
    // DNS-like Pull Implementation
    // ========================================
    void handleDnsQuery(DnsQuery *msg, int arrivalGate);
    void handleDnsResponse(DnsResponse *msg);
    void handleDnsRegister(DnsRegister *msg);
    void handleDnsDeregister(DnsDeregister *msg);
    void handleDnsReferral(DnsReferral *msg, int arrivalGate);

    void dnsRegisterEid(int eid);
    void dnsDeregisterEid(int eid);
    void dnsQueryEid(int eid);

    void dnsForwardQuery(DnsQuery *msg, int targetNodeId);
    void dnsSendResponse(int queryId, int eid, bool found,
                         const EndpointInfo& endpoint, int ttl,
                         bool cacheHit, bool authoritative,
                         simtime_t recordTime, int toGate);
    void dnsAddToCache(int eid, const EndpointInfo& endpoint, int ttl,
                       simtime_t recordTime, bool authoritative);
    DnsCacheEntry* dnsLookupCache(int eid);
    void dnsEvictCache();

    int findAuthorityForEid(int eid);
    int findResolverForNode();
    int findRootServer();
    int findGateToNode(int targetNodeId);

    // ========================================
    // Timer Handlers
    // ========================================
    void handlePublishTimer();
    void handleQueryTimer();
    void handleChurnTimer();
    void handleKeepaliveTimer();

    // ========================================
    // Utility Functions
    // ========================================
    void sendToGate(cMessage *msg, int gateIndex);
    void sendToAllNeighbors(cMessage *msg, int excludeGate = -1);
    void recordTableOperation();
    void recordBytesSent(int bytes);
    void recordBytesReceived(int bytes);

    int selectQueryEid();  // Select EID to query based on distribution
    EndpointInfo createEndpointInfo();

    std::vector<int> parseIntList(const std::string& str);
    std::string intListToString(const std::vector<int>& list);

  public:
    EidNode() : publishTimer(nullptr), queryTimer(nullptr),
                churnTimer(nullptr), keepaliveTimer(nullptr),
                groundTruth(nullptr), tableOperationCount(0), nextQueryId(0) {}
    virtual ~EidNode();

    // Public accessors for GroundTruth module
    int getNodeId() const { return nodeId; }
    const std::map<int, BgpEntry>& getBgpTable() const { return bgpTable; }
    const std::map<int, DnsCacheEntry>& getDnsCache() const { return dnsCache; }
    const std::map<int, DnsAuthorityRecord>& getDnsAuthorityDb() const { return dnsAuthorityDb; }
    long getTableOperationCount() const { return tableOperationCount; }
    bool isBgpEnabled() const { return bgpEnabled; }
    bool isDnsEnabled() const { return dnsEnabled; }
};

#endif // __BGPDNS_EIDNODE_H
