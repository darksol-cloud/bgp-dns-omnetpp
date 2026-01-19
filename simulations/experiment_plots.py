#!/usr/bin/env python3
"""
experiment_plots.py - Analyze and visualize BGP vs DNS comparison experiments

Usage:
    python experiment_plots.py [results/experiments_latest.csv]

Generates tables and plots for experiments 1-5 as defined in PLAN.md
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys
import os
import re
from pathlib import Path

# Style configuration
plt.style.use('seaborn-v0_8-whitegrid')
COLORS = {'BGP': '#2E86AB', 'DNS': '#A23B72'}
FIGSIZE = (10, 6)
DPI = 150


def load_data(csv_path):
    """Load and preprocess the experiment results CSV."""
    df = pd.read_csv(csv_path)

    # Extract experiment info from run column
    df['experiment'] = df['run'].apply(lambda x: re.match(r'(Exp\d+_[^-]+)', x).group(1) if re.match(r'(Exp\d+_[^-]+)', x) else x)
    df['protocol'] = df['experiment'].apply(lambda x: 'BGP' if 'Bgp' in x else 'DNS')
    df['exp_num'] = df['experiment'].apply(lambda x: int(re.search(r'Exp(\d+)', x).group(1)) if re.search(r'Exp(\d+)', x) else 0)

    # Extract grid size for Exp2
    df['grid_size'] = df['experiment'].apply(lambda x: re.search(r'(\d+x\d+)', x).group(1) if re.search(r'(\d+x\d+)', x) else None)
    df['num_nodes'] = df['grid_size'].apply(lambda x: int(x.split('x')[0])**2 if x else None)

    # Clean M column (EID range) for Exp3 - handle triple quotes
    df['M_clean'] = df['M'].apply(lambda x: str(x).strip('"').strip() if pd.notna(x) else None)
    df['num_eids'] = df['M_clean'].apply(lambda x: int(x.split('-')[1]) if x and '-' in str(x) and x != 'nan' else None)

    # Clean churnInt for Exp5
    df['churn_interval'] = pd.to_numeric(df['churnInt'], errors='coerce')

    return df


def get_metric(df, module_pattern, metric_name):
    """Extract a specific metric from the dataframe."""
    mask = df['module'].str.contains(module_pattern, regex=True) & (df['name'] == metric_name)
    return df[mask]['value'].astype(float)


def aggregate_by_experiment(df, exp_filter, metric_name, module='groundTruth', groupby=None):
    """Aggregate metrics by experiment and optional groupby column."""
    mask = (df['experiment'].str.contains(exp_filter)) & \
           (df['module'].str.contains(module)) & \
           (df['name'] == metric_name)

    subset = df[mask].copy()
    subset['value'] = pd.to_numeric(subset['value'], errors='coerce')

    if groupby and groupby in subset.columns:
        return subset.groupby(['protocol', groupby])['value'].agg(['mean', 'std', 'count']).reset_index()
    else:
        return subset.groupby('protocol')['value'].agg(['mean', 'std', 'count']).reset_index()


def print_table(title, data, columns=None):
    """Print a formatted table."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print('='*60)
    if isinstance(data, pd.DataFrame):
        print(data.to_string(index=False))
    else:
        print(data)
    print()


# =============================================================================
# EXPERIMENT 1: BASELINE OVERHEAD
# =============================================================================

