#!/bin/bash
# run_experiments.sh - Execute BGP vs DNS comparison experiments 1-10
#
# Usage: ./run_experiments.sh [experiment_number]
#   No argument: runs all experiments 1-10
#   With number: runs only that experiment (e.g., ./run_experiments.sh 1)
#   "deepspace": runs only deep-space experiments (8-10)
#   "export": exports results to CSV only

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SIM_BINARY="$PROJECT_DIR/out/clang-release/bgp-dns"
RESULTS_DIR="$SCRIPT_DIR/results"
NED_PATH="$PROJECT_DIR/src"
INI_FILE="$SCRIPT_DIR/experiments.ini"

# Source OMNeT++ environment
source "$PROJECT_DIR/../../setenv"

# Create results directory if needed
mkdir -p "$RESULTS_DIR"

# Define experiments
declare -a EXP1=("Exp1_Baseline_Bgp" "Exp1_Baseline_Dns")
declare -a EXP2=("Exp2_Scale_Bgp_5x5" "Exp2_Scale_Bgp_10x10" "Exp2_Scale_Bgp_15x15" "Exp2_Scale_Bgp_20x20" "Exp2_Scale_Dns_5x5" "Exp2_Scale_Dns_10x10" "Exp2_Scale_Dns_15x15" "Exp2_Scale_Dns_20x20")
declare -a EXP3=("Exp3_Eids_Bgp" "Exp3_Eids_Dns")
declare -a EXP4=("Exp4_Latency_Bgp" "Exp4_Latency_Dns")
declare -a EXP5=("Exp5_Churn_Bgp" "Exp5_Churn_Dns")
declare -a EXP6=("Exp6_Stale_Bgp" "Exp6_Stale_Dns")
declare -a EXP7=("Exp7_QueryPattern_Dns")
declare -a EXP8=("Exp8_DeepSpace_Bgp" "Exp8_DeepSpace_Dns")
declare -a EXP9=("Exp9_DeepSpace_DnsCache" "Exp9_DeepSpace_DnsNoCache")
declare -a EXP10=("Exp10_DeepSpace_Churn_Bgp" "Exp10_DeepSpace_Churn_Dns")

run_config() {
    local config=$1
    echo "========================================"
    echo "Running: $config"
    echo "========================================"
    "$SIM_BINARY" -u Cmdenv -c "$config" -n "$NED_PATH" -f "$INI_FILE" --result-dir="$RESULTS_DIR"
    echo "Completed: $config"
    echo ""
}

run_experiment() {
    local exp_num=$1

    echo "########################################"
    echo "# EXPERIMENT $exp_num"
    echo "########################################"
    echo ""

    case $exp_num in
        1) for config in "${EXP1[@]}"; do run_config "$config"; done ;;
        2) for config in "${EXP2[@]}"; do run_config "$config"; done ;;
        3) for config in "${EXP3[@]}"; do run_config "$config"; done ;;
        4) for config in "${EXP4[@]}"; do run_config "$config"; done ;;
        5) for config in "${EXP5[@]}"; do run_config "$config"; done ;;
        6) for config in "${EXP6[@]}"; do run_config "$config"; done ;;
        7) for config in "${EXP7[@]}"; do run_config "$config"; done ;;
        8) for config in "${EXP8[@]}"; do run_config "$config"; done ;;
        9) for config in "${EXP9[@]}"; do run_config "$config"; done ;;
        10) for config in "${EXP10[@]}"; do run_config "$config"; done ;;
    esac
}

export_results() {
    echo "========================================"
    echo "Exporting results to CSV"
    echo "========================================"

    local timestamp=$(date +%Y%m%d_%H%M%S)
    local output_file="$RESULTS_DIR/experiments_${timestamp}.csv"

    # Export all scalars from experiment results
    # Find result files (exclude .vci index files)
    local result_files=$(find "$RESULTS_DIR" -maxdepth 1 -type f -name 'Exp*' ! -name '*.vci' ! -name '*.csv' | sort)

    if [ -z "$result_files" ]; then
        echo "No result files found in $RESULTS_DIR"
        return 1
    fi

    opp_scavetool export \
        -o "$output_file" \
        -F CSV-S \
        -T s \
        $result_files

    echo "Results exported to: $output_file"

    # Also create a "latest" symlink
    ln -sf "experiments_${timestamp}.csv" "$RESULTS_DIR/experiments_latest.csv"
    echo "Symlink created: $RESULTS_DIR/experiments_latest.csv"
}

# Main logic
if [ ! -f "$SIM_BINARY" ]; then
    echo "Error: Simulation binary not found at $SIM_BINARY"
    echo "Please build the project first: cd $PROJECT_DIR && make"
    exit 1
fi

if [ $# -eq 0 ]; then
    # Run all experiments 1-10
    echo "Running all experiments (1-10)..."
    echo ""

    for i in 1 2 3 4 5 6 7 8 9 10; do
        run_experiment $i
    done

    export_results

    echo ""
    echo "========================================"
    echo "ALL EXPERIMENTS COMPLETED"
    echo "========================================"

elif [ "$1" == "export" ]; then
    # Export only
    export_results

elif [ "$1" == "deepspace" ]; then
    # Run only deep-space experiments (8-10)
    echo "Running deep-space experiments (8-10)..."
    echo ""

    for i in 8 9 10; do
        run_experiment $i
    done

    export_results

    echo ""
    echo "========================================"
    echo "DEEP-SPACE EXPERIMENTS COMPLETED"
    echo "========================================"

else
    # Run specific experiment
    exp_num=$1
    if [[ ! "$exp_num" =~ ^([1-9]|10)$ ]]; then
        echo "Error: Invalid experiment number. Use 1-10, 'deepspace', or 'export'"
        exit 1
    fi

    run_experiment $exp_num
    export_results
fi
