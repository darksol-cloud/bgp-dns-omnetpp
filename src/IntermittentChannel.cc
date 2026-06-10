//
// IntermittentChannel.cc - Delay channel with periodic contact windows
//

#include "IntermittentChannel.h"

#include <cmath>

Define_Channel(IntermittentChannel);

void IntermittentChannel::initialize()
{
    cDelayChannel::initialize();
    contactPeriod = par("contactPeriod").doubleValue();
    contactDuty = par("contactDuty").doubleValue();
    contactPhase = par("contactPhase").doubleValue();

    if (contactDuty <= 0 || contactDuty > 1)
        throw cRuntimeError("contactDuty must be in (0, 1], got %g", contactDuty);
}

double IntermittentChannel::timeToNextContact(double t, double period, double duty, double phase)
{
    if (period <= 0 || duty >= 1.0)
        return 0;

    double pos = std::fmod(t - phase, period);
    if (pos < 0)
        pos += period;

    double upLength = duty * period;
    return pos < upLength ? 0 : period - pos;
}

cChannel::Result IntermittentChannel::processMessage(cMessage *msg, const SendOptions& options, simtime_t t)
{
    Result result = cDelayChannel::processMessage(msg, options, t);

    double wait = timeToNextContact(t.dbl(), contactPeriod, contactDuty, contactPhase);
    if (wait > 0)
        result.delay += SimTime(wait);

    return result;
}