def analyze_exp1(df, output_dir):
    """Analyze Experiment 1: Baseline Overhead Comparison."""
    print("\n" + "="*70)
    print(" EXPERIMENT 1: BASELINE OVERHEAD")
    print("="*70)

    exp1 = df[df['exp_num'] == 1].copy()

    # Aggregate node-level metrics per run
    results = []
    for protocol in ['BGP', 'DNS']:
        prot_data = exp1[exp1['protocol'] == protocol]
        runs = prot_data['run'].unique()

        total_bytes_list = []
        total_msgs_list = []
        table_size_list = []

        for run in runs:
            run_data = prot_data[prot_data['run'] == run]

            # Total bytes sent across all nodes
            bytes_mask = (run_data['module'].str.contains('node')) & \
                         (run_data['name'] == 'messageBytesSent:sum')
            total_bytes = pd.to_numeric(run_data[bytes_mask]['value'], errors='coerce').sum()
            total_bytes_list.append(total_bytes)

            # Total messages: BGP announces or DNS queries+responses
            if protocol == 'BGP':
                msg_mask = (run_data['module'].str.contains('node')) & \
                           (run_data['name'] == 'bgpAnnouncesSent:sum')
            else:
                msg_mask = (run_data['module'].str.contains('node')) & \
                           (run_data['name'].isin(['dnsQueriesSent:sum', 'dnsResponsesSent:sum']))
            total_msgs = pd.to_numeric(run_data[msg_mask]['value'], errors='coerce').sum()
            total_msgs_list.append(total_msgs)

            # State size from groundTruth
            if protocol == 'BGP':
                size_mask = (run_data['module'].str.contains('groundTruth')) & \
                            (run_data['name'] == 'totalBgpTableSize')
            else:
                # For DNS, count authority records + cache
                size_mask = (run_data['module'].str.contains('groundTruth')) & \
                            (run_data['name'].isin(['totalDnsCacheSize', 'totalDnsAuthoritySize']))
            table_size = pd.to_numeric(run_data[size_mask]['value'], errors='coerce').sum()
            table_size_list.append(table_size)

        results.append({
            'Protocol': protocol,
            'Total Bytes (mean)': np.mean(total_bytes_list),
            'Total Bytes (std)': np.std(total_bytes_list),
            'Total Messages (mean)': np.mean(total_msgs_list),
            'Total Messages (std)': np.std(total_msgs_list),
            'State Size (mean)': np.mean(table_size_list),
            'State Size (std)': np.std(table_size_list),
        })

    results_df = pd.DataFrame(results)
    print_table("Baseline Overhead Comparison", results_df)

    # Also get DNS-specific query metrics
    dns_data = exp1[exp1['protocol'] == 'DNS']
    dns_queries = dns_data[(dns_data['module'].str.contains('node\\[99\\]')) &
                           (dns_data['name'] == 'dnsQueriesSent:sum')]
    dns_responses = dns_data[(dns_data['module'].str.contains('node\\[99\\]')) &
                             (dns_data['name'] == 'dnsResponsesReceived:sum')]

    print(f"\n  DNS Client (node[99]):")
    print(f"    Queries Sent: {pd.to_numeric(dns_queries['value'], errors='coerce').mean():.0f}")
    print(f"    Responses Received: {pd.to_numeric(dns_responses['value'], errors='coerce').mean():.0f}")

    # Plot: Bar chart comparison
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Plot 1: Messages comparison
    ax1 = axes[0]
    protocols = results_df['Protocol'].tolist()
    msgs = results_df['Total Messages (mean)'].tolist()
    msgs_err = results_df['Total Messages (std)'].tolist()

    bars = ax1.bar(protocols, msgs, yerr=msgs_err, capsize=5,
                   color=[COLORS['BGP'], COLORS['DNS']], edgecolor='black')
    ax1.set_ylabel('Messages')
    ax1.set_title('Total Messages Sent')
    for bar, val in zip(bars, msgs):
        if val > 0:
            ax1.annotate(f'{val:.0f}', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                        xytext=(0, 3), textcoords='offset points', ha='center', va='bottom')

    # Plot 2: State size comparison
    ax2 = axes[1]
    sizes = results_df['State Size (mean)'].tolist()
    sizes_err = results_df['State Size (std)'].tolist()

    bars = ax2.bar(protocols, sizes, yerr=sizes_err, capsize=5,
                   color=[COLORS['BGP'], COLORS['DNS']], edgecolor='black')
    ax2.set_ylabel('Entries')
    ax2.set_title('Total State Size')
    for bar, val in zip(bars, sizes):
        if val > 0:
            ax2.annotate(f'{val:.0f}', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                        xytext=(0, 3), textcoords='offset points', ha='center', va='bottom')

    plt.suptitle('Experiment 1: Baseline Overhead Comparison', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_dir / 'exp1_baseline_overhead.png', dpi=DPI, bbox_inches='tight')
    plt.close()

    print(f"\n  Plot saved: {output_dir / 'exp1_baseline_overhead.png'}")
    return results_df


