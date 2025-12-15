// EidChannel.ned - Channel definitions for the simulation

package bgpdns;

// Basic delay channel - using DelayChannel for simplicity (no transmission time modeling)
// This is appropriate for control-plane simulation where we focus on propagation delay
channel EidChannel extends ned.DelayChannel
{
    parameters:
        delay = default(10ms);
        @display("ls=black,1");
}

// High-latency channel (e.g., satellite/space links)
channel HighLatencyChannel extends EidChannel
{
    parameters:
        delay = default(250ms);
}

// Lossy channel for disruption scenarios - uses IdealChannel with loss handled at module level
channel LossyChannel extends EidChannel
{
    parameters:
        delay = default(50ms);
        // Note: Loss is simulated at module level for DelayChannel
}

// Disruption-prone channel (for DTN scenarios)
channel DisruptionChannel extends EidChannel
{
    parameters:
        delay = default(100ms);
        // Disruption handled at module level
        @display("ls=red,1,dashed");
}
