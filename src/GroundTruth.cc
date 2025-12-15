// GroundTruth.cc - Ground truth and metrics collection implementation

#include "GroundTruth.h"
#include "EidNode.h"
#include <algorithm>

Define_Module(GroundTruth);

GroundTruth::~GroundTruth()
{
    cancelAndDelete(snapshotTimer);
    cancelAndDelete(convergenceTimer);
}

void GroundTruth::initialize()
{
    // Parse parameters
    snapshotInterval = par("snapshotInterval").doubleValue();
    convergenceCheckInterval = par("convergenceCheckInterval").doubleValue();
    convergenceThreshold = par("convergenceThreshold").doubleValue();
    totalNodes = par("totalNodes").intValue();
    totalEids = par("totalEids").intValue();
    verboseLogging = par("verboseLogging").boolValue();
    recordConvergenceEvents = par("recordConvergenceEvents").boolValue();
    recordAccuracySnapshots = par("recordAccuracySnapshots").boolValue();

    // Register signals
    globalBgpMessagesSignal = registerSignal("globalBgpMessages");
    globalDnsMessagesSignal = registerSignal("globalDnsMessages");
    globalBgpBytesSignal = registerSignal("globalBgpBytes");
    globalDnsBytesSignal = registerSignal("globalDnsBytes");
    globalConvergenceTimeSignal = registerSignal("globalConvergenceTime");
    globalAccuracySignal = registerSignal("globalAccuracy");
    globalCoverageSignal = registerSignal("globalCoverage");
    globalStaleRateSignal = registerSignal("globalStaleRate");
    avgBgpTableSizeSignal = registerSignal("avgBgpTableSize");
    avgDnsCacheSizeSignal = registerSignal("avgDnsCacheSize");
    totalTableOperationsSignal = registerSignal("totalTableOperations");

    // Initialize RNG
    rng.seed(42);

    // Collect node references after network is initialized
    scheduleAt(simTime() + 0.001, new cMessage("collectNodes"));

    // Schedule periodic snapshots
    if (snapshotInterval > 0) {
        snapshotTimer = new cMessage("snapshotTimer");
        scheduleAt(simTime() + snapshotInterval, snapshotTimer);
    }

    // Schedule convergence checks
    if (convergenceCheckInterval > 0) {
        convergenceTimer = new cMessage("convergenceTimer");
        scheduleAt(simTime() + convergenceCheckInterval, convergenceTimer);
    }

    EV_INFO << "GroundTruth initialized for " << totalNodes << " nodes" << endl;
}

void GroundTruth::handleMessage(cMessage *msg)
{
    if (strcmp(msg->getName(), "collectNodes") == 0) {
        collectNodes();
        delete msg;
        return;
    }

    if (msg == snapshotTimer) {
        takeSnapshot();
        scheduleAt(simTime() + snapshotInterval, snapshotTimer);
        return;
    }

    if (msg == convergenceTimer) {
        checkConvergence();
        scheduleAt(simTime() + convergenceCheckInterval, convergenceTimer);
        return;
    }

    delete msg;
}

void GroundTruth::collectNodes()
{
    nodes.clear();
    cModule *network = getParentModule();

    // Try different submodule naming patterns
    std::vector<std::string> patterns = {"node", "hub", "spoke", "clusterA", "clusterB",
                                          "gateway", "root", "resolver", "authority", "domainNode"};

    for (const std::string& pattern : patterns) {
        // Try indexed modules
        for (int i = 0; i < 10000; i++) {
            cModule *mod = network->getSubmodule(pattern.c_str(), i);
            if (!mod) break;

            EidNode *node = dynamic_cast<EidNode*>(mod);
            if (node) {
                nodes.push_back(node);
            }
        }

        // Try single module
        cModule *mod = network->getSubmodule(pattern.c_str());
        if (mod) {
            EidNode *node = dynamic_cast<EidNode*>(mod);
            if (node) {
                // Check if not already added
                if (std::find(nodes.begin(), nodes.end(), node) == nodes.end()) {
                    nodes.push_back(node);
                }
            }
        }
    }

    EV_INFO << "GroundTruth collected " << nodes.size() << " nodes" << endl;
    totalNodes = nodes.size();
}

