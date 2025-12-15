// EidNode.cc - Main node module implementation for EID distribution simulation

#include "EidNode.h"
#include "GroundTruth.h"
#include <algorithm>
#include <sstream>
#include <cmath>

Define_Module(EidNode);

// ============================================================================
// Initialization and Lifecycle
// ============================================================================

EidNode::~EidNode()
{
    cancelAndDelete(publishTimer);
    cancelAndDelete(queryTimer);
    cancelAndDelete(churnTimer);
    cancelAndDelete(keepaliveTimer);
}

void EidNode::initialize()
{
    // Initialize RNG with node-specific seed
    rng.seed(getId() + intuniform(0, 1000000));

    parseParameters();
    initializeNeighbors();

    // Register signals
    bgpAnnouncesSentSignal = registerSignal("bgpAnnouncesSent");
    bgpAnnouncesReceivedSignal = registerSignal("bgpAnnouncesReceived");
    bgpWithdrawsSentSignal = registerSignal("bgpWithdrawsSent");
    bgpWithdrawsReceivedSignal = registerSignal("bgpWithdrawsReceived");
    bgpTableSizeSignal = registerSignal("bgpTableSize");
    bgpConvergenceTimeSignal = registerSignal("bgpConvergenceTime");

    dnsQueriesSentSignal = registerSignal("dnsQueriesSent");
    dnsQueriesReceivedSignal = registerSignal("dnsQueriesReceived");
    dnsResponsesSentSignal = registerSignal("dnsResponsesSent");
    dnsResponsesReceivedSignal = registerSignal("dnsResponsesReceived");
    dnsRegistrationsSentSignal = registerSignal("dnsRegistrationsSent");
    dnsCacheSizeSignal = registerSignal("dnsCacheSize");
    dnsCacheHitsSignal = registerSignal("dnsCacheHits");
    dnsCacheMissesSignal = registerSignal("dnsCacheMisses");
    dnsQueryLatencySignal = registerSignal("dnsQueryLatency");

    messageBytesSentSignal = registerSignal("messageBytesSent");
    messageBytesReceivedSignal = registerSignal("messageBytesReceived");
    tableOperationsSignal = registerSignal("tableOperations");

    discoveryLatencySignal = registerSignal("discoveryLatency");
    staleAnswersSignal = registerSignal("staleAnswers");
    correctAnswersSignal = registerSignal("correctAnswers");

    // Get reference to GroundTruth module
    cModule *gtModule = getParentModule()->getSubmodule("groundTruth");
    if (gtModule) {
        groundTruth = check_and_cast<GroundTruth*>(gtModule);
    }

    // Initialize counters
    tableOperationCount = 0;
    nextQueryId = nodeId * 1000000;  // Unique query ID space per node
    queriesSent = 0;

    scheduleInitialEvents();

    EV_INFO << "EidNode " << nodeId << " initialized"
            << " [publisher=" << isPublisher
            << ", client=" << isClient
            << ", bgp=" << bgpEnabled
            << ", dns=" << dnsEnabled
            << ", resolver=" << isResolver
            << ", authority=" << isAuthority
            << "]" << endl;
}

void EidNode::parseParameters()
{
    nodeId = par("nodeId").intValue();
    if (nodeId < 0) {
        // Use module index if available, otherwise use module ID
        if (isVector()) {
            nodeId = getIndex();
        } else {
            nodeId = getId();  // Fallback to unique module ID
        }
    }

    isPublisher = par("isPublisher").boolValue();
    isClient = par("isClient").boolValue();
    bgpEnabled = par("bgpEnabled").boolValue();
    dnsEnabled = par("dnsEnabled").boolValue();
    isResolver = par("isResolver").boolValue();
    isAuthority = par("isAuthority").boolValue();
    isRoot = par("isRoot").boolValue();
    authorityDomain = par("authorityDomain").intValue();
    resolverNodeId = par("resolverNodeId").intValue();
    authorityNodeId = par("authorityNodeId").intValue();

    bgpKeepaliveInterval = par("bgpKeepaliveInterval").doubleValue();
    bgpHoldTime = par("bgpHoldTime").doubleValue();
    bgpPathVector = par("bgpPathVector").boolValue();
    bgpMaxPathLength = par("bgpMaxPathLength").intValue();

    dnsTtl = par("dnsTtl").intValue();
    dnsCacheSize = par("dnsCacheSize").intValue();
    dnsQueryTimeout = par("dnsQueryTimeout").doubleValue();
    dnsMaxHierarchyDepth = par("dnsMaxHierarchyDepth").intValue();

    publishEids = parseIntList(par("publishEids").stringValue());
    publishStartTime = par("publishStartTime").doubleValue();
    publishInterval = par("publishInterval").doubleValue();
    claProtocol = par("claProtocol").stringValue();
    claPort = par("claPort").intValue();

    queryEids = parseIntList(par("queryEids").stringValue());
    queryStartTime = par("queryStartTime").doubleValue();
    queryInterval = par("queryInterval").doubleValue();
    queryCount = par("queryCount").intValue();
    queryZipfAlpha = par("queryZipfAlpha").doubleValue();

    churnInterval = par("churnInterval").doubleValue();
    churnProbability = par("churnProbability").doubleValue();
    withdrawProbability = par("withdrawProbability").doubleValue();

    processingDelayPerOp = par("processingDelayPerOp").doubleValue();
}

