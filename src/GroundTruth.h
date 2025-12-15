// GroundTruth.h - Ground truth and metrics collection module

#ifndef __BGPDNS_GROUNDTRUTH_H
#define __BGPDNS_GROUNDTRUTH_H

#include <omnetpp.h>
#include <map>
#include <set>
#include <vector>
#include <random>

#include "EidMessages_m.h"

using namespace omnetpp;

// Forward declaration
class EidNode;

// Ground truth record for an EID
struct GroundTruthRecord {
    int eid;
    int publisherId;
    EndpointInfo endpoint;
    simtime_t publishTime;
    simtime_t lastChangeTime;
    int version;
    bool isActive;
};

// Convergence tracking for an EID
struct ConvergenceState {
    int eid;
    simtime_t eventTime;         // When the publish/update occurred
    int expectedCorrectNodes;    // How many nodes should have correct info
    int currentCorrectNodes;     // How many currently have correct info
    bool converged;
    simtime_t convergenceTime;   // When convergence was achieved
};

class GroundTruth : public cSimpleModule
{
  protected:
    // Parameters
    double snapshotInterval;
    double convergenceCheckInterval;
    double convergenceThreshold;
    int totalNodes;
    int totalEids;
    bool verboseLogging;
    bool recordConvergenceEvents;
    bool recordAccuracySnapshots;

    // Ground truth database
    std::map<int, GroundTruthRecord> groundTruthDb;  // eid -> record

    // Convergence tracking
    std::map<int, ConvergenceState> convergenceStates;  // eid -> state

    // Statistics signals
    simsignal_t globalBgpMessagesSignal;
    simsignal_t globalDnsMessagesSignal;
    simsignal_t globalBgpBytesSignal;
    simsignal_t globalDnsBytesSignal;
    simsignal_t globalConvergenceTimeSignal;
    simsignal_t globalAccuracySignal;
    simsignal_t globalCoverageSignal;
    simsignal_t globalStaleRateSignal;
    simsignal_t avgBgpTableSizeSignal;
    simsignal_t avgDnsCacheSizeSignal;
    simsignal_t totalTableOperationsSignal;

    // Self-messages
    cMessage *snapshotTimer;
    cMessage *convergenceTimer;

    // Node references (cached)
    std::vector<EidNode*> nodes;

    // Random generator
    std::mt19937 rng;

    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
    virtual void finish() override;

    void collectNodes();
    void takeSnapshot();
    void checkConvergence();

    // Compute metrics
    double computeBgpAccuracy(int eid);
    double computeBgpCoverage(int eid);
    double computeDnsStaleRate();
    void computeAggregateMetrics();

  public:
    GroundTruth() : snapshotTimer(nullptr), convergenceTimer(nullptr) {}
    virtual ~GroundTruth();

    // Called by EidNode to update ground truth
    void recordEidPublish(int eid, int publisherId, const EndpointInfo& endpoint, simtime_t time);
    void recordEidWithdraw(int eid, int publisherId, simtime_t time);
    void recordEidUpdate(int eid, int publisherId, const EndpointInfo& endpoint, simtime_t time);

    // Called by EidNode to check correctness
    bool isRecordCurrent(int eid, const EndpointInfo& endpoint, simtime_t recordTime);
    bool isEidActive(int eid);
    const GroundTruthRecord* getGroundTruth(int eid);

    // For random query generation
    int getRandomPublishedEid();
    std::vector<int> getAllPublishedEids();
};

#endif // __BGPDNS_GROUNDTRUTH_H