# =============================================================================
# EXPERIMENT 2: NETWORK SIZE SCALABILITY
# =============================================================================

def analyze_exp2(df, output_dir):
    """Analyze Experiment 2: Network Size Scalability."""
    print("\n" + "="*70)
    print(" EXPERIMENT 2: NETWORK SIZE SCALABILITY")
    print("="*70)

    exp2 = df[df['exp_num'] == 2].copy()

    # Aggregate by protocol and grid size using node-level data
    results = []
    for protocol in ['BGP', 'DNS']:
        for grid in ['5x5', '10x10', '15x15', '20x20']:
            prot_data = exp2[(exp2['protocol'] == protocol) & (exp2['grid_size'] == grid)]
            runs = prot_data['run'].unique()

            num_nodes = int(grid.split('x')[0]) ** 2
            msgs_list = []
            size_list = []

            for run in runs:
                run_data = prot_data[prot_data['run'] == run]

                # Total bytes received across all nodes (proxy for network activity)
                bytes_mask = (run_data['module'].str.contains('node')) & \
                             (run_data['name'] == 'messageBytesReceived:sum')
                total_bytes = pd.to_numeric(run_data[bytes_mask]['value'], errors='coerce').sum()
                msgs_list.append(total_bytes)

                # State size from groundTruth
                if protocol == 'BGP':
                    size_mask = (run_data['module'].str.contains('groundTruth')) & \
                                (run_data['name'] == 'totalBgpTableSize')
                else:
                    size_mask = (run_data['module'].str.contains('groundTruth')) & \
                                (run_data['name'].isin(['totalDnsCacheSize', 'totalDnsAuthoritySize']))
                state_size = pd.to_numeric(run_data[size_mask]['value'], errors='coerce').sum()
                size_list.append(state_size)

            results.append({
                'Protocol': protocol,
                'Grid': grid,
                'Nodes': num_nodes,
                'Bytes (mean)': np.mean(msgs_list) if msgs_list else 0,
                'Bytes (std)': np.std(msgs_list) if len(msgs_list) > 1 else 0,
                'State Size (mean)': np.mean(size_list) if size_list else 0,
            })

    results_df = pd.DataFrame(results)
    print_table("Scalability by Network Size", results_df)

    # Plot
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    bgp_data = results_df[results_df['Protocol'] == 'BGP'].sort_values('Nodes')
    dns_data = results_df[results_df['Protocol'] == 'DNS'].sort_values('Nodes')

    # Plot 1: Messages vs Network Size
    ax1 = axes[0]
    ax1.plot(bgp_data['Nodes'], bgp_data['Bytes (mean)'], 'o-',
             color=COLORS['BGP'], label='BGP', linewidth=2, markersize=8)
    ax1.plot(dns_data['Nodes'], dns_data['Bytes (mean)'], 's-',
             color=COLORS['DNS'], label='DNS', linewidth=2, markersize=8)
    ax1.set_xlabel('Number of Nodes')
    ax1.set_ylabel('Total Bytes')
    ax1.set_title('Network Bytes vs Network Size')
    ax1.legend()
    if bgp_data['Bytes (mean)'].max() > 0:
        ax1.set_yscale('log')

    # Plot 2: State Size vs Network Size
    ax2 = axes[1]
    ax2.plot(bgp_data['Nodes'], bgp_data['State Size (mean)'], 'o-',
             color=COLORS['BGP'], label='BGP (FIB entries)', linewidth=2, markersize=8)
    ax2.plot(dns_data['Nodes'], dns_data['State Size (mean)'], 's-',
             color=COLORS['DNS'], label='DNS (authority+cache)', linewidth=2, markersize=8)
    ax2.set_xlabel('Number of Nodes')
    ax2.set_ylabel('State Size (entries)')
    ax2.set_title('State Size vs Network Size')
    ax2.legend()

    plt.suptitle('Experiment 2: Network Size Scalability', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_dir / 'exp2_network_scalability.png', dpi=DPI, bbox_inches='tight')
    plt.close()

    print(f"  Plot saved: {output_dir / 'exp2_network_scalability.png'}")
    return results_df


# =============================================================================
# EXPERIMENT 3: EID COUNT SCALABILITY
# =============================================================================