void EidNode::initializeNeighbors()
{
    int numPorts = gateSize("port");
    for (int i = 0; i < numPorts; i++) {
        cGate *outGate = gate("port$o", i);
        if (outGate && outGate->isConnected()) {
            neighborGates.push_back(i);

            // Try to determine neighbor node ID
            cGate *remoteGate = outGate->getNextGate();
            if (remoteGate) {
                cModule *remoteModule = remoteGate->getOwnerModule();
                if (remoteModule) {
                    EidNode *neighbor = dynamic_cast<EidNode*>(remoteModule);
                    if (neighbor) {
                        gateToNodeId[i] = neighbor->getIndex();
                    }
                }
            }
        }
    }

    EV_DEBUG << "Node " << nodeId << " has " << neighborGates.size() << " neighbors" << endl;
}

void EidNode::scheduleInitialEvents()
{
    // Schedule publishing
    if (isPublisher && !publishEids.empty()) {
        publishTimer = new cMessage("publishTimer");
        scheduleAt(simTime() + publishStartTime, publishTimer);
    }

    // Schedule querying
    if (isClient && queryCount > 0) {
        queryTimer = new cMessage("queryTimer");
        scheduleAt(simTime() + queryStartTime, queryTimer);
    }

    // Schedule churn
    if (isPublisher && churnInterval > 0) {
        churnTimer = new cMessage("churnTimer");
        scheduleAt(simTime() + publishStartTime + churnInterval, churnTimer);
    }

    // Schedule BGP keepalives (optional)
    if (bgpEnabled && bgpKeepaliveInterval > 0) {
        keepaliveTimer = new cMessage("keepaliveTimer");
        scheduleAt(simTime() + bgpKeepaliveInterval, keepaliveTimer);
    }
}

// ============================================================================
// Message Handling
// ============================================================================

void EidNode::handleMessage(cMessage *msg)
{
    if (msg->isSelfMessage()) {
        if (msg == publishTimer) {
            handlePublishTimer();
        } else if (msg == queryTimer) {
            handleQueryTimer();
        } else if (msg == churnTimer) {
            handleChurnTimer();
        } else if (msg == keepaliveTimer) {
            handleKeepaliveTimer();
        }
        return;
    }

    // Record received bytes
    if (cPacket *pkt = dynamic_cast<cPacket*>(msg)) {
        recordBytesReceived(pkt->getByteLength());
    }

    int arrivalGate = msg->getArrivalGate()->getIndex();

    // Handle BGP messages
    if (BgpAnnounce *announce = dynamic_cast<BgpAnnounce*>(msg)) {
        if (bgpEnabled) {
            handleBgpAnnounce(announce, arrivalGate);
        }
        delete msg;
        return;
    }

    if (BgpWithdraw *withdraw = dynamic_cast<BgpWithdraw*>(msg)) {
        if (bgpEnabled) {
            handleBgpWithdraw(withdraw, arrivalGate);
        }
        delete msg;
        return;
    }

    if (BgpKeepalive *keepalive = dynamic_cast<BgpKeepalive*>(msg)) {
        if (bgpEnabled) {
            handleBgpKeepalive(keepalive);
        }
        delete msg;
        return;
    }

    // Handle DNS messages
    if (DnsQuery *query = dynamic_cast<DnsQuery*>(msg)) {
        if (dnsEnabled) {
            handleDnsQuery(query, arrivalGate);
        }
        delete msg;
        return;
    }

    if (DnsResponse *response = dynamic_cast<DnsResponse*>(msg)) {
        if (dnsEnabled) {
            handleDnsResponse(response);
        }
        delete msg;
        return;
    }

    if (DnsRegister *reg = dynamic_cast<DnsRegister*>(msg)) {
        if (dnsEnabled && isAuthority) {
            handleDnsRegister(reg);
        }
        delete msg;
        return;
    }

    if (DnsDeregister *dereg = dynamic_cast<DnsDeregister*>(msg)) {
        if (dnsEnabled && isAuthority) {
            handleDnsDeregister(dereg);
        }
        delete msg;
        return;
    }

    if (DnsReferral *referral = dynamic_cast<DnsReferral*>(msg)) {
        if (dnsEnabled) {
            handleDnsReferral(referral, arrivalGate);
        }
        delete msg;
        return;
    }

    EV_WARN << "Node " << nodeId << " received unknown message type" << endl;
    delete msg;
}

void EidNode::finish()
{
    // Record final statistics
    emit(bgpTableSizeSignal, (long)bgpTable.size());
    emit(dnsCacheSizeSignal, (long)dnsCache.size());

    recordScalar("finalBgpTableSize", bgpTable.size());
    recordScalar("finalDnsCacheSize", dnsCache.size());
    recordScalar("finalDnsAuthoritySize", dnsAuthorityDb.size());
    recordScalar("totalTableOperations", tableOperationCount);
    recordScalar("nodeId", nodeId);
}

// ============================================================================
// BGP-like Push Implementation
// ============================================================================