void GroundTruth::recordEidPublish(int eid, int publisherId, const EndpointInfo& endpoint, simtime_t time)
{
    GroundTruthRecord record;
    record.eid = eid;
    record.publisherId = publisherId;
    record.endpoint = endpoint;
    record.publishTime = time;
    record.lastChangeTime = time;
    record.isActive = true;

    auto it = groundTruthDb.find(eid);
    if (it != groundTruthDb.end()) {
        record.version = it->second.version + 1;
    } else {
        record.version = 1;
    }

    groundTruthDb[eid] = record;

    // Initialize convergence tracking
    ConvergenceState state;
    state.eid = eid;
    state.eventTime = time;
    state.expectedCorrectNodes = totalNodes;
    state.currentCorrectNodes = 1;  // Publisher has it
    state.converged = false;
    state.convergenceTime = SIMTIME_ZERO;
    convergenceStates[eid] = state;

    if (verboseLogging) {
        EV_INFO << "GroundTruth: EID " << eid << " published by node " << publisherId
                << " at " << time << " (version " << record.version << ")" << endl;
    }
}

void GroundTruth::recordEidWithdraw(int eid, int publisherId, simtime_t time)
{
    auto it = groundTruthDb.find(eid);
    if (it != groundTruthDb.end() && it->second.publisherId == publisherId) {
        it->second.isActive = false;
        it->second.lastChangeTime = time;
        it->second.version++;

        // Update convergence state
        ConvergenceState state;
        state.eid = eid;
        state.eventTime = time;
        state.expectedCorrectNodes = totalNodes;
        state.currentCorrectNodes = 0;
        state.converged = false;
        state.convergenceTime = SIMTIME_ZERO;
        convergenceStates[eid] = state;

        if (verboseLogging) {
            EV_INFO << "GroundTruth: EID " << eid << " withdrawn by node " << publisherId
                    << " at " << time << endl;
        }
    }
}

void GroundTruth::recordEidUpdate(int eid, int publisherId, const EndpointInfo& endpoint, simtime_t time)
{
    // Update is same as publish with version increment
    recordEidPublish(eid, publisherId, endpoint, time);
}

bool GroundTruth::isRecordCurrent(int eid, const EndpointInfo& endpoint, simtime_t recordTime)
{
    auto it = groundTruthDb.find(eid);
    if (it == groundTruthDb.end()) {
        return false;  // EID doesn't exist
    }

    const GroundTruthRecord& gt = it->second;

    // Check if the record is from before the last change
    if (recordTime < gt.lastChangeTime) {
        return false;  // Stale
    }

    // Check if endpoint matches
    if (endpoint.targetNodeId != gt.endpoint.targetNodeId) {
        return false;  // Wrong endpoint
    }

    // Check if EID is still active
    if (!gt.isActive) {
        return false;  // EID was withdrawn
    }

    return true;
}

bool GroundTruth::isEidActive(int eid)
{
    auto it = groundTruthDb.find(eid);
    return (it != groundTruthDb.end() && it->second.isActive);
}

const GroundTruthRecord* GroundTruth::getGroundTruth(int eid)
{
    auto it = groundTruthDb.find(eid);
    if (it != groundTruthDb.end()) {
        return &(it->second);
    }
    return nullptr;
}

int GroundTruth::getRandomPublishedEid()
{
    std::vector<int> activeEids;
    for (auto& pair : groundTruthDb) {
        if (pair.second.isActive) {
            activeEids.push_back(pair.first);
        }
    }

    if (activeEids.empty()) {
        return -1;
    }

    std::uniform_int_distribution<size_t> dist(0, activeEids.size() - 1);
    return activeEids[dist(rng)];
}

std::vector<int> GroundTruth::getAllPublishedEids()
{
    std::vector<int> eids;
    for (auto& pair : groundTruthDb) {
        if (pair.second.isActive) {
            eids.push_back(pair.first);
        }
    }
    return eids;
}