def analyze_exp3(df, output_dir):
    """Analyze Experiment 3: EID Count Scalability."""
    print("\n" + "="*70)
    print(" EXPERIMENT 3: EID COUNT SCALABILITY")
    print("="*70)

    exp3 = df[df['exp_num'] == 3].copy()

    # Debug: check unique num_eids values
    print(f"  DEBUG: Unique num_eids values: {exp3['num_eids'].dropna().unique()}")

    results = []
    for protocol in ['BGP', 'DNS']:
        for num_eids in [10, 50, 100, 200, 500]:
            prot_data = exp3[(exp3['protocol'] == protocol) & (exp3['num_eids'] == num_eids)]
            runs = prot_data['run'].unique()

            msgs_list = []
            size_list = []

            for run in runs:
                run_data = prot_data[prot_data['run'] == run]

                # Total bytes received across all nodes (proxy for network activity)
                bytes_mask = (run_data['module'].str.contains('node')) & \
                             (run_data['name'] == 'messageBytesReceived:sum')
                total_bytes = pd.to_numeric(run_data[bytes_mask]['value'], errors='coerce').sum()
                msgs_list.append(total_bytes)

                # State size from groundTruth
                if protocol == 'BGP':
                    size_mask = (run_data['module'].str.contains('groundTruth')) & \
                                (run_data['name'] == 'totalBgpTableSize')
                else:
                    size_mask = (run_data['module'].str.contains('groundTruth')) & \
                                (run_data['name'] == 'totalDnsAuthoritySize')
                state_size = pd.to_numeric(run_data[size_mask]['value'], errors='coerce').sum()
                size_list.append(state_size)

            results.append({
                'Protocol': protocol,
                'EIDs': num_eids,
                'Bytes (mean)': np.mean(msgs_list) if msgs_list else 0,
                'Bytes (std)': np.std(msgs_list) if len(msgs_list) > 1 else 0,
                'State Size (mean)': np.mean(size_list) if size_list else 0,
            })

    results_df = pd.DataFrame(results)
    print_table("Scalability by EID Count", results_df)

    # Plot
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    bgp_data = results_df[results_df['Protocol'] == 'BGP'].sort_values('EIDs')
    dns_data = results_df[results_df['Protocol'] == 'DNS'].sort_values('EIDs')

    # Plot 1: Messages vs EID Count
    ax1 = axes[0]
    if bgp_data['Bytes (mean)'].max() > 0:
        ax1.plot(bgp_data['EIDs'], bgp_data['Bytes (mean)'], 'o-',
                 color=COLORS['BGP'], label='BGP', linewidth=2, markersize=8)
    if dns_data['Bytes (mean)'].max() > 0:
        ax1.plot(dns_data['EIDs'], dns_data['Bytes (mean)'], 's-',
                 color=COLORS['DNS'], label='DNS', linewidth=2, markersize=8)
    ax1.set_xlabel('Number of EIDs')
    ax1.set_ylabel('Total Bytes')
    ax1.set_title('Messages vs EID Count')
    ax1.legend()
    if bgp_data['Bytes (mean)'].max() > 0:
        ax1.set_yscale('log')

    # Plot 2: State Size vs EID Count
    ax2 = axes[1]
    if bgp_data['State Size (mean)'].max() > 0:
        ax2.plot(bgp_data['EIDs'], bgp_data['State Size (mean)'], 'o-',
                 color=COLORS['BGP'], label='BGP (N*E entries)', linewidth=2, markersize=8)
    if dns_data['State Size (mean)'].max() > 0:
        ax2.plot(dns_data['EIDs'], dns_data['State Size (mean)'], 's-',
                 color=COLORS['DNS'], label='DNS (E entries)', linewidth=2, markersize=8)
    ax2.set_xlabel('Number of EIDs')
    ax2.set_ylabel('State Size (entries)')
    ax2.set_title('State Size vs EID Count')
    ax2.legend()

    plt.suptitle('Experiment 3: EID Count Scalability', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_dir / 'exp3_eid_scalability.png', dpi=DPI, bbox_inches='tight')
    plt.close()

    print(f"  Plot saved: {output_dir / 'exp3_eid_scalability.png'}")
    return results_df


# =============================================================================
# EXPERIMENT 4: DISCOVERY LATENCY
# =============================================================================