void EidNode::bgpPublishEid(int eid)
{
    EV_INFO << "Node " << nodeId << " publishing EID " << eid << " via BGP" << endl;

    // Update or create version
    int version = 1;
    if (publishedVersions.find(eid) != publishedVersions.end()) {
        version = ++publishedVersions[eid];
    } else {
        publishedVersions[eid] = version;
    }

    // Create local table entry
    BgpEntry entry;
    entry.eid = eid;
    entry.originId = nodeId;
    entry.nextHop = -1;  // Local
    entry.nextHopNodeId = nodeId;
    entry.pathLength = 0;
    entry.version = version;
    entry.endpoint = createEndpointInfo();
    entry.lastUpdateTime = simTime();
    entry.path.push_back(nodeId);

    bgpTable[eid] = entry;
    recordTableOperation();
    emit(bgpTableSizeSignal, (long)bgpTable.size());

    // Notify ground truth
    if (groundTruth) {
        groundTruth->recordEidPublish(eid, nodeId, entry.endpoint, simTime());
    }

    // Create and broadcast announcement
    BgpAnnounce *announce = new BgpAnnounce("BgpAnnounce");
    announce->setEid(eid);
    announce->setOriginId(nodeId);
    announce->setPathLength(0);
    announce->setVersion(version);
    announce->setEndpoint(entry.endpoint);
    announce->setOriginTime(simTime());
    announce->setPathArraySize(1);
    announce->setPath(0, nodeId);
    announce->setByteLength(announce->getByteSize());

    bgpForwardAnnounce(announce, -1);
    emit(bgpAnnouncesSentSignal, (long)neighborGates.size());
}

void EidNode::bgpWithdrawEid(int eid)
{
    EV_INFO << "Node " << nodeId << " withdrawing EID " << eid << " via BGP" << endl;

    if (publishedVersions.find(eid) == publishedVersions.end()) {
        EV_WARN << "Node " << nodeId << " tried to withdraw unpublished EID " << eid << endl;
        return;
    }

    int version = ++publishedVersions[eid];

    // Remove from local table
    bgpTable.erase(eid);
    recordTableOperation();
    emit(bgpTableSizeSignal, (long)bgpTable.size());

    // Notify ground truth
    if (groundTruth) {
        groundTruth->recordEidWithdraw(eid, nodeId, simTime());
    }

    // Create and broadcast withdrawal
    BgpWithdraw *withdraw = new BgpWithdraw("BgpWithdraw");
    withdraw->setEid(eid);
    withdraw->setOriginId(nodeId);
    withdraw->setVersion(version);
    withdraw->setOriginTime(simTime());
    withdraw->setByteLength(withdraw->getByteSize());

    bgpForwardWithdraw(withdraw, -1);
    emit(bgpWithdrawsSentSignal, (long)neighborGates.size());
}

void EidNode::bgpUpdateEid(int eid)
{
    // Update is essentially re-publish with new version
    bgpPublishEid(eid);
}

void EidNode::handleBgpAnnounce(BgpAnnounce *msg, int arrivalGate)
{
    emit(bgpAnnouncesReceivedSignal, 1L);

    int eid = msg->getEid();
    int candidatePathLen = msg->getPathLength() + 1;

    EV_DEBUG << "Node " << nodeId << " received BGP announce for EID " << eid
             << " from origin " << msg->getOriginId()
             << " pathLen=" << candidatePathLen << endl;

    // Check for loops in path vector
    if (bgpPathVector) {
        for (unsigned int i = 0; i < msg->getPathArraySize(); i++) {
            if (msg->getPath(i) == nodeId) {
                EV_DEBUG << "Node " << nodeId << " dropping announce due to loop" << endl;
                return;
            }
        }
    }

    // Check path length limit
    if (candidatePathLen > bgpMaxPathLength) {
        EV_DEBUG << "Node " << nodeId << " dropping announce due to path length" << endl;
        return;
    }

    // Determine if we should accept this announcement
    if (!bgpShouldAccept(msg, candidatePathLen)) {
        return;
    }

    // Get next hop node ID
    int nextHopNodeId = -1;
    if (gateToNodeId.find(arrivalGate) != gateToNodeId.end()) {
        nextHopNodeId = gateToNodeId[arrivalGate];
    }

    // Update local table
    BgpEntry entry;
    entry.eid = eid;
    entry.originId = msg->getOriginId();
    entry.nextHop = arrivalGate;
    entry.nextHopNodeId = nextHopNodeId;
    entry.pathLength = candidatePathLen;
    entry.version = msg->getVersion();
    entry.endpoint = msg->getEndpoint();
    entry.lastUpdateTime = simTime();

    // Copy and extend path
    entry.path.clear();
    for (unsigned int i = 0; i < msg->getPathArraySize(); i++) {
        entry.path.push_back(msg->getPath(i));
    }
    entry.path.push_back(nodeId);

    bool isNew = (bgpTable.find(eid) == bgpTable.end());
    bgpTable[eid] = entry;
    recordTableOperation();
    emit(bgpTableSizeSignal, (long)bgpTable.size());

    // Record convergence time
    if (isNew) {
        simtime_t latency = simTime() - msg->getOriginTime();
        emit(discoveryLatencySignal, latency);
        emit(bgpConvergenceTimeSignal, latency);
    }

    // Forward to other neighbors
    BgpAnnounce *forward = msg->dup();
    forward->setPathLength(candidatePathLen);
    forward->setPathArraySize(entry.path.size());
    for (size_t i = 0; i < entry.path.size(); i++) {
        forward->setPath(i, entry.path[i]);
    }
    forward->setByteLength(forward->getByteSize() + entry.path.size() * 4);

    bgpForwardAnnounce(forward, arrivalGate);
}

