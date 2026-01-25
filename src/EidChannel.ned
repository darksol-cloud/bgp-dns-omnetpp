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

// ============================================================================
// Realistic Space Network Channels
// ============================================================================

// Terrestrial wireless channel (disaster response, mobile networks)
channel TerrestrialWirelessChannel extends EidChannel
{
    parameters:
        delay = default(20ms);
        @display("ls=green,1");
}

// Short-range radio channel (drones, EVA suits, local sensors)
channel ShortRangeChannel extends EidChannel
{
    parameters:
        delay = default(5ms);
        @display("ls=blue,1");
}

// Earth-Moon channel (~1.3 seconds one-way light delay)
channel LunarChannel extends EidChannel
{
    parameters:
        delay = default(1.3s);
        @display("ls=purple,2");
}

// Lunar orbital relay channel (Gateway to surface, includes processing)
channel LunarOrbitalChannel extends EidChannel
{
    parameters:
        delay = default(250ms);
        @display("ls=purple,1");
}

// Lunar surface channel (base to rover, line-of-sight)
channel LunarSurfaceChannel extends EidChannel
{
    parameters:
        delay = default(10ms);
        @display("ls=gray,1");
}

// Earth-Mars channel (~12 minutes average one-way, varies 3-22 min)
channel MarsInterplanetaryChannel extends EidChannel
{
    parameters:
        delay = default(720s);  // 12 minutes
        @display("ls=red,3");
}

// Mars orbital relay channel (MRO to surface)
channel MarsOrbitalChannel extends EidChannel
{
    parameters:
        delay = default(60s);  // Includes orbital pass timing and processing
        @display("ls=orange,2");
}

// Mars surface channel (habitat to rover, terrain/distance delays)
channel MarsSurfaceChannel extends EidChannel
{
    parameters:
        delay = default(5s);
        @display("ls=orange,1");
}

// Mars local channel (rover to instrument, short range)
channel MarsLocalChannel extends EidChannel
{
    parameters:
        delay = default(1s);
        @display("ls=yellow,1");
}