def analyze_exp4(df, output_dir):
    """Analyze Experiment 4: Discovery Latency."""
    print("\n" + "="*70)
    print(" EXPERIMENT 4: DISCOVERY LATENCY")
    print("="*70)

    exp4 = df[df['exp_num'] == 4].copy()

    results = []
    for protocol in ['BGP', 'DNS']:
        mask = (exp4['protocol'] == protocol) & (exp4['module'].str.contains('groundTruth'))
        subset = exp4[mask]

        # Convergence time (BGP) or query latency indicator
        conv_mask = subset['name'] == 'avgConvergenceTime'
        conv = pd.to_numeric(subset[conv_mask]['value'], errors='coerce').dropna()

        # Get client node latency
        client_mask = (exp4['protocol'] == protocol) & \
                      (exp4['module'].str.contains('node\\[99\\]')) & \
                      (exp4['name'] == 'dnsQueryLatency:mean')
        client_latency = pd.to_numeric(exp4[client_mask]['value'], errors='coerce').dropna()

        results.append({
            'Protocol': protocol,
            'Convergence Time (mean)': conv.mean() if len(conv) > 0 else np.nan,
            'Convergence Time (std)': conv.std() if len(conv) > 1 else 0,
            'Query Latency (mean)': client_latency.mean() if len(client_latency) > 0 else np.nan,
            'Query Latency (std)': client_latency.std() if len(client_latency) > 1 else 0,
        })

    results_df = pd.DataFrame(results)
    print_table("Discovery Latency Comparison", results_df)

    # Also get discovery latency from client nodes
    discovery_results = []
    for protocol in ['BGP', 'DNS']:
        mask = (exp4['protocol'] == protocol) & \
               (exp4['module'].str.contains('node\\[99\\]')) & \
               (exp4['name'] == 'discoveryLatency:mean')
        values = pd.to_numeric(exp4[mask]['value'], errors='coerce').dropna()
        discovery_results.append({
            'Protocol': protocol,
            'Discovery Latency (s)': values.mean() if len(values) > 0 else np.nan
        })

    discovery_df = pd.DataFrame(discovery_results)
    print_table("Client Discovery Latency", discovery_df)

    # Plot using discoveryLatency for fair comparison
    fig, ax = plt.subplots(figsize=(8, 6))

    protocols = ['BGP', 'DNS']
    x = np.arange(len(protocols))
    width = 0.35

    # Use discovery latency for both protocols (fair comparison)
    disc_times = [discovery_df[discovery_df['Protocol'] == p]['Discovery Latency (s)'].values[0]
                  for p in protocols]

    # Replace NaN with 0 for plotting
    disc_times = [0 if pd.isna(x) else x for x in disc_times]

    bars = ax.bar(x, disc_times, width, capsize=5,
                  color=[COLORS['BGP'], COLORS['DNS']], edgecolor='black')

    ax.set_ylabel('Time (seconds)')
    ax.set_title('Experiment 4: Discovery Latency Comparison')
    ax.set_xticks(x)
    ax.set_xticklabels(['BGP', 'DNS'])

    # Add value labels on bars
    for bar, val in zip(bars, disc_times):
        if val > 0:
            ax.annotate(f'{val:.3f}s', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                       xytext=(0, 3), textcoords='offset points', ha='center', va='bottom')

    plt.tight_layout()
    plt.savefig(output_dir / 'exp4_discovery_latency.png', dpi=DPI, bbox_inches='tight')
    plt.close()

    print(f"  Plot saved: {output_dir / 'exp4_discovery_latency.png'}")
    return results_df


# =============================================================================
# EXPERIMENT 5: CHURN RESILIENCE
# =============================================================================