bool EidNode::bgpShouldAccept(const BgpAnnounce *msg, int candidatePathLen)
{
    int eid = msg->getEid();
    auto it = bgpTable.find(eid);

    if (it == bgpTable.end()) {
        // New EID - accept
        return true;
    }

    const BgpEntry& existing = it->second;

    // Same origin, newer version - accept (handles updates)
    if (existing.originId == msg->getOriginId()) {
        return msg->getVersion() > existing.version;
    }

    // Shorter path - accept
    if (candidatePathLen < existing.pathLength) {
        return true;
    }

    // Same path length, lower origin ID wins (deterministic tie-breaker)
    if (candidatePathLen == existing.pathLength &&
        msg->getOriginId() < existing.originId) {
        return true;
    }

    return false;
}

void EidNode::handleBgpWithdraw(BgpWithdraw *msg, int arrivalGate)
{
    emit(bgpWithdrawsReceivedSignal, 1L);

    int eid = msg->getEid();

    EV_DEBUG << "Node " << nodeId << " received BGP withdraw for EID " << eid
             << " from origin " << msg->getOriginId() << endl;

    auto it = bgpTable.find(eid);
    if (it == bgpTable.end()) {
        return;  // Don't have this EID
    }

    // Only process if this withdraw is from the origin we know about
    // and has a newer or matching version
    if (it->second.originId == msg->getOriginId() &&
        msg->getVersion() >= it->second.version) {

        bgpTable.erase(it);
        recordTableOperation();
        emit(bgpTableSizeSignal, (long)bgpTable.size());

        // Forward withdrawal
        bgpForwardWithdraw(msg->dup(), arrivalGate);
    }
}

void EidNode::handleBgpKeepalive(BgpKeepalive *msg)
{
    // Simple keepalive handling - just acknowledge receipt
    EV_DEBUG << "Node " << nodeId << " received keepalive from " << msg->getSenderId() << endl;
}

void EidNode::bgpForwardAnnounce(BgpAnnounce *msg, int excludeGate)
{
    int sentCount = 0;
    for (int gateIdx : neighborGates) {
        if (gateIdx != excludeGate) {
            BgpAnnounce *copy = msg->dup();
            sendToGate(copy, gateIdx);
            sentCount++;
        }
    }

    if (sentCount > 0) {
        emit(bgpAnnouncesSentSignal, (long)sentCount);
        recordBytesSent(msg->getByteLength() * sentCount);
    }

    delete msg;
}

void EidNode::bgpForwardWithdraw(BgpWithdraw *msg, int excludeGate)
{
    int sentCount = 0;
    for (int gateIdx : neighborGates) {
        if (gateIdx != excludeGate) {
            BgpWithdraw *copy = msg->dup();
            sendToGate(copy, gateIdx);
            sentCount++;
        }
    }

    if (sentCount > 0) {
        emit(bgpWithdrawsSentSignal, (long)sentCount);
        recordBytesSent(msg->getByteLength() * sentCount);
    }

    delete msg;
}

// ============================================================================
// DNS-like Pull Implementation
// ============================================================================

void EidNode::dnsRegisterEid(int eid)
{
    EV_INFO << "Node " << nodeId << " registering EID " << eid << " via DNS" << endl;

    // Update version
    int version = 1;
    if (publishedVersions.find(eid) != publishedVersions.end()) {
        version = ++publishedVersions[eid];
    } else {
        publishedVersions[eid] = version;
    }

    EndpointInfo endpoint = createEndpointInfo();

    // If we are an authority, register locally
    if (isAuthority) {
        DnsAuthorityRecord record;
        record.eid = eid;
        record.publisherId = nodeId;
        record.endpoint = endpoint;
        record.ttl = dnsTtl;
        record.version = version;
        record.lastChangedTime = simTime();
        dnsAuthorityDb[eid] = record;
        recordTableOperation();

        // Notify ground truth
        if (groundTruth) {
            groundTruth->recordEidPublish(eid, nodeId, endpoint, simTime());
        }
        return;
    }

    // Otherwise, send registration to authority
    int authNode = findAuthorityForEid(eid);
    if (authNode < 0) {
        EV_WARN << "Node " << nodeId << " cannot find authority for EID " << eid << endl;
        return;
    }

    DnsRegister *reg = new DnsRegister("DnsRegister");
    reg->setEid(eid);
    reg->setPublisherId(nodeId);
    reg->setEndpoint(endpoint);
    reg->setTtl(dnsTtl);
    reg->setVersion(version);
    reg->setByteLength(reg->getByteSize());

    int gateIdx = findGateToNode(authNode);
    if (gateIdx >= 0) {
        sendToGate(reg, gateIdx);
        emit(dnsRegistrationsSentSignal, 1L);
        recordBytesSent(reg->getByteLength());

        // Notify ground truth (registration in progress)
        if (groundTruth) {
            groundTruth->recordEidPublish(eid, nodeId, endpoint, simTime());
        }
    } else {
        EV_WARN << "Node " << nodeId << " has no route to authority " << authNode << endl;
        delete reg;
    }
}

