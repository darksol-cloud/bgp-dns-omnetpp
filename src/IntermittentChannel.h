//
// IntermittentChannel.h - Delay channel with periodic contact windows
//
// Models a scheduled DTN link: the channel alternates between "up" windows
// (fraction contactDuty of each contactPeriod) and "down" windows. Messages
// submitted during a down window are held until the start of the next up
// window (store-and-forward semantics), then experience the propagation delay.
// With contactPeriod = 0 or contactDuty = 1 the channel behaves exactly like
// a plain DelayChannel, so existing experiments are unaffected.
//

#ifndef __BGPDNS_INTERMITTENTCHANNEL_H
#define __BGPDNS_INTERMITTENTCHANNEL_H

#include <omnetpp.h>

using namespace omnetpp;

class IntermittentChannel : public cDelayChannel
{
  protected:
    double contactPeriod = 0;   // seconds; 0 disables intermittency
    double contactDuty = 1.0;   // fraction of period the link is up
    double contactPhase = 0;    // seconds; up window starts at phase within each period

    virtual void initialize() override;
    virtual Result processMessage(cMessage *msg, const SendOptions& options, simtime_t t) override;

  public:
    // Wait time from t until the link is next up (0 if currently up)
    static double timeToNextContact(double t, double period, double duty, double phase);
};

#endif