def analyze_exp5(df, output_dir):
    """Analyze Experiment 5: Churn Resilience."""
    print("\n" + "="*70)
    print(" EXPERIMENT 5: CHURN RESILIENCE")
    print("="*70)

    exp5 = df[df['exp_num'] == 5].copy()

    results = []
    for protocol in ['BGP', 'DNS']:
        for churn_int in [5, 10, 20, 60]:
            prot_data = exp5[(exp5['protocol'] == protocol) & (exp5['churn_interval'] == churn_int)]
            runs = prot_data['run'].unique()

            msgs_list = []
            for run in runs:
                run_data = prot_data[prot_data['run'] == run]

                # Total bytes received across all nodes (proxy for network activity)
                bytes_mask = (run_data['module'].str.contains('node')) & \
                             (run_data['name'] == 'messageBytesReceived:sum')
                total_bytes = pd.to_numeric(run_data[bytes_mask]['value'], errors='coerce').sum()
                msgs_list.append(total_bytes)

            results.append({
                'Protocol': protocol,
                'Churn Interval (s)': churn_int,
                'Bytes (mean)': np.mean(msgs_list) if msgs_list else 0,
                'Bytes (std)': np.std(msgs_list) if len(msgs_list) > 1 else 0,
            })

    results_df = pd.DataFrame(results)
    print_table("Churn Resilience - Message Overhead", results_df)

    # Client-side metrics: correct/stale answers and query responses
    client_results = []
    for protocol in ['BGP', 'DNS']:
        for churn_int in [5, 10, 20, 60]:
            prot_data = exp5[(exp5['protocol'] == protocol) & (exp5['churn_interval'] == churn_int)]

            # Get client node (node[99]) metrics
            client_mask = prot_data['module'].str.contains('node\\[99\\]')
            client_data = prot_data[client_mask]

            correct = pd.to_numeric(client_data[client_data['name'] == 'correctAnswers:sum']['value'],
                                   errors='coerce').sum()
            stale = pd.to_numeric(client_data[client_data['name'] == 'staleAnswers:sum']['value'],
                                 errors='coerce').sum()

            # For DNS, also check responses received
            if protocol == 'DNS':
                responses = pd.to_numeric(client_data[client_data['name'] == 'dnsResponsesReceived:sum']['value'],
                                         errors='coerce').sum()
            else:
                responses = correct + stale

            total = correct + stale
            if total == 0:
                total = responses  # Use responses as total if correct/stale not tracked

            client_results.append({
                'Protocol': protocol,
                'Churn Interval (s)': churn_int,
                'Correct Answers': correct,
                'Stale Answers': stale,
                'Total Responses': responses if protocol == 'DNS' else total,
                'Accuracy %': (correct / total * 100) if total > 0 else np.nan,
            })

    client_df = pd.DataFrame(client_results)
    print_table("Client Answer Accuracy", client_df)

    # Plot
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    bgp_data = results_df[results_df['Protocol'] == 'BGP'].sort_values('Churn Interval (s)')
    dns_data = results_df[results_df['Protocol'] == 'DNS'].sort_values('Churn Interval (s)')

    # Plot 1: Messages under Churn
    ax1 = axes[0]
    if bgp_data['Bytes (mean)'].max() > 0:
        ax1.plot(bgp_data['Churn Interval (s)'], bgp_data['Bytes (mean)'], 'o-',
                 color=COLORS['BGP'], label='BGP', linewidth=2, markersize=8)
    if dns_data['Bytes (mean)'].max() > 0:
        ax1.plot(dns_data['Churn Interval (s)'], dns_data['Bytes (mean)'], 's-',
                 color=COLORS['DNS'], label='DNS', linewidth=2, markersize=8)
    ax1.set_xlabel('Churn Interval (seconds)\n← Higher churn rate')
    ax1.set_ylabel('Total Bytes')
    ax1.set_title('Message Overhead vs Churn Rate')
    ax1.legend()
    ax1.invert_xaxis()  # Lower interval = higher churn rate
    if bgp_data['Bytes (mean)'].max() > 0:
        ax1.set_yscale('log')

    # Plot 2: Accuracy under Churn
    ax2 = axes[1]
    bgp_client = client_df[client_df['Protocol'] == 'BGP'].sort_values('Churn Interval (s)')
    dns_client = client_df[client_df['Protocol'] == 'DNS'].sort_values('Churn Interval (s)')

    ax2.plot(bgp_client['Churn Interval (s)'], bgp_client['Accuracy %'].fillna(0), 'o-',
             color=COLORS['BGP'], label='BGP', linewidth=2, markersize=8)
    ax2.plot(dns_client['Churn Interval (s)'], dns_client['Accuracy %'].fillna(0), 's-',
             color=COLORS['DNS'], label='DNS', linewidth=2, markersize=8)
    ax2.set_xlabel('Churn Interval (seconds)\n← Higher churn rate')
    ax2.set_ylabel('Answer Accuracy (%)')
    ax2.set_title('Accuracy vs Churn Rate')
    ax2.legend()
    ax2.set_ylim([0, 105])
    ax2.invert_xaxis()

    plt.suptitle('Experiment 5: Churn Resilience', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_dir / 'exp5_churn_resilience.png', dpi=DPI, bbox_inches='tight')
    plt.close()

    print(f"  Plot saved: {output_dir / 'exp5_churn_resilience.png'}")
    return results_df, client_df