void EidNode::dnsDeregisterEid(int eid)
{
    EV_INFO << "Node " << nodeId << " deregistering EID " << eid << " via DNS" << endl;

    if (publishedVersions.find(eid) == publishedVersions.end()) {
        return;
    }

    int version = ++publishedVersions[eid];

    // If we are authority, remove locally
    if (isAuthority) {
        dnsAuthorityDb.erase(eid);
        recordTableOperation();

        if (groundTruth) {
            groundTruth->recordEidWithdraw(eid, nodeId, simTime());
        }
        return;
    }

    // Send deregistration to authority
    int authNode = findAuthorityForEid(eid);
    if (authNode < 0) {
        return;
    }

    DnsDeregister *dereg = new DnsDeregister("DnsDeregister");
    dereg->setEid(eid);
    dereg->setPublisherId(nodeId);
    dereg->setVersion(version);
    dereg->setByteLength(dereg->getByteSize());

    int gateIdx = findGateToNode(authNode);
    if (gateIdx >= 0) {
        sendToGate(dereg, gateIdx);
        recordBytesSent(dereg->getByteLength());

        if (groundTruth) {
            groundTruth->recordEidWithdraw(eid, nodeId, simTime());
        }
    } else {
        delete dereg;
    }
}

void EidNode::dnsQueryEid(int eid)
{
    EV_DEBUG << "Node " << nodeId << " querying EID " << eid << endl;

    int queryId = nextQueryId++;

    // Check local cache first
    DnsCacheEntry *cached = dnsLookupCache(eid);
    if (cached && !cached->isExpired()) {
        emit(dnsCacheHitsSignal, 1L);

        // Check if answer is stale (correct endpoint but outdated)
        bool isStale = false;
        if (groundTruth) {
            isStale = !groundTruth->isRecordCurrent(eid, cached->endpoint, cached->recordTime);
            if (isStale) {
                emit(staleAnswersSignal, 1L);
            } else {
                emit(correctAnswersSignal, 1L);
            }
        }

        EV_DEBUG << "Node " << nodeId << " cache hit for EID " << eid
                 << (isStale ? " (STALE)" : "") << endl;
        return;
    }

    emit(dnsCacheMissesSignal, 1L);

    // Store pending query
    PendingQuery pending;
    pending.queryId = queryId;
    pending.eid = eid;
    pending.clientId = nodeId;
    pending.requestingGate = -1;
    pending.queryTime = simTime();
    pending.hopCount = 0;
    pending.isLocalClient = true;
    pendingQueries[queryId] = pending;

    // Create query message
    DnsQuery *query = new DnsQuery("DnsQuery");
    query->setEid(eid);
    query->setQueryId(queryId);
    query->setClientId(nodeId);
    query->setHopCount(0);
    query->setQueryTime(simTime());
    query->setByteLength(query->getByteSize());

    // Send to resolver or authority
    int targetNode = -1;
    if (isResolver) {
        // We are a resolver, check authority directly
        targetNode = findAuthorityForEid(eid);
    } else if (resolverNodeId >= 0) {
        targetNode = resolverNodeId;
    } else {
        // No configured resolver, try to find one or go to authority directly
        targetNode = findAuthorityForEid(eid);
    }

    if (targetNode >= 0) {
        int gateIdx = findGateToNode(targetNode);
        if (gateIdx >= 0) {
            sendToGate(query, gateIdx);
            emit(dnsQueriesSentSignal, 1L);
            recordBytesSent(query->getByteLength());
            return;
        }
    }

    // Fallback: send to first neighbor
    if (!neighborGates.empty()) {
        sendToGate(query, neighborGates[0]);
        emit(dnsQueriesSentSignal, 1L);
        recordBytesSent(query->getByteLength());
    } else {
        EV_WARN << "Node " << nodeId << " cannot send query - no neighbors" << endl;
        delete query;
        pendingQueries.erase(queryId);
    }
}

void EidNode::handleDnsQuery(DnsQuery *msg, int arrivalGate)
{
    emit(dnsQueriesReceivedSignal, 1L);

    int eid = msg->getEid();
    int queryId = msg->getQueryId();

    EV_DEBUG << "Node " << nodeId << " received DNS query for EID " << eid
             << " (queryId=" << queryId << ")" << endl;

    // Check hierarchy depth
    if (msg->getHopCount() >= dnsMaxHierarchyDepth) {
        EV_WARN << "Node " << nodeId << " dropping query - max depth exceeded" << endl;
        return;
    }

    // If we are authority, check our database
    if (isAuthority) {
        auto it = dnsAuthorityDb.find(eid);
        if (it != dnsAuthorityDb.end()) {
            // Found - send authoritative response
            dnsSendResponse(queryId, eid, true, it->second.endpoint,
                           it->second.ttl, false, true,
                           it->second.lastChangedTime, arrivalGate);
            return;
        }

        // Not in our domain - if root, we could refer to appropriate authority
        if (isRoot) {
            // For simplicity, root knows all authorities
            // In a real implementation, this would do hierarchical lookup
        }

        // Not found
        EndpointInfo empty;
        dnsSendResponse(queryId, eid, false, empty, 0, false, true, simTime(), arrivalGate);
        return;
    }

    // If we are a resolver, check cache
    if (isResolver) {
        DnsCacheEntry *cached = dnsLookupCache(eid);
        if (cached && !cached->isExpired()) {
            emit(dnsCacheHitsSignal, 1L);
            dnsSendResponse(queryId, eid, true, cached->endpoint,
                           cached->ttl, true, cached->authoritative,
                           cached->recordTime, arrivalGate);
            return;
        }
        emit(dnsCacheMissesSignal, 1L);
    }

    // Forward query to authority
    PendingQuery pending;
    pending.queryId = queryId;
    pending.eid = eid;
    pending.clientId = msg->getClientId();
    pending.requestingGate = arrivalGate;
    pending.queryTime = msg->getQueryTime();
    pending.hopCount = msg->getHopCount() + 1;
    pending.isLocalClient = false;
    pendingQueries[queryId] = pending;

    int targetNode = findAuthorityForEid(eid);
    if (targetNode < 0) {
        targetNode = findRootServer();
    }

    if (targetNode >= 0) {
        dnsForwardQuery(msg, targetNode);
    } else {
        // Cannot resolve - send negative response
        EndpointInfo empty;
        dnsSendResponse(queryId, eid, false, empty, 0, false, false, simTime(), arrivalGate);
        pendingQueries.erase(queryId);
    }
}

