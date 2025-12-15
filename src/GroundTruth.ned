// GroundTruth.ned - Central ground truth and metrics collection module

package bgpdns;

simple GroundTruth
{
    parameters:
        // Metrics collection parameters
        double snapshotInterval @unit(s) = default(1s);     // How often to collect metrics
        double convergenceCheckInterval @unit(s) = default(0.1s);  // How often to check convergence
        double convergenceThreshold = default(0.99);        // Fraction of nodes needed for "converged"

        // Experiment parameters
        int totalNodes;                                      // Total nodes in network
        int totalEids = default(0);                         // Total EIDs (0 = count dynamically)

        // Output control
        bool verboseLogging = default(false);
        bool recordConvergenceEvents = default(true);
        bool recordAccuracySnapshots = default(true);

        // Statistics signals
        @signal[globalBgpMessages](type=long);
        @signal[globalDnsMessages](type=long);
        @signal[globalBgpBytes](type=long);
        @signal[globalDnsBytes](type=long);
        @signal[globalConvergenceTime](type=simtime_t);
        @signal[globalAccuracy](type=double);
        @signal[globalCoverage](type=double);
        @signal[globalStaleRate](type=double);
        @signal[avgBgpTableSize](type=double);
        @signal[avgDnsCacheSize](type=double);
        @signal[totalTableOperations](type=long);

        @statistic[globalBgpMessages](record=last,sum,vector);
        @statistic[globalDnsMessages](record=last,sum,vector);
        @statistic[globalBgpBytes](record=last,sum,vector);
        @statistic[globalDnsBytes](record=last,sum,vector);
        @statistic[globalConvergenceTime](record=mean,max,histogram,vector);
        @statistic[globalAccuracy](record=mean,min,timeavg,vector);
        @statistic[globalCoverage](record=mean,min,timeavg,vector);
        @statistic[globalStaleRate](record=mean,max,timeavg,vector);
        @statistic[avgBgpTableSize](record=mean,max,timeavg,vector);
        @statistic[avgDnsCacheSize](record=mean,max,timeavg,vector);
        @statistic[totalTableOperations](record=last,sum,vector);

        @display("i=block/table2");
}