void GroundTruth::takeSnapshot()
{
    if (nodes.empty()) return;

    computeAggregateMetrics();
}

void GroundTruth::checkConvergence()
{
    if (nodes.empty()) return;

    for (auto& pair : convergenceStates) {
        if (pair.second.converged) continue;

        int eid = pair.first;
        ConvergenceState& state = pair.second;

        const GroundTruthRecord* gt = getGroundTruth(eid);
        if (!gt) continue;

        int correctCount = 0;

        for (EidNode* node : nodes) {
            if (!node->isBgpEnabled()) continue;

            const auto& bgpTable = node->getBgpTable();
            auto it = bgpTable.find(eid);

            if (gt->isActive) {
                // EID should be present with correct endpoint
                if (it != bgpTable.end() &&
                    it->second.endpoint.targetNodeId == gt->endpoint.targetNodeId) {
                    correctCount++;
                }
            } else {
                // EID should be absent
                if (it == bgpTable.end()) {
                    correctCount++;
                }
            }
        }

        state.currentCorrectNodes = correctCount;

        // Check if converged
        double fraction = (double)correctCount / totalNodes;
        if (fraction >= convergenceThreshold && !state.converged) {
            state.converged = true;
            state.convergenceTime = simTime();

            simtime_t convergenceLatency = simTime() - state.eventTime;
            emit(globalConvergenceTimeSignal, convergenceLatency);

            if (verboseLogging || recordConvergenceEvents) {
                EV_INFO << "GroundTruth: EID " << eid << " converged at " << simTime()
                        << " (latency=" << convergenceLatency << "s, "
                        << correctCount << "/" << totalNodes << " nodes)" << endl;
            }
        }
    }
}

double GroundTruth::computeBgpAccuracy(int eid)
{
    const GroundTruthRecord* gt = getGroundTruth(eid);
    if (!gt) return 0.0;

    int correctCount = 0;
    int bgpNodeCount = 0;

    for (EidNode* node : nodes) {
        if (!node->isBgpEnabled()) continue;
        bgpNodeCount++;

        const auto& bgpTable = node->getBgpTable();
        auto it = bgpTable.find(eid);

        if (gt->isActive) {
            if (it != bgpTable.end() &&
                it->second.endpoint.targetNodeId == gt->endpoint.targetNodeId) {
                correctCount++;
            }
        } else {
            if (it == bgpTable.end()) {
                correctCount++;
            }
        }
    }

    return bgpNodeCount > 0 ? (double)correctCount / bgpNodeCount : 0.0;
}

double GroundTruth::computeBgpCoverage(int eid)
{
    if (!isEidActive(eid)) return 0.0;

    int coverageCount = 0;
    int bgpNodeCount = 0;

    for (EidNode* node : nodes) {
        if (!node->isBgpEnabled()) continue;
        bgpNodeCount++;

        const auto& bgpTable = node->getBgpTable();
        if (bgpTable.find(eid) != bgpTable.end()) {
            coverageCount++;
        }
    }

    return bgpNodeCount > 0 ? (double)coverageCount / bgpNodeCount : 0.0;
}

double GroundTruth::computeDnsStaleRate()
{
    int staleCount = 0;
    int totalCacheEntries = 0;

    for (EidNode* node : nodes) {
        if (!node->isDnsEnabled()) continue;

        const auto& cache = node->getDnsCache();
        for (auto& pair : cache) {
            totalCacheEntries++;

            const GroundTruthRecord* gt = getGroundTruth(pair.first);
            if (!gt) {
                staleCount++;  // EID no longer exists
                continue;
            }

            if (!gt->isActive) {
                staleCount++;  // EID was withdrawn
                continue;
            }

            if (pair.second.recordTime < gt->lastChangeTime) {
                staleCount++;  // Cache entry is from before last change
            }
        }
    }

    return totalCacheEntries > 0 ? (double)staleCount / totalCacheEntries : 0.0;
}