void EidNode::handleDnsResponse(DnsResponse *msg)
{
    emit(dnsResponsesReceivedSignal, 1L);

    int queryId = msg->getQueryId();
    int eid = msg->getEid();

    EV_DEBUG << "Node " << nodeId << " received DNS response for EID " << eid
             << " found=" << msg->getFound() << endl;

    auto it = pendingQueries.find(queryId);
    if (it == pendingQueries.end()) {
        EV_DEBUG << "Node " << nodeId << " no pending query for ID " << queryId << endl;
        return;
    }

    PendingQuery pending = it->second;
    pendingQueries.erase(it);

    // Cache the response if we're a resolver
    if (isResolver && msg->getFound()) {
        dnsAddToCache(eid, msg->getEndpoint(), msg->getTtl(),
                      msg->getRecordTime(), msg->getAuthoritative());
    }

    // If this was our own query, record latency
    if (pending.isLocalClient) {
        simtime_t latency = simTime() - pending.queryTime;
        emit(dnsQueryLatencySignal, latency);
        emit(discoveryLatencySignal, latency);

        // Check correctness
        if (msg->getFound() && groundTruth) {
            bool isStale = !groundTruth->isRecordCurrent(eid, msg->getEndpoint(), msg->getRecordTime());
            if (isStale) {
                emit(staleAnswersSignal, 1L);
            } else {
                emit(correctAnswersSignal, 1L);
            }
        }
    } else {
        // Forward response back to requester
        DnsResponse *forward = msg->dup();
        forward->setHopCount(msg->getHopCount() + 1);
        sendToGate(forward, pending.requestingGate);
        emit(dnsResponsesSentSignal, 1L);
        recordBytesSent(forward->getByteLength());
    }
}

void EidNode::handleDnsRegister(DnsRegister *msg)
{
    if (!isAuthority) {
        return;
    }

    int eid = msg->getEid();
    EV_INFO << "Authority " << nodeId << " registering EID " << eid
            << " from publisher " << msg->getPublisherId() << endl;

    DnsAuthorityRecord record;
    record.eid = eid;
    record.publisherId = msg->getPublisherId();
    record.endpoint = msg->getEndpoint();
    record.ttl = msg->getTtl();
    record.version = msg->getVersion();
    record.lastChangedTime = simTime();

    dnsAuthorityDb[eid] = record;
    recordTableOperation();
}

void EidNode::handleDnsDeregister(DnsDeregister *msg)
{
    if (!isAuthority) {
        return;
    }

    int eid = msg->getEid();
    auto it = dnsAuthorityDb.find(eid);
    if (it != dnsAuthorityDb.end() && it->second.publisherId == msg->getPublisherId()) {
        EV_INFO << "Authority " << nodeId << " deregistering EID " << eid << endl;
        dnsAuthorityDb.erase(it);
        recordTableOperation();
    }
}

void EidNode::handleDnsReferral(DnsReferral *msg, int arrivalGate)
{
    // Handle referral by forwarding query to referred node
    int queryId = msg->getQueryId();
    auto it = pendingQueries.find(queryId);
    if (it == pendingQueries.end()) {
        return;
    }

    DnsQuery *query = new DnsQuery("DnsQuery");
    query->setEid(msg->getEid());
    query->setQueryId(queryId);
    query->setClientId(it->second.clientId);
    query->setHopCount(it->second.hopCount);
    query->setQueryTime(it->second.queryTime);
    query->setByteLength(query->getByteSize());

    dnsForwardQuery(query, msg->getReferToNodeId());
}

void EidNode::dnsForwardQuery(DnsQuery *msg, int targetNodeId)
{
    DnsQuery *forward = msg->dup();
    forward->setHopCount(msg->getHopCount() + 1);

    int gateIdx = findGateToNode(targetNodeId);
    if (gateIdx >= 0) {
        sendToGate(forward, gateIdx);
        emit(dnsQueriesSentSignal, 1L);
        recordBytesSent(forward->getByteLength());
    } else {
        // No direct path - send to first neighbor as fallback
        if (!neighborGates.empty()) {
            sendToGate(forward, neighborGates[0]);
            emit(dnsQueriesSentSignal, 1L);
            recordBytesSent(forward->getByteLength());
        } else {
            delete forward;
        }
    }
}