# =============================================================================
# SUMMARY COMPARISON
# =============================================================================

def create_summary(df, output_dir):
    """Create overall summary comparison."""
    print("\n" + "="*70)
    print(" OVERALL SUMMARY: BGP vs DNS")
    print("="*70)

    summary_data = {
        'Dimension': [],
        'BGP': [],
        'DNS': [],
        'Winner': []
    }

    # Helper to add row
    def add_row(dim, bgp_val, dns_val, lower_is_better=True):
        summary_data['Dimension'].append(dim)
        summary_data['BGP'].append(bgp_val)
        summary_data['DNS'].append(dns_val)

        try:
            bgp_num = float(str(bgp_val).rstrip('%s'))
            dns_num = float(str(dns_val).rstrip('%s'))
            if lower_is_better:
                winner = 'DNS' if dns_num < bgp_num else 'BGP' if bgp_num < dns_num else 'Tie'
            else:
                winner = 'BGP' if bgp_num > dns_num else 'DNS' if dns_num > bgp_num else 'Tie'
        except:
            winner = 'N/A'
        summary_data['Winner'].append(winner)

    # Exp1: Baseline messages
    exp1 = df[df['exp_num'] == 1]
    bgp_msgs = dns_msgs = 0
    for protocol in ['BGP', 'DNS']:
        prot_data = exp1[exp1['protocol'] == protocol]
        if protocol == 'BGP':
            msg_mask = (prot_data['module'].str.contains('node')) & \
                       (prot_data['name'] == 'bgpAnnouncesSent:sum')
        else:
            msg_mask = (prot_data['module'].str.contains('node')) & \
                       (prot_data['name'].isin(['dnsQueriesSent:sum', 'dnsResponsesSent:sum']))
        total = pd.to_numeric(prot_data[msg_mask]['value'], errors='coerce').sum()
        if protocol == 'BGP':
            bgp_msgs = total
        else:
            dns_msgs = total
    add_row('Baseline Messages', f"{bgp_msgs:.0f}", f"{dns_msgs:.0f}")

    # Exp2: State size at 100 nodes
    exp2 = df[df['exp_num'] == 2]
    for protocol in ['BGP', 'DNS']:
        metric = 'totalBgpTableSize' if protocol == 'BGP' else 'totalDnsCacheSize'
        mask = (exp2['protocol'] == protocol) & \
               (exp2['grid_size'] == '10x10') & \
               (exp2['module'].str.contains('groundTruth')) & \
               (exp2['name'] == metric)
        val = pd.to_numeric(exp2[mask]['value'], errors='coerce').mean()
        if protocol == 'BGP':
            bgp_state = f"{val:.0f}" if not np.isnan(val) else "0"
        else:
            dns_state = f"{val:.0f}" if not np.isnan(val) else "0"
    add_row('State @ 100 nodes', bgp_state, dns_state)

    # Exp4: Discovery latency
    exp4 = df[df['exp_num'] == 4]
    bgp_lat = exp4[(exp4['protocol'] == 'BGP') &
                   (exp4['module'].str.contains('groundTruth')) &
                   (exp4['name'] == 'avgConvergenceTime')]
    dns_lat = exp4[(exp4['protocol'] == 'DNS') &
                   (exp4['module'].str.contains('node\\[99\\]')) &
                   (exp4['name'] == 'dnsQueryLatency:mean')]

    bgp_val = pd.to_numeric(bgp_lat['value'], errors='coerce').mean()
    dns_val = pd.to_numeric(dns_lat['value'], errors='coerce').mean()
    add_row('Discovery Latency',
            f"{bgp_val:.3f}s" if not np.isnan(bgp_val) else "N/A",
            f"{dns_val:.3f}s" if not np.isnan(dns_val) else "N/A")

    # Exp5: Churn messages at 5s interval
    exp5 = df[df['exp_num'] == 5]
    for protocol in ['BGP', 'DNS']:
        prot_data = exp5[(exp5['protocol'] == protocol) & (exp5['churn_interval'] == 5)]
        if protocol == 'BGP':
            msg_mask = (prot_data['module'].str.contains('node')) & \
                       (prot_data['name'] == 'bgpAnnouncesSent:sum')
        else:
            msg_mask = (prot_data['module'].str.contains('node')) & \
                       (prot_data['name'].isin(['dnsQueriesSent:sum', 'dnsResponsesSent:sum']))
        total = pd.to_numeric(prot_data[msg_mask]['value'], errors='coerce').sum()
        if protocol == 'BGP':
            bgp_churn = total
        else:
            dns_churn = total
    add_row('Churn Msgs (5s)', f"{bgp_churn:.0f}", f"{dns_churn:.0f}")

    # Exp5: Accuracy at 5s churn
    for protocol in ['BGP', 'DNS']:
        prot_data = exp5[(exp5['protocol'] == protocol) & (exp5['churn_interval'] == 5)]
        client_data = prot_data[prot_data['module'].str.contains('node\\[99\\]')]

        correct = pd.to_numeric(client_data[client_data['name'] == 'correctAnswers:sum']['value'],
                               errors='coerce').sum()
        stale = pd.to_numeric(client_data[client_data['name'] == 'staleAnswers:sum']['value'],
                             errors='coerce').sum()
        total = correct + stale
        acc = (correct / total * 100) if total > 0 else 0

        if protocol == 'BGP':
            bgp_acc = f"{acc:.1f}%"
        else:
            dns_acc = f"{acc:.1f}%" if total > 0 else "N/A"
    add_row('Churn Accuracy', bgp_acc, dns_acc, lower_is_better=False)

    summary_df = pd.DataFrame(summary_data)
    print_table("Summary Comparison", summary_df)

    # Create comparison table as figure
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.axis('off')

    table_data = [summary_df.columns.tolist()] + summary_df.values.tolist()
    colors = [['lightgray'] * 4] + [['white'] * 4 for _ in range(len(summary_df))]

    # Color winners
    for i, winner in enumerate(summary_df['Winner']):
        if winner == 'BGP':
            colors[i+1][1] = '#c8e6c9'  # Light green
        elif winner == 'DNS':
            colors[i+1][2] = '#c8e6c9'

    table = ax.table(cellText=table_data, cellColours=colors,
                     loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.2, 1.8)

    plt.title('BGP vs DNS: Summary Comparison', fontsize=14, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.savefig(output_dir / 'summary_comparison.png', dpi=DPI, bbox_inches='tight')
    plt.close()

    print(f"  Plot saved: {output_dir / 'summary_comparison.png'}")

    return summary_df


# =============================================================================
# MAIN
# =============================================================================

def main():
    # Parse arguments
    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])
    else:
        csv_path = Path('results/experiments_latest.csv')

    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}")
        print("Usage: python experiment_plots.py [path/to/experiments.csv]")
        sys.exit(1)

    # Create output directory
    output_dir = Path('plots')
    output_dir.mkdir(exist_ok=True)

    print(f"\nLoading data from: {csv_path}")
    df = load_data(csv_path)
    print(f"Loaded {len(df)} records from {df['run'].nunique()} experiment runs")

    # Analyze each experiment
    analyze_exp1(df, output_dir)
    analyze_exp2(df, output_dir)
    analyze_exp3(df, output_dir)
    analyze_exp4(df, output_dir)
    analyze_exp5(df, output_dir)

    # Create summary
    create_summary(df, output_dir)

    print("\n" + "="*70)
    print(" ANALYSIS COMPLETE")
    print("="*70)
    print(f"\nAll plots saved to: {output_dir.absolute()}")
    print("\nGenerated files:")
    for f in sorted(output_dir.glob('*.png')):
        print(f"  - {f.name}")


if __name__ == '__main__':
    main()