void GroundTruth::computeAggregateMetrics()
{
    // Compute average BGP table size
    double totalBgpSize = 0;
    int bgpNodeCount = 0;
    for (EidNode* node : nodes) {
        if (node->isBgpEnabled()) {
            totalBgpSize += node->getBgpTable().size();
            bgpNodeCount++;
        }
    }
    if (bgpNodeCount > 0) {
        emit(avgBgpTableSizeSignal, totalBgpSize / bgpNodeCount);
    }

    // Compute average DNS cache size
    double totalDnsSize = 0;
    int dnsNodeCount = 0;
    for (EidNode* node : nodes) {
        if (node->isDnsEnabled()) {
            totalDnsSize += node->getDnsCache().size();
            dnsNodeCount++;
        }
    }
    if (dnsNodeCount > 0) {
        emit(avgDnsCacheSizeSignal, totalDnsSize / dnsNodeCount);
    }

    // Compute total table operations
    long totalOps = 0;
    for (EidNode* node : nodes) {
        totalOps += node->getTableOperationCount();
    }
    emit(totalTableOperationsSignal, totalOps);

    // Compute overall accuracy
    if (!groundTruthDb.empty()) {
        double totalAccuracy = 0;
        int eidCount = 0;
        for (auto& pair : groundTruthDb) {
            totalAccuracy += computeBgpAccuracy(pair.first);
            eidCount++;
        }
        if (eidCount > 0) {
            emit(globalAccuracySignal, totalAccuracy / eidCount);
        }
    }

    // Compute overall coverage
    if (!groundTruthDb.empty()) {
        double totalCoverage = 0;
        int activeCount = 0;
        for (auto& pair : groundTruthDb) {
            if (pair.second.isActive) {
                totalCoverage += computeBgpCoverage(pair.first);
                activeCount++;
            }
        }
        if (activeCount > 0) {
            emit(globalCoverageSignal, totalCoverage / activeCount);
        }
    }

    // Compute stale rate
    emit(globalStaleRateSignal, computeDnsStaleRate());

    if (verboseLogging) {
        EV_INFO << "GroundTruth snapshot at " << simTime()
                << ": avgBgpTable=" << (bgpNodeCount > 0 ? totalBgpSize/bgpNodeCount : 0)
                << ", avgDnsCache=" << (dnsNodeCount > 0 ? totalDnsSize/dnsNodeCount : 0)
                << ", totalOps=" << totalOps << endl;
    }
}

void GroundTruth::finish()
{
    // Record final metrics
    computeAggregateMetrics();

    // Record summary statistics
    recordScalar("totalEidsPublished", groundTruthDb.size());

    int activeEids = 0;
    for (auto& pair : groundTruthDb) {
        if (pair.second.isActive) activeEids++;
    }
    recordScalar("activeEids", activeEids);

    int convergedEids = 0;
    simtime_t totalConvergenceTime = SIMTIME_ZERO;
    for (auto& pair : convergenceStates) {
        if (pair.second.converged) {
            convergedEids++;
            totalConvergenceTime += (pair.second.convergenceTime - pair.second.eventTime);
        }
    }
    recordScalar("convergedEids", convergedEids);
    if (convergedEids > 0) {
        recordScalar("avgConvergenceTime", totalConvergenceTime.dbl() / convergedEids);
    }

    // Per-node final statistics
    long totalBgpTableSize = 0;
    long totalDnsCacheSize = 0;
    long totalDnsAuthoritySize = 0;
    long totalTableOps = 0;

    for (EidNode* node : nodes) {
        if (node->isBgpEnabled()) {
            totalBgpTableSize += node->getBgpTable().size();
        }
        if (node->isDnsEnabled()) {
            totalDnsCacheSize += node->getDnsCache().size();
            totalDnsAuthoritySize += node->getDnsAuthorityDb().size();
        }
        totalTableOps += node->getTableOperationCount();
    }

    recordScalar("totalBgpTableSize", totalBgpTableSize);
    recordScalar("totalDnsCacheSize", totalDnsCacheSize);
    recordScalar("totalDnsAuthoritySize", totalDnsAuthoritySize);
    recordScalar("totalTableOperations", totalTableOps);
}