void EidNode::dnsSendResponse(int queryId, int eid, bool found,
                              const EndpointInfo& endpoint, int ttl,
                              bool cacheHit, bool authoritative,
                              simtime_t recordTime, int toGate)
{
    DnsResponse *response = new DnsResponse("DnsResponse");
    response->setEid(eid);
    response->setQueryId(queryId);
    response->setFound(found);
    response->setEndpoint(endpoint);
    response->setTtl(ttl);
    response->setCacheHit(cacheHit);
    response->setAuthoritative(authoritative);
    response->setRecordTime(recordTime);
    response->setHopCount(0);
    response->setByteLength(response->getByteSize());

    sendToGate(response, toGate);
    emit(dnsResponsesSentSignal, 1L);
    recordBytesSent(response->getByteLength());
}

void EidNode::dnsAddToCache(int eid, const EndpointInfo& endpoint, int ttl,
                            simtime_t recordTime, bool authoritative)
{
    // Evict if cache is full
    if ((int)dnsCache.size() >= dnsCacheSize) {
        dnsEvictCache();
    }

    DnsCacheEntry entry;
    entry.eid = eid;
    entry.endpoint = endpoint;
    entry.ttl = ttl;
    entry.expiryTime = simTime() + SimTime(ttl, SIMTIME_S);
    entry.recordTime = recordTime;
    entry.authoritative = authoritative;

    dnsCache[eid] = entry;
    recordTableOperation();
    emit(dnsCacheSizeSignal, (long)dnsCache.size());
}

DnsCacheEntry* EidNode::dnsLookupCache(int eid)
{
    auto it = dnsCache.find(eid);
    if (it != dnsCache.end()) {
        recordTableOperation();
        return &(it->second);
    }
    return nullptr;
}

void EidNode::dnsEvictCache()
{
    // Simple LRU-like eviction: remove expired entries first, then oldest
    simtime_t oldestTime = simTime();
    int oldestEid = -1;

    for (auto it = dnsCache.begin(); it != dnsCache.end(); ) {
        if (it->second.isExpired()) {
            it = dnsCache.erase(it);
            recordTableOperation();
        } else {
            if (it->second.expiryTime < oldestTime) {
                oldestTime = it->second.expiryTime;
                oldestEid = it->first;
            }
            ++it;
        }
    }

    // If still over capacity, remove oldest
    if ((int)dnsCache.size() >= dnsCacheSize && oldestEid >= 0) {
        dnsCache.erase(oldestEid);
        recordTableOperation();
    }

    emit(dnsCacheSizeSignal, (long)dnsCache.size());
}

int EidNode::findAuthorityForEid(int eid)
{
    // Simple authority assignment: EID mod number of authorities
    // In a real system, this would be based on EID namespace/prefix

    if (authorityNodeId >= 0) {
        return authorityNodeId;
    }

    // Look for authority among neighbors
    for (auto& pair : gateToNodeId) {
        cModule *mod = getParentModule()->getSubmodule("node", pair.second);
        if (!mod) mod = getParentModule()->getSubmodule("authority", pair.second);
        if (!mod) continue;

        EidNode *node = dynamic_cast<EidNode*>(mod);
        if (node && node->isAuthority) {
            return pair.second;
        }
    }

    return -1;
}

int EidNode::findResolverForNode()
{
    if (resolverNodeId >= 0) {
        return resolverNodeId;
    }

    // Look for resolver among neighbors
    for (auto& pair : gateToNodeId) {
        cModule *mod = getParentModule()->getSubmodule("node", pair.second);
        if (!mod) mod = getParentModule()->getSubmodule("resolver", pair.second);
        if (!mod) continue;

        EidNode *node = dynamic_cast<EidNode*>(mod);
        if (node && node->isResolver) {
            return pair.second;
        }
    }

    return -1;
}

int EidNode::findRootServer()
{
    // Look for root among neighbors
    for (auto& pair : gateToNodeId) {
        cModule *mod = getParentModule()->getSubmodule("root");
        if (mod) {
            EidNode *node = dynamic_cast<EidNode*>(mod);
            if (node) return node->getNodeId();
        }
    }
    return -1;
}

int EidNode::findGateToNode(int targetNodeId)
{
    // Direct neighbor?
    for (auto& pair : gateToNodeId) {
        if (pair.second == targetNodeId) {
            return pair.first;
        }
    }

    // For simplicity, return first neighbor as fallback
    // In a real implementation, this would use routing tables
    if (!neighborGates.empty()) {
        return neighborGates[0];
    }

    return -1;
}

// ============================================================================
// Timer Handlers
// ============================================================================

void EidNode::handlePublishTimer()
{
    static size_t publishIndex = 0;

    if (publishIndex < publishEids.size()) {
        int eid = publishEids[publishIndex];

        if (bgpEnabled) {
            bgpPublishEid(eid);
        }
        if (dnsEnabled) {
            dnsRegisterEid(eid);
        }

        publishIndex++;
    }

    // Schedule next publish
    if (publishInterval > 0 && publishIndex < publishEids.size()) {
        scheduleAt(simTime() + publishInterval, publishTimer);
    }
}

void EidNode::handleQueryTimer()
{
    if (queriesSent >= queryCount) {
        return;
    }

    int eid = selectQueryEid();
    if (eid >= 0) {
        if (dnsEnabled) {
            dnsQueryEid(eid);
        } else if (bgpEnabled) {
            // For BGP, "query" is checking if EID is in table
            auto it = bgpTable.find(eid);
            if (it != bgpTable.end()) {
                emit(correctAnswersSignal, 1L);
            }
        }
        queriesSent++;
    }

    // Schedule next query
    if (queriesSent < queryCount && queryInterval > 0) {
        scheduleAt(simTime() + queryInterval, queryTimer);
    }
}

void EidNode::handleChurnTimer()
{
    std::uniform_real_distribution<double> dist(0.0, 1.0);

    for (int eid : publishEids) {
        if (dist(rng) < churnProbability) {
            if (dist(rng) < withdrawProbability) {
                // Withdraw
                if (bgpEnabled) bgpWithdrawEid(eid);
                if (dnsEnabled) dnsDeregisterEid(eid);
            } else {
                // Update
                if (bgpEnabled) bgpUpdateEid(eid);
                if (dnsEnabled) dnsRegisterEid(eid);  // Re-register updates
            }
        }
    }

    // Schedule next churn event
    if (churnInterval > 0) {
        scheduleAt(simTime() + churnInterval, churnTimer);
    }
}

void EidNode::handleKeepaliveTimer()
{
    if (!bgpEnabled) return;

    BgpKeepalive *keepalive = new BgpKeepalive("BgpKeepalive");
    keepalive->setSenderId(nodeId);
    keepalive->setByteLength(keepalive->getByteSize());

    sendToAllNeighbors(keepalive);

    // Schedule next
    if (bgpKeepaliveInterval > 0) {
        scheduleAt(simTime() + bgpKeepaliveInterval, keepaliveTimer);
    }
}

// ============================================================================
// Utility Functions
// ============================================================================

void EidNode::sendToGate(cMessage *msg, int gateIndex)
{
    if (gateIndex >= 0 && gateIndex < gateSize("port")) {
        cGate *outGate = gate("port$o", gateIndex);
        if (outGate && outGate->isConnected()) {
            send(msg, outGate);
            return;
        }
    }
    EV_WARN << "Node " << nodeId << " cannot send to gate " << gateIndex << endl;
    delete msg;
}

void EidNode::sendToAllNeighbors(cMessage *msg, int excludeGate)
{
    bool sent = false;
    for (int gateIdx : neighborGates) {
        if (gateIdx != excludeGate) {
            cMessage *copy = sent ? msg->dup() : msg;
            sendToGate(copy, gateIdx);
            sent = true;
        }
    }
    if (!sent) {
        delete msg;
    }
}

void EidNode::recordTableOperation()
{
    tableOperationCount++;
    emit(tableOperationsSignal, tableOperationCount);
}

void EidNode::recordBytesSent(int bytes)
{
    emit(messageBytesSentSignal, (long)bytes);
}

void EidNode::recordBytesReceived(int bytes)
{
    emit(messageBytesReceivedSignal, (long)bytes);
}

int EidNode::selectQueryEid()
{
    if (queryEids.empty()) {
        // Query random EID from ground truth if available
        if (groundTruth) {
            return groundTruth->getRandomPublishedEid();
        }
        return -1;
    }

    if (queryZipfAlpha <= 0) {
        // Uniform distribution
        std::uniform_int_distribution<int> dist(0, queryEids.size() - 1);
        return queryEids[dist(rng)];
    }

    // Zipf distribution
    double sum = 0;
    for (size_t i = 1; i <= queryEids.size(); i++) {
        sum += 1.0 / std::pow(i, queryZipfAlpha);
    }

    std::uniform_real_distribution<double> dist(0.0, sum);
    double r = dist(rng);

    double cumulative = 0;
    for (size_t i = 0; i < queryEids.size(); i++) {
        cumulative += 1.0 / std::pow(i + 1, queryZipfAlpha);
        if (r <= cumulative) {
            return queryEids[i];
        }
    }

    return queryEids.back();
}

EndpointInfo EidNode::createEndpointInfo()
{
    EndpointInfo info;
    info.targetNodeId = nodeId;
    info.claProtocol = claProtocol.c_str();
    info.port = claPort;
    info.hint = "";
    return info;
}

std::vector<int> EidNode::parseIntList(const std::string& str)
{
    std::vector<int> result;
    if (str.empty()) return result;

    std::stringstream ss(str);
    std::string token;
    while (std::getline(ss, token, ',')) {
        // Trim whitespace
        size_t start = token.find_first_not_of(" \t");
        size_t end = token.find_last_not_of(" \t");
        if (start != std::string::npos && end != std::string::npos) {
            token = token.substr(start, end - start + 1);
            // Check for range notation (e.g., "1-10")
            size_t dash = token.find('-');
            if (dash != std::string::npos && dash > 0) {
                int rangeStart = std::stoi(token.substr(0, dash));
                int rangeEnd = std::stoi(token.substr(dash + 1));
                for (int i = rangeStart; i <= rangeEnd; i++) {
                    result.push_back(i);
                }
            } else {
                result.push_back(std::stoi(token));
            }
        }
    }
    return result;
}

std::string EidNode::intListToString(const std::vector<int>& list)
{
    std::stringstream ss;
    for (size_t i = 0; i < list.size(); i++) {
        if (i > 0) ss << ",";
        ss << list[i];
    }
    return ss.str();
}
