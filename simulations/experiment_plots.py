#!/usr/bin/env python3
"""
experiment_plots.py - Analyze and visualize BGP vs DNS comparison experiments

Usage:
    python experiment_plots.py [results/experiments_latest.csv]

Generates tables and plots for experiments 1-10 as defined in experiment_plan.md
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


def save_plot(output_dir, name, dpi=DPI):
    """Save current plot in both PNG and PDF formats."""
    png_path = output_dir / f'{name}.png'
    pdf_path = output_dir / f'{name}.pdf'
    plt.savefig(png_path, dpi=dpi, bbox_inches='tight')
    plt.savefig(pdf_path, bbox_inches='tight')
    return png_path, pdf_path


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
    if 'M' in df.columns:
        df['M_clean'] = df['M'].apply(lambda x: str(x).strip('"').strip() if pd.notna(x) else None)
        df['num_eids'] = df['M_clean'].apply(lambda x: int(x.split('-')[1]) if x and '-' in str(x) and x != 'nan' else None)
    else:
        df['M_clean'] = None
        df['num_eids'] = np.nan

    # Clean churnInt for Exp5
    if 'churnInt' in df.columns:
        df['churn_interval'] = pd.to_numeric(df['churnInt'], errors='coerce')
    else:
        df['churn_interval'] = np.nan

    # Clean TTL for Exp6
    if 'TTL' in df.columns:
        df['ttl'] = pd.to_numeric(df['TTL'], errors='coerce')
    else:
        df['ttl'] = np.nan

    # Clean zipf alpha for Exp7
    if 'zipf' in df.columns:
        df['zipf_alpha'] = pd.to_numeric(df['zipf'], errors='coerce')
    else:
        df['zipf_alpha'] = np.nan

    # Clean delay for Exp8-10 (deep-space experiments)
    if 'delay' in df.columns:
        df['link_delay'] = pd.to_numeric(df['delay'], errors='coerce')
    else:
        df['link_delay'] = np.nan

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
    save_plot(output_dir, 'exp1_baseline_overhead')
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
    save_plot(output_dir, 'exp2_network_scalability')
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
    save_plot(output_dir, 'exp3_eid_scalability')
    plt.close()

    print(f"  Plot saved: {output_dir / 'exp3_eid_scalability.png'}")
    return results_df


# =============================================================================
# EXPERIMENT 4: DISCOVERY LATENCY
# =============================================================================

def analyze_exp4(df, output_dir):
    """Analyze Experiment 4: Discovery Latency and Resolution Latency."""
    print("\n" + "="*70)
    print(" EXPERIMENT 4: DISCOVERY & RESOLUTION LATENCY")
    print("="*70)

    exp4 = df[df['exp_num'] == 4].copy()

    # Collect metrics for both protocols
    results = []
    for protocol in ['BGP', 'DNS']:
        # Get convergence time from groundTruth (for BGP, this is discovery time)
        gt_mask = (exp4['protocol'] == protocol) & (exp4['module'].str.contains('groundTruth'))
        gt_subset = exp4[gt_mask]

        # Try initial convergence first, fallback to avg convergence
        conv_mask = gt_subset['name'] == 'avgInitialConvergenceTime'
        conv = pd.to_numeric(gt_subset[conv_mask]['value'], errors='coerce').dropna()
        if len(conv) == 0:
            conv_mask = gt_subset['name'] == 'avgConvergenceTime'
            conv = pd.to_numeric(gt_subset[conv_mask]['value'], errors='coerce').dropna()

        # Get query latency from client node (resolution latency for DNS)
        client_mask = (exp4['protocol'] == protocol) & \
                      (exp4['module'].str.contains('node\\[99\\]')) & \
                      (exp4['name'] == 'dnsQueryLatency:mean')
        query_latency = pd.to_numeric(exp4[client_mask]['value'], errors='coerce').dropna()

        # Get discovery latency from client node
        disc_mask = (exp4['protocol'] == protocol) & \
                    (exp4['module'].str.contains('node\\[99\\]')) & \
                    (exp4['name'] == 'discoveryLatency:mean')
        disc_latency = pd.to_numeric(exp4[disc_mask]['value'], errors='coerce').dropna()

        results.append({
            'Protocol': protocol,
            'Convergence Time (s)': conv.mean() if len(conv) > 0 else np.nan,
            'Discovery Latency (s)': disc_latency.mean() if len(disc_latency) > 0 else np.nan,
            'Resolution Latency (s)': query_latency.mean() if len(query_latency) > 0 else np.nan,
        })

    results_df = pd.DataFrame(results)
    print_table("Latency Metrics", results_df)

    # Explanation of metrics
    print("""
  Discovery Latency: Time from EID publish until a node can resolve it
    - BGP: Convergence time (proactive propagation)
    - DNS: First query round-trip (reactive lookup)

  Resolution Latency: Time to resolve an EID once discoverable
    - BGP: ~0 (local table lookup)
    - DNS: Query round-trip time (network dependent)
""")

    # Extract values for plotting
    bgp_row = results_df[results_df['Protocol'] == 'BGP'].iloc[0]
    dns_row = results_df[results_df['Protocol'] == 'DNS'].iloc[0]

    # For BGP: discovery = convergence, resolution = ~0 (use small value for visibility)
    bgp_discovery = bgp_row['Discovery Latency (s)'] if not pd.isna(bgp_row['Discovery Latency (s)']) else bgp_row['Convergence Time (s)']
    bgp_resolution = 0.001  # Near-zero local lookup

    # For DNS: discovery = first query, resolution = query latency
    dns_discovery = dns_row['Discovery Latency (s)'] if not pd.isna(dns_row['Discovery Latency (s)']) else dns_row['Resolution Latency (s)']
    dns_resolution = dns_row['Resolution Latency (s)'] if not pd.isna(dns_row['Resolution Latency (s)']) else dns_discovery

    # Create grouped bar chart
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    protocols = ['BGP', 'DNS']
    x = np.arange(len(protocols))
    width = 0.35

    # Left plot: Discovery Latency (time until first resolution possible)
    discovery_vals = [bgp_discovery if not pd.isna(bgp_discovery) else 0,
                      dns_discovery if not pd.isna(dns_discovery) else 0]

    bars1 = ax1.bar(x, discovery_vals, width, color=[COLORS['BGP'], COLORS['DNS']], edgecolor='black')
    ax1.set_ylabel('Time (seconds)')
    ax1.set_title('Discovery Latency\n(Time until EID is resolvable)')
    ax1.set_xticks(x)
    ax1.set_xticklabels(protocols)

    for bar, val in zip(bars1, discovery_vals):
        if val > 0:
            ax1.annotate(f'{val:.3f}s', xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                        xytext=(0, 3), textcoords='offset points', ha='center', va='bottom', fontsize=10)

    # Right plot: Resolution Latency (time per query once discoverable)
    resolution_vals = [bgp_resolution, dns_resolution if not pd.isna(dns_resolution) else 0]

    bars2 = ax2.bar(x, resolution_vals, width, color=[COLORS['BGP'], COLORS['DNS']], edgecolor='black')
    ax2.set_ylabel('Time (seconds)')
    ax2.set_title('Resolution Latency\n(Time per query after discovery)')
    ax2.set_xticks(x)
    ax2.set_xticklabels(protocols)

    for bar, val in zip(bars2, resolution_vals):
        label = f'{val:.3f}s' if val >= 0.001 else '~0s'
        ax2.annotate(label, xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                    xytext=(0, 3), textcoords='offset points', ha='center', va='bottom', fontsize=10)

    # Add explanation text
    fig.text(0.5, -0.02,
             'BGP: High discovery latency (proactive push), near-zero resolution (local lookup)\n'
             'DNS: Low discovery latency (no pre-propagation), but each query requires network round-trip',
             ha='center', fontsize=9, style='italic')

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.15)
    save_plot(output_dir, 'exp4_discovery_latency')
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
    save_plot(output_dir, 'exp5_churn_resilience')
    plt.close()

    print(f"  Plot saved: {output_dir / 'exp5_churn_resilience.png'}")
    return results_df, client_df


# =============================================================================
# EXPERIMENT 6: STALENESS UNDER CHURN
# =============================================================================

def analyze_exp6(df, output_dir):
    """Analyze Experiment 6: Staleness Under Churn with TTL sweep."""
    print("\n" + "="*70)
    print(" EXPERIMENT 6: STALENESS UNDER CHURN")
    print("="*70)

    exp6 = df[df['exp_num'] == 6].copy()

    if len(exp6) == 0:
        print("  No data available for Experiment 6. Run the experiment first.")
        return None

    # BGP results (single configuration, no TTL sweep)
    bgp_results = []
    bgp_data = exp6[exp6['protocol'] == 'BGP']
    runs = bgp_data['run'].unique()

    correct_list = []
    stale_list = []
    for run in runs:
        run_data = bgp_data[bgp_data['run'] == run]
        client_data = run_data[run_data['module'].str.contains('node\\[99\\]')]

        correct = pd.to_numeric(client_data[client_data['name'] == 'correctAnswers:sum']['value'],
                               errors='coerce').sum()
        stale = pd.to_numeric(client_data[client_data['name'] == 'staleAnswers:sum']['value'],
                             errors='coerce').sum()
        correct_list.append(correct)
        stale_list.append(stale)

    bgp_correct = np.mean(correct_list) if correct_list else 0
    bgp_stale = np.mean(stale_list) if stale_list else 0
    bgp_total = bgp_correct + bgp_stale
    bgp_accuracy = (bgp_correct / bgp_total * 100) if bgp_total > 0 else 0

    print(f"\n  BGP (no TTL):")
    print(f"    Correct: {bgp_correct:.0f}, Stale: {bgp_stale:.0f}, Accuracy: {bgp_accuracy:.1f}%")

    # DNS results with TTL sweep
    dns_results = []
    for ttl in [15, 30, 60, 120]:
        dns_data = exp6[(exp6['protocol'] == 'DNS') & (exp6['ttl'] == ttl)]
        runs = dns_data['run'].unique()

        correct_list = []
        stale_list = []
        for run in runs:
            run_data = dns_data[dns_data['run'] == run]
            client_data = run_data[run_data['module'].str.contains('node\\[99\\]')]

            correct = pd.to_numeric(client_data[client_data['name'] == 'correctAnswers:sum']['value'],
                                   errors='coerce').sum()
            stale = pd.to_numeric(client_data[client_data['name'] == 'staleAnswers:sum']['value'],
                                 errors='coerce').sum()
            correct_list.append(correct)
            stale_list.append(stale)

        mean_correct = np.mean(correct_list) if correct_list else 0
        mean_stale = np.mean(stale_list) if stale_list else 0
        total = mean_correct + mean_stale
        accuracy = (mean_correct / total * 100) if total > 0 else 0

        dns_results.append({
            'TTL (s)': ttl,
            'Correct': mean_correct,
            'Stale': mean_stale,
            'Total': total,
            'Accuracy %': accuracy,
        })

    results_df = pd.DataFrame(dns_results)
    print_table("DNS Staleness by TTL", results_df)

    # Plot
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    ttls = results_df['TTL (s)'].tolist()
    accuracies = results_df['Accuracy %'].tolist()
    stale_counts = results_df['Stale'].tolist()

    # Plot 1: Accuracy vs TTL
    ax1 = axes[0]
    ax1.plot(ttls, accuracies, 's-', color=COLORS['DNS'], label='DNS', linewidth=2, markersize=8)
    ax1.axhline(y=bgp_accuracy, color=COLORS['BGP'], linestyle='--', linewidth=2, label=f'BGP ({bgp_accuracy:.1f}%)')
    ax1.set_xlabel('DNS TTL (seconds)')
    ax1.set_ylabel('Accuracy (%)')
    ax1.set_title('Answer Accuracy vs TTL')
    ax1.legend()
    ax1.set_ylim([0, 105])

    # Plot 2: Stale answers vs TTL
    ax2 = axes[1]
    ax2.plot(ttls, stale_counts, 's-', color=COLORS['DNS'], label='DNS', linewidth=2, markersize=8)
    ax2.axhline(y=bgp_stale, color=COLORS['BGP'], linestyle='--', linewidth=2, label=f'BGP ({bgp_stale:.0f})')
    ax2.set_xlabel('DNS TTL (seconds)')
    ax2.set_ylabel('Stale Answers (count)')
    ax2.set_title('Stale Answers vs TTL')
    ax2.legend()

    plt.suptitle('Experiment 6: Staleness Under Churn', fontsize=14, fontweight='bold')
    plt.tight_layout()
    save_plot(output_dir, 'exp6_staleness')
    plt.close()

    print(f"  Plot saved: {output_dir / 'exp6_staleness.png'}")
    return results_df


# =============================================================================
# EXPERIMENT 7: QUERY PATTERN IMPACT (DNS only)
# =============================================================================

def analyze_exp7(df, output_dir):
    """Analyze Experiment 7: Query Pattern Impact on DNS caching."""
    print("\n" + "="*70)
    print(" EXPERIMENT 7: QUERY PATTERN IMPACT (DNS)")
    print("="*70)

    exp7 = df[df['exp_num'] == 7].copy()

    if len(exp7) == 0:
        print("  No data available for Experiment 7. Run the experiment first.")
        return None

    # Debug: show available zipf values
    print(f"  DEBUG: Available zipf_alpha values: {sorted(exp7['zipf_alpha'].dropna().unique())}")

    results = []
    for zipf in [0, 0.5, 1.0, 1.5, 2.0]:
        zipf_data = exp7[exp7['zipf_alpha'] == zipf]
        runs = zipf_data['run'].unique()

        if len(runs) == 0:
            print(f"  Warning: No data for zipf={zipf}")
            continue

        cache_hits_list = []
        cache_misses_list = []
        queries_list = []

        for run in runs:
            run_data = zipf_data[zipf_data['run'] == run]

            # In direct mode, cache stats are emitted by the CLIENT (node[99])
            # because the client directly accesses resolver's cache
            client_data = run_data[run_data['module'].str.contains('node\\[99\\]')]

            hits = pd.to_numeric(client_data[client_data['name'] == 'dnsCacheHits:sum']['value'],
                                errors='coerce').sum()
            misses = pd.to_numeric(client_data[client_data['name'] == 'dnsCacheMisses:sum']['value'],
                                  errors='coerce').sum()
            cache_hits_list.append(hits)
            cache_misses_list.append(misses)

            # Get client queries sent
            queries = pd.to_numeric(client_data[client_data['name'] == 'dnsQueriesSent:sum']['value'],
                                   errors='coerce').sum()
            queries_list.append(queries)

        mean_hits = np.mean(cache_hits_list) if cache_hits_list else 0
        mean_misses = np.mean(cache_misses_list) if cache_misses_list else 0
        mean_queries = np.mean(queries_list) if queries_list else 0
        total_lookups = mean_hits + mean_misses
        hit_rate = (mean_hits / total_lookups * 100) if total_lookups > 0 else 0

        results.append({
            'Zipf Alpha': zipf,
            'Cache Hits': mean_hits,
            'Cache Misses': mean_misses,
            'Hit Rate %': hit_rate,
            'Client Queries': mean_queries,
        })

    if not results:
        print("  No valid data found for Experiment 7.")
        return None

    results_df = pd.DataFrame(results)
    print_table("DNS Cache Performance by Query Distribution", results_df)

    # Plot
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    zipf_vals = results_df['Zipf Alpha'].tolist()
    hit_rates = results_df['Hit Rate %'].tolist()
    misses = results_df['Cache Misses'].tolist()

    # Plot 1: Cache Hit Rate vs Zipf Alpha
    ax1 = axes[0]
    ax1.plot(zipf_vals, hit_rates, 'o-', color=COLORS['DNS'], linewidth=2, markersize=8)
    ax1.set_xlabel('Zipf Alpha (0=uniform, higher=more skewed)')
    ax1.set_ylabel('Cache Hit Rate (%)')
    ax1.set_title('Cache Hit Rate vs Query Distribution')
    ax1.set_ylim([0, 105])

    # Add annotations
    for i, (x, y) in enumerate(zip(zipf_vals, hit_rates)):
        ax1.annotate(f'{y:.1f}%', xy=(x, y), xytext=(0, 8),
                    textcoords='offset points', ha='center', fontsize=9)

    # Plot 2: Cache Misses (Authority Queries) vs Zipf Alpha
    ax2 = axes[1]
    ax2.plot(zipf_vals, misses, 's-', color=COLORS['DNS'], linewidth=2, markersize=8)
    ax2.set_xlabel('Zipf Alpha (0=uniform, higher=more skewed)')
    ax2.set_ylabel('Cache Misses (Authority Queries)')
    ax2.set_title('Authority Load vs Query Distribution')

    plt.suptitle('Experiment 7: Query Pattern Impact on DNS Caching', fontsize=14, fontweight='bold')
    plt.tight_layout()
    save_plot(output_dir, 'exp7_query_pattern')
    plt.close()

    print(f"  Plot saved: {output_dir / 'exp7_query_pattern.png'}")
    return results_df


# =============================================================================
# EXPERIMENT 8: DEEP-SPACE BASELINE LATENCY
# =============================================================================

def analyze_exp8(df, output_dir):
    """Analyze Experiment 8: Deep-space baseline latency."""
    print("\n" + "="*70)
    print(" EXPERIMENT 8: DEEP-SPACE BASELINE LATENCY")
    print("="*70)

    exp8 = df[df['exp_num'] == 8].copy()

    if len(exp8) == 0:
        print("  No data available for Experiment 8. Run the experiment first.")
        return None

    # Debug: show available delay values
    print(f"  DEBUG: Available link_delay values: {sorted(exp8['link_delay'].dropna().unique())}")

    results = []
    for delay in [0.01, 0.1, 1, 5, 10, 20]:
        for protocol in ['BGP', 'DNS']:
            delay_data = exp8[(exp8['link_delay'] == delay) & (exp8['protocol'] == protocol)]
            runs = delay_data['run'].unique()

            if len(runs) == 0:
                continue

            convergence_list = []
            discovery_lat_list = []
            query_lat_list = []

            for run in runs:
                run_data = delay_data[delay_data['run'] == run]

                # Get convergence time from groundTruth
                gt_data = run_data[run_data['module'].str.contains('groundTruth')]
                # Use avgInitialConvergenceTime for accurate initial propagation time
                conv = pd.to_numeric(gt_data[gt_data['name'] == 'avgInitialConvergenceTime']['value'],
                                    errors='coerce').mean()
                # Fall back to avgConvergenceTime if initial not available
                if pd.isna(conv):
                    conv = pd.to_numeric(gt_data[gt_data['name'] == 'avgConvergenceTime']['value'],
                                        errors='coerce').mean()
                convergence_list.append(conv if not pd.isna(conv) else 0)

                # Get client discovery latency
                client_data = run_data[run_data['module'].str.contains('node\\[24\\]')]
                disc_lat = pd.to_numeric(client_data[client_data['name'] == 'discoveryLatency:mean']['value'],
                                        errors='coerce').mean()
                discovery_lat_list.append(disc_lat if not pd.isna(disc_lat) else 0)

                # Get DNS query latency
                if protocol == 'DNS':
                    query_lat = pd.to_numeric(client_data[client_data['name'] == 'dnsQueryLatency:mean']['value'],
                                             errors='coerce').mean()
                    query_lat_list.append(query_lat if not pd.isna(query_lat) else 0)

            results.append({
                'Protocol': protocol,
                'Link Delay (s)': delay,
                'Convergence Time (s)': np.mean(convergence_list) if convergence_list else 0,
                'Discovery Latency (s)': np.mean(discovery_lat_list) if discovery_lat_list else 0,
                'Query Latency (s)': np.mean(query_lat_list) if query_lat_list else 0,
            })

    if not results:
        print("  No valid data found for Experiment 8.")
        return None

    results_df = pd.DataFrame(results)
    print_table("Deep-Space Latency Comparison", results_df)

    # Plot
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    bgp_data = results_df[results_df['Protocol'] == 'BGP'].sort_values('Link Delay (s)')
    dns_data = results_df[results_df['Protocol'] == 'DNS'].sort_values('Link Delay (s)')

    # Plot 1: Convergence/First-Discovery Time vs Link Delay
    ax1 = axes[0]
    if len(bgp_data) > 0 and bgp_data['Convergence Time (s)'].max() > 0:
        ax1.plot(bgp_data['Link Delay (s)'], bgp_data['Convergence Time (s)'], 'o-',
                 color=COLORS['BGP'], label='BGP Convergence', linewidth=2, markersize=8)
    if len(dns_data) > 0 and dns_data['Discovery Latency (s)'].max() > 0:
        ax1.plot(dns_data['Link Delay (s)'], dns_data['Discovery Latency (s)'], 's-',
                 color=COLORS['DNS'], label='DNS First Query', linewidth=2, markersize=8)
    ax1.set_xlabel('Link Delay (seconds)')
    ax1.set_ylabel('Time (seconds)')
    ax1.set_title('Initial Discovery Time vs Link Delay')
    ax1.legend()
    ax1.set_xscale('log')
    ax1.set_yscale('log')

    # Plot 2: Subsequent Lookup Latency
    ax2 = axes[1]
    delays = bgp_data['Link Delay (s)'].tolist() if len(bgp_data) > 0 else dns_data['Link Delay (s)'].tolist()

    # BGP lookup is essentially 0 (local FIB)
    bgp_lookup = [0.001] * len(delays)  # Use small value for log scale
    dns_lookup = dns_data['Query Latency (s)'].tolist() if len(dns_data) > 0 else []

    if delays:
        ax2.plot(delays, bgp_lookup, 'o-', color=COLORS['BGP'],
                 label='BGP (local FIB)', linewidth=2, markersize=8)
    if dns_lookup:
        ax2.plot(dns_data['Link Delay (s)'].tolist(), dns_lookup, 's-', color=COLORS['DNS'],
                 label='DNS (query RTT)', linewidth=2, markersize=8)
    ax2.set_xlabel('Link Delay (seconds)')
    ax2.set_ylabel('Lookup Latency (seconds)')
    ax2.set_title('Subsequent Lookup Latency')
    ax2.legend()
    ax2.set_xscale('log')
    ax2.set_yscale('log')

    plt.suptitle('Experiment 8: Deep-Space Baseline Latency', fontsize=14, fontweight='bold')
    plt.tight_layout()
    save_plot(output_dir, 'exp8_deepspace_latency')
    plt.close()

    print(f"  Plot saved: {output_dir / 'exp8_deepspace_latency.png'}")
    return results_df


# =============================================================================
# EXPERIMENT 9: DEEP-SPACE DNS CACHING IMPACT
# =============================================================================

def analyze_exp9(df, output_dir):
    """Analyze Experiment 9: Deep-space DNS caching impact."""
    print("\n" + "="*70)
    print(" EXPERIMENT 9: DEEP-SPACE DNS CACHING IMPACT")
    print("="*70)

    exp9 = df[df['exp_num'] == 9].copy()

    if len(exp9) == 0:
        print("  No data available for Experiment 9. Run the experiment first.")
        return None

    print(f"  DEBUG: Available link_delay values: {sorted(exp9['link_delay'].dropna().unique())}")

    results = []
    for delay in [1, 5, 10, 20]:
        for cache_mode in ['Cache', 'NoCache']:
            # Filter by experiment name pattern
            if cache_mode == 'Cache':
                mode_data = exp9[exp9['experiment'].str.contains('DnsCache') &
                                ~exp9['experiment'].str.contains('NoCache')]
            else:
                mode_data = exp9[exp9['experiment'].str.contains('DnsNoCache')]

            delay_data = mode_data[mode_data['link_delay'] == delay]
            runs = delay_data['run'].unique()

            if len(runs) == 0:
                continue

            cache_hits_list = []
            cache_misses_list = []
            query_lat_list = []
            total_queries_list = []

            for run in runs:
                run_data = delay_data[delay_data['run'] == run]

                # Get client stats
                client_data = run_data[run_data['module'].str.contains('node\\[24\\]')]

                hits = pd.to_numeric(client_data[client_data['name'] == 'dnsCacheHits:sum']['value'],
                                    errors='coerce').sum()
                misses = pd.to_numeric(client_data[client_data['name'] == 'dnsCacheMisses:sum']['value'],
                                      errors='coerce').sum()
                cache_hits_list.append(hits)
                cache_misses_list.append(misses)

                queries = pd.to_numeric(client_data[client_data['name'] == 'dnsQueriesSent:sum']['value'],
                                       errors='coerce').sum()
                total_queries_list.append(queries)

                query_lat = pd.to_numeric(client_data[client_data['name'] == 'dnsQueryLatency:mean']['value'],
                                         errors='coerce').mean()
                query_lat_list.append(query_lat if not pd.isna(query_lat) else 0)

            mean_hits = np.mean(cache_hits_list) if cache_hits_list else 0
            mean_misses = np.mean(cache_misses_list) if cache_misses_list else 0
            mean_queries = np.mean(total_queries_list) if total_queries_list else 0
            mean_lat = np.mean(query_lat_list) if query_lat_list else 0

            total = mean_hits + mean_misses
            hit_rate = (mean_hits / total * 100) if total > 0 else 0

            results.append({
                'Link Delay (s)': delay,
                'Cache Mode': cache_mode,
                'Cache Hits': mean_hits,
                'Cache Misses': mean_misses,
                'Hit Rate %': hit_rate,
                'Avg Query Latency (s)': mean_lat,
                'Total Queries': mean_queries,
            })

    if not results:
        print("  No valid data found for Experiment 9.")
        return None

    results_df = pd.DataFrame(results)
    print_table("Deep-Space DNS Caching Impact", results_df)

    # Plot
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    cache_data = results_df[results_df['Cache Mode'] == 'Cache'].sort_values('Link Delay (s)')
    nocache_data = results_df[results_df['Cache Mode'] == 'NoCache'].sort_values('Link Delay (s)')

    # Plot 1: Average Query Latency comparison (the key insight!)
    ax1 = axes[0]
    if len(cache_data) > 0:
        ax1.plot(cache_data['Link Delay (s)'], cache_data['Avg Query Latency (s)'], 'o-',
                 color=COLORS['DNS'], label='With Caching', linewidth=2, markersize=8)
    if len(nocache_data) > 0:
        ax1.plot(nocache_data['Link Delay (s)'], nocache_data['Avg Query Latency (s)'], 's--',
                 color='gray', label='No Caching', linewidth=2, markersize=8)
    ax1.set_xlabel('Link Delay (seconds)')
    ax1.set_ylabel('Average Query Latency (seconds)')
    ax1.set_title('Query Latency: Caching Benefit')
    ax1.legend()
    ax1.set_xscale('log')
    ax1.set_yscale('log')

    # Plot 2: Latency reduction percentage
    ax2 = axes[1]
    if len(cache_data) > 0 and len(nocache_data) > 0:
        # Calculate latency reduction for each delay
        delays = cache_data['Link Delay (s)'].tolist()
        cache_lat = cache_data['Avg Query Latency (s)'].tolist()
        nocache_lat = nocache_data['Avg Query Latency (s)'].tolist()

        reduction_pct = [(1 - c/n) * 100 if n > 0 else 0 for c, n in zip(cache_lat, nocache_lat)]
        time_saved = [n - c for c, n in zip(cache_lat, nocache_lat)]

        # Bar chart showing time saved
        x = np.arange(len(delays))
        width = 0.6
        bars = ax2.bar(x, time_saved, width, color=COLORS['DNS'], alpha=0.7)

        # Add percentage labels on bars
        for i, (bar, pct) in enumerate(zip(bars, reduction_pct)):
            ax2.annotate(f'{pct:.1f}%',
                        xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                        xytext=(0, 3), textcoords='offset points',
                        ha='center', va='bottom', fontsize=10, fontweight='bold')

        ax2.set_xlabel('Link Delay (seconds)')
        ax2.set_ylabel('Time Saved per Query (seconds)')
        ax2.set_title('Absolute Latency Reduction from Caching')
        ax2.set_xticks(x)
        ax2.set_xticklabels([f'{d}s' for d in delays])

    plt.suptitle('Experiment 9: Deep-Space DNS Caching Impact', fontsize=14, fontweight='bold')
    plt.tight_layout()
    save_plot(output_dir, 'exp9_deepspace_caching')
    plt.close()

    print(f"  Plot saved: {output_dir / 'exp9_deepspace_caching.png'}")
    return results_df


# =============================================================================
# EXPERIMENT 10: DEEP-SPACE CHURN RESILIENCE
# =============================================================================

def analyze_exp10(df, output_dir):
    """Analyze Experiment 10: Deep-space churn resilience."""
    print("\n" + "="*70)
    print(" EXPERIMENT 10: DEEP-SPACE CHURN RESILIENCE")
    print("="*70)

    exp10 = df[df['exp_num'] == 10].copy()

    if len(exp10) == 0:
        print("  No data available for Experiment 10. Run the experiment first.")
        return None

    print(f"  DEBUG: Available link_delay values: {sorted(exp10['link_delay'].dropna().unique())}")
    print(f"  DEBUG: Available churn_interval values: {sorted(exp10['churn_interval'].dropna().unique())}")

    results = []
    for delay in [5, 10, 20]:
        for churn_int in [20, 60, 120]:
            for protocol in ['BGP', 'DNS']:
                prot_data = exp10[(exp10['protocol'] == protocol) &
                                  (exp10['link_delay'] == delay) &
                                  (exp10['churn_interval'] == churn_int)]
                runs = prot_data['run'].unique()

                if len(runs) == 0:
                    continue

                correct_list = []
                stale_list = []
                convergence_list = []

                for run in runs:
                    run_data = prot_data[prot_data['run'] == run]

                    # Get client accuracy stats
                    client_data = run_data[run_data['module'].str.contains('node\\[24\\]')]

                    correct = pd.to_numeric(client_data[client_data['name'] == 'correctAnswers:sum']['value'],
                                           errors='coerce').sum()
                    stale = pd.to_numeric(client_data[client_data['name'] == 'staleAnswers:sum']['value'],
                                         errors='coerce').sum()
                    correct_list.append(correct)
                    stale_list.append(stale)

                    # Get convergence time - use avgInitialConvergenceTime for accurate initial propagation
                    gt_data = run_data[run_data['module'].str.contains('groundTruth')]
                    conv = pd.to_numeric(gt_data[gt_data['name'] == 'avgInitialConvergenceTime']['value'],
                                        errors='coerce').mean()
                    # Fall back to globalConvergenceTime:max (captures initial convergence even with churn)
                    if pd.isna(conv) or conv == 0:
                        conv = pd.to_numeric(gt_data[gt_data['name'] == 'globalConvergenceTime:max']['value'],
                                            errors='coerce').mean()
                    # Last resort: avgConvergenceTime
                    if pd.isna(conv) or conv == 0:
                        conv = pd.to_numeric(gt_data[gt_data['name'] == 'avgConvergenceTime']['value'],
                                            errors='coerce').mean()
                    convergence_list.append(conv if not pd.isna(conv) else 0)

                mean_correct = np.mean(correct_list) if correct_list else 0
                mean_stale = np.mean(stale_list) if stale_list else 0
                mean_conv = np.mean(convergence_list) if convergence_list else 0
                total = mean_correct + mean_stale
                accuracy = (mean_correct / total * 100) if total > 0 else 0

                # Calculate expected convergence time (8 hops × delay)
                expected_conv = 8 * delay

                results.append({
                    'Protocol': protocol,
                    'Link Delay (s)': delay,
                    'Churn Interval (s)': churn_int,
                    'Correct': mean_correct,
                    'Stale': mean_stale,
                    'Accuracy %': accuracy,
                    'Convergence (s)': mean_conv,
                    'Expected Conv (s)': expected_conv,
                    'Conv/Churn Ratio': expected_conv / churn_int,
                })

    if not results:
        print("  No valid data found for Experiment 10.")
        return None

    results_df = pd.DataFrame(results)
    print_table("Deep-Space Churn Resilience", results_df)

    # Plot with more informative visualizations
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    bgp_data = results_df[results_df['Protocol'] == 'BGP']
    dns_data = results_df[results_df['Protocol'] == 'DNS']

    # Plot 1: Convergence Time vs Link Delay (this clearly scales!)
    ax1 = axes[0]
    for churn_int in [20, 60, 120]:
        bgp_churn = bgp_data[bgp_data['Churn Interval (s)'] == churn_int].sort_values('Link Delay (s)')

        if len(bgp_churn) > 0:
            ax1.plot(bgp_churn['Link Delay (s)'], bgp_churn['Convergence (s)'], 'o-',
                     label=f'Measured (churn={churn_int}s)', linewidth=2, markersize=8)

    # Add theoretical line (8 hops × delay)
    delays = [5, 10, 20]
    theoretical = [8 * d for d in delays]
    ax1.plot(delays, theoretical, 'k--', linewidth=2, label='Theoretical (8×delay)', alpha=0.7)

    # Add horizontal lines for churn intervals
    ax1.axhline(y=20, color='red', linestyle=':', alpha=0.5, label='Churn=20s')
    ax1.axhline(y=60, color='orange', linestyle=':', alpha=0.5, label='Churn=60s')
    ax1.axhline(y=120, color='green', linestyle=':', alpha=0.5, label='Churn=120s')

    ax1.set_xlabel('Link Delay (seconds)')
    ax1.set_ylabel('BGP Convergence Time (seconds)')
    ax1.set_title('BGP Convergence Time vs Link Delay\n(Convergence > Churn = potential staleness)')
    ax1.legend(fontsize=8, loc='upper left')
    ax1.set_xlim([3, 25])
    ax1.set_ylim([0, 200])

    # Plot 2: Grouped bar chart comparing accuracy (zoomed to show differences)
    ax2 = axes[1]

    # Prepare data for grouped bars
    delays = sorted(results_df['Link Delay (s)'].unique())
    churn_intervals = sorted(results_df['Churn Interval (s)'].unique())

    x = np.arange(len(delays))
    width = 0.12
    offset = 0

    # Create bars for each protocol × churn combination
    colors_bgp = ['#1a5276', '#2874a6', '#3498db']  # Dark to light blue
    colors_dns = ['#7b241c', '#a93226', '#e74c3c']  # Dark to light red

    for i, churn_int in enumerate(churn_intervals):
        bgp_acc = bgp_data[bgp_data['Churn Interval (s)'] == churn_int].sort_values('Link Delay (s)')['Accuracy %'].tolist()
        dns_acc = dns_data[dns_data['Churn Interval (s)'] == churn_int].sort_values('Link Delay (s)')['Accuracy %'].tolist()

        if bgp_acc:
            bars1 = ax2.bar(x + offset, bgp_acc, width, label=f'BGP churn={churn_int}s',
                           color=colors_bgp[i], alpha=0.8)
            offset += width
        if dns_acc:
            bars2 = ax2.bar(x + offset, dns_acc, width, label=f'DNS churn={churn_int}s',
                           color=colors_dns[i], alpha=0.8)
            offset += width

    ax2.set_xlabel('Link Delay (seconds)')
    ax2.set_ylabel('Accuracy (%)')
    ax2.set_title('Answer Accuracy by Protocol, Delay & Churn\n(Zoomed: 75-100%)')
    ax2.set_xticks(x + width * 2.5)
    ax2.set_xticklabels([f'{d}s' for d in delays])
    ax2.legend(fontsize=7, ncol=2, loc='lower left')
    ax2.set_ylim([0, 105])  # Full range to show degradation
    ax2.axhline(y=100, color='green', linestyle='--', alpha=0.3)

    plt.suptitle('Experiment 10: Deep-Space Churn Resilience', fontsize=14, fontweight='bold')
    plt.tight_layout()
    save_plot(output_dir, 'exp10_deepspace_churn')
    plt.close()

    print(f"  Plot saved: {output_dir / 'exp10_deepspace_churn.png'}")
    return results_df


# =============================================================================
# SUMMARY COMPARISON
# =============================================================================

def create_summary(df, output_dir):
    """Create comprehensive summary comparison covering all experiments."""
    print("\n" + "="*70)
    print(" OVERALL SUMMARY: BGP vs DNS (All Experiments)")
    print("="*70)

    summary_data = {
        'Experiment': [],
        'Metric': [],
        'BGP': [],
        'DNS': [],
        'Winner': []
    }

    # Helper to normalize value with unit to base unit
    def normalize_value(val_str):
        """Convert value string to normalized number (e.g., '5.0 MB' -> 5000000)."""
        val_str = str(val_str).strip()
        if val_str == 'N/A':
            return None
        # Extract number and unit
        import re
        match = re.match(r'([\d.]+)\s*(%|s|KB|MB|GB)?', val_str)
        if not match:
            return None
        num = float(match.group(1))
        unit = match.group(2) if match.group(2) else ''
        # Normalize based on unit
        if unit == 'KB':
            return num * 1000
        elif unit == 'MB':
            return num * 1000000
        elif unit == 'GB':
            return num * 1000000000
        else:
            return num  # Already in base unit (bytes, seconds, %)

    # Helper to add row
    def add_row(exp, metric, bgp_val, dns_val, lower_is_better=True):
        summary_data['Experiment'].append(exp)
        summary_data['Metric'].append(metric)
        summary_data['BGP'].append(bgp_val)
        summary_data['DNS'].append(dns_val)

        try:
            bgp_num = normalize_value(bgp_val)
            dns_num = normalize_value(dns_val)
            if bgp_num is None or dns_num is None:
                winner = '-'
            elif lower_is_better:
                winner = 'DNS' if dns_num < bgp_num else 'BGP' if bgp_num < dns_num else 'Tie'
            else:
                winner = 'BGP' if bgp_num > dns_num else 'DNS' if dns_num > bgp_num else 'Tie'
        except:
            winner = '-'
        summary_data['Winner'].append(winner)

    # =========================================================================
    # Exp1: Baseline Overhead
    # =========================================================================
    exp1 = df[df['exp_num'] == 1]
    if len(exp1) > 0:
        for protocol in ['BGP', 'DNS']:
            prot_data = exp1[exp1['protocol'] == protocol]
            # Sum bytes sent across all nodes
            bytes_mask = (prot_data['module'].str.contains('node')) & \
                         (prot_data['name'] == 'messageBytesSent:sum')
            bytes_val = pd.to_numeric(prot_data[bytes_mask]['value'], errors='coerce').sum()
            if protocol == 'BGP':
                bgp_bytes = bytes_val
            else:
                dns_bytes = bytes_val
        add_row('1: Baseline', 'Total Bytes',
                f"{bgp_bytes/1000:.1f} KB" if bgp_bytes > 0 else "N/A",
                f"{dns_bytes/1000:.1f} KB" if dns_bytes > 0 else "N/A")

    # =========================================================================
    # Exp2: Network Scalability (400 nodes)
    # =========================================================================
    exp2 = df[df['exp_num'] == 2]
    if len(exp2) > 0:
        for protocol in ['BGP', 'DNS']:
            prot_data = exp2[(exp2['protocol'] == protocol) & (exp2['grid_size'] == '20x20')]
            bytes_mask = (prot_data['module'].str.contains('node')) & \
                         (prot_data['name'] == 'messageBytesSent:sum')
            bytes_val = pd.to_numeric(prot_data[bytes_mask]['value'], errors='coerce').sum()
            if protocol == 'BGP':
                bgp_bytes = bytes_val
            else:
                dns_bytes = bytes_val
        add_row('2: Scale (400 nodes)', 'Total Bytes',
                f"{bgp_bytes/1000:.0f} KB" if bgp_bytes > 0 else "N/A",
                f"{dns_bytes/1000:.0f} KB" if dns_bytes > 0 else "N/A")

    # =========================================================================
    # Exp3: EID Scalability (500 EIDs)
    # =========================================================================
    exp3 = df[df['exp_num'] == 3]
    if len(exp3) > 0:
        for protocol in ['BGP', 'DNS']:
            prot_data = exp3[(exp3['protocol'] == protocol) & (exp3['num_eids'] == 500)]
            bytes_mask = (prot_data['module'].str.contains('node')) & \
                         (prot_data['name'] == 'messageBytesSent:sum')
            bytes_val = pd.to_numeric(prot_data[bytes_mask]['value'], errors='coerce').sum()
            if protocol == 'BGP':
                bgp_bytes = bytes_val
            else:
                dns_bytes = bytes_val
        add_row('3: Scale (500 EIDs)', 'Total Bytes',
                f"{bgp_bytes/1000000:.1f} MB" if bgp_bytes > 0 else "N/A",
                f"{dns_bytes/1000:.0f} KB" if dns_bytes > 0 else "N/A")

    # =========================================================================
    # Exp4: Discovery Latency
    # =========================================================================
    exp4 = df[df['exp_num'] == 4]
    if len(exp4) > 0:
        bgp_lat = exp4[(exp4['protocol'] == 'BGP') &
                       (exp4['module'].str.contains('groundTruth')) &
                       (exp4['name'] == 'avgConvergenceTime')]
        dns_lat = exp4[(exp4['protocol'] == 'DNS') &
                       (exp4['module'].str.contains('node\\[99\\]')) &
                       (exp4['name'] == 'dnsQueryLatency:mean')]
        bgp_val = pd.to_numeric(bgp_lat['value'], errors='coerce').mean()
        dns_val = pd.to_numeric(dns_lat['value'], errors='coerce').mean()
        add_row('4: Latency', 'Discovery Time',
                f"{bgp_val:.2f}s" if not np.isnan(bgp_val) else "N/A",
                f"{dns_val:.2f}s" if not np.isnan(dns_val) else "N/A")

    # =========================================================================
    # Exp5: Churn Resilience (5s churn)
    # =========================================================================
    exp5 = df[df['exp_num'] == 5]
    if len(exp5) > 0:
        for protocol in ['BGP', 'DNS']:
            prot_data = exp5[(exp5['protocol'] == protocol) & (exp5['churn_interval'] == 5)]
            bytes_mask = (prot_data['module'].str.contains('node')) & \
                         (prot_data['name'] == 'messageBytesSent:sum')
            bytes_val = pd.to_numeric(prot_data[bytes_mask]['value'], errors='coerce').sum()
            if protocol == 'BGP':
                bgp_bytes = bytes_val
            else:
                dns_bytes = bytes_val
        add_row('5: Churn (5s)', 'Overhead',
                f"{bgp_bytes/1000000:.1f} MB" if bgp_bytes > 0 else "N/A",
                f"{dns_bytes/1000:.0f} KB" if dns_bytes > 0 else "N/A")

        # Accuracy
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
                bgp_acc = acc
            else:
                dns_acc = acc
        add_row('5: Churn (5s)', 'Accuracy',
                f"{bgp_acc:.0f}%", f"{dns_acc:.0f}%", lower_is_better=False)

    # =========================================================================
    # Exp6: Staleness (TTL=15s)
    # =========================================================================
    exp6 = df[df['exp_num'] == 6]
    if len(exp6) > 0:
        bgp_data = exp6[exp6['protocol'] == 'BGP']
        client_data = bgp_data[bgp_data['module'].str.contains('node\\[99\\]')]
        bgp_correct = pd.to_numeric(client_data[client_data['name'] == 'correctAnswers:sum']['value'],
                                   errors='coerce').sum()
        bgp_stale = pd.to_numeric(client_data[client_data['name'] == 'staleAnswers:sum']['value'],
                                 errors='coerce').sum()
        bgp_total = bgp_correct + bgp_stale
        bgp_acc = (bgp_correct / bgp_total * 100) if bgp_total > 0 else 0

        dns_data = exp6[(exp6['protocol'] == 'DNS') & (exp6['ttl'] == 15)]
        client_data = dns_data[dns_data['module'].str.contains('node\\[99\\]')]
        dns_correct = pd.to_numeric(client_data[client_data['name'] == 'correctAnswers:sum']['value'],
                                   errors='coerce').sum()
        dns_stale = pd.to_numeric(client_data[client_data['name'] == 'staleAnswers:sum']['value'],
                                 errors='coerce').sum()
        dns_total = dns_correct + dns_stale
        dns_acc = (dns_correct / dns_total * 100) if dns_total > 0 else 0

        add_row('6: Staleness', 'Accuracy (TTL=15s)',
                f"{bgp_acc:.0f}%", f"{dns_acc:.0f}%", lower_is_better=False)

    # =========================================================================
    # Exp7: Query Pattern (DNS only, α=1.0)
    # =========================================================================
    exp7 = df[df['exp_num'] == 7]
    if len(exp7) > 0:
        dns_data = exp7[(exp7['protocol'] == 'DNS') & (exp7['zipf_alpha'] == 1.0)]
        client_data = dns_data[dns_data['module'].str.contains('node\\[99\\]')]
        hits = pd.to_numeric(client_data[client_data['name'] == 'dnsCacheHits:sum']['value'],
                            errors='coerce').sum()
        misses = pd.to_numeric(client_data[client_data['name'] == 'dnsCacheMisses:sum']['value'],
                              errors='coerce').sum()
        hit_rate = (hits / (hits + misses) * 100) if (hits + misses) > 0 else 0
        add_row('7: Query Pattern', 'Cache Hit Rate (α=1)',
                "N/A", f"{hit_rate:.0f}%", lower_is_better=False)

    # =========================================================================
    # Exp8: Deep-Space Latency (20s delay)
    # =========================================================================
    exp8 = df[df['exp_num'] == 8]
    if len(exp8) > 0:
        bgp_data = exp8[(exp8['protocol'] == 'BGP') & (exp8['link_delay'] == 20)]
        gt_data = bgp_data[bgp_data['module'].str.contains('groundTruth')]
        bgp_conv = pd.to_numeric(gt_data[gt_data['name'] == 'avgInitialConvergenceTime']['value'],
                                errors='coerce').mean()
        if np.isnan(bgp_conv):
            bgp_conv = pd.to_numeric(gt_data[gt_data['name'] == 'avgConvergenceTime']['value'],
                                    errors='coerce').mean()

        dns_data = exp8[(exp8['protocol'] == 'DNS') & (exp8['link_delay'] == 20)]
        client_data = dns_data[dns_data['module'].str.contains('node\\[24\\]')]
        dns_lat = pd.to_numeric(client_data[client_data['name'] == 'dnsQueryLatency:mean']['value'],
                               errors='coerce').mean()

        add_row('8: Deep-Space (20s)', 'Convergence/Query',
                f"{bgp_conv:.0f}s" if not np.isnan(bgp_conv) else "N/A",
                f"{dns_lat:.0f}s" if not np.isnan(dns_lat) else "N/A")

    # =========================================================================
    # Exp9: DNS Caching (20s delay)
    # =========================================================================
    exp9 = df[df['exp_num'] == 9]
    if len(exp9) > 0:
        cache_data = exp9[exp9['experiment'].str.contains('DnsCache') &
                          ~exp9['experiment'].str.contains('NoCache') &
                          (exp9['link_delay'] == 20)]
        nocache_data = exp9[exp9['experiment'].str.contains('NoCache') &
                           (exp9['link_delay'] == 20)]

        cache_client = cache_data[cache_data['module'].str.contains('node\\[24\\]')]
        cache_lat = pd.to_numeric(cache_client[cache_client['name'] == 'dnsQueryLatency:mean']['value'],
                                 errors='coerce').mean()

        nocache_client = nocache_data[nocache_data['module'].str.contains('node\\[24\\]')]
        nocache_lat = pd.to_numeric(nocache_client[nocache_client['name'] == 'dnsQueryLatency:mean']['value'],
                                   errors='coerce').mean()

        if not np.isnan(cache_lat) and not np.isnan(nocache_lat):
            reduction = (1 - cache_lat / nocache_lat) * 100
            add_row('9: Caching (20s)', 'Latency Reduction',
                    "N/A", f"{reduction:.0f}%", lower_is_better=False)

    # =========================================================================
    # Exp10: Deep-Space Churn (20s delay, 20s churn)
    # =========================================================================
    exp10 = df[df['exp_num'] == 10]
    if len(exp10) > 0:
        for protocol in ['BGP', 'DNS']:
            prot_data = exp10[(exp10['protocol'] == protocol) &
                             (exp10['link_delay'] == 20) &
                             (exp10['churn_interval'] == 20)]
            client_data = prot_data[prot_data['module'].str.contains('node\\[24\\]')]
            correct = pd.to_numeric(client_data[client_data['name'] == 'correctAnswers:sum']['value'],
                                   errors='coerce').sum()
            stale = pd.to_numeric(client_data[client_data['name'] == 'staleAnswers:sum']['value'],
                                 errors='coerce').sum()
            total = correct + stale
            acc = (correct / total * 100) if total > 0 else 0
            if protocol == 'BGP':
                bgp_acc = acc
            else:
                dns_acc = acc
        add_row('10: Deep Churn', 'Accuracy (20s/20s)',
                f"{bgp_acc:.0f}%", f"{dns_acc:.0f}%", lower_is_better=False)

    summary_df = pd.DataFrame(summary_data)
    print_table("Comprehensive Summary", summary_df)

    # Count wins
    bgp_wins = (summary_df['Winner'] == 'BGP').sum()
    dns_wins = (summary_df['Winner'] == 'DNS').sum()
    print(f"\n  Score: BGP {bgp_wins} - DNS {dns_wins}")

    # Create comparison table as figure
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.axis('off')

    table_data = [summary_df.columns.tolist()] + summary_df.values.tolist()
    colors = [['#d0d0d0'] * 5] + [['white'] * 5 for _ in range(len(summary_df))]

    # Color winners
    for i, winner in enumerate(summary_df['Winner']):
        if winner == 'BGP':
            colors[i+1][2] = '#c8e6c9'  # Light green for BGP column
        elif winner == 'DNS':
            colors[i+1][3] = '#c8e6c9'  # Light green for DNS column

    table = ax.table(cellText=table_data, cellColours=colors,
                     loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.6)

    # Style header row
    for j in range(5):
        table[(0, j)].set_text_props(fontweight='bold')

    plt.title(f'BGP vs DNS: Comprehensive Summary (BGP {bgp_wins} - DNS {dns_wins})',
              fontsize=14, fontweight='bold', pad=20)
    plt.tight_layout()
    save_plot(output_dir, 'summary_comparison')
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
    analyze_exp6(df, output_dir)
    analyze_exp7(df, output_dir)

    # Deep-space experiments
    analyze_exp8(df, output_dir)
    analyze_exp9(df, output_dir)
    analyze_exp10(df, output_dir)

    # Create summary
    create_summary(df, output_dir)

    print("\n" + "="*70)
    print(" ANALYSIS COMPLETE")
    print("="*70)
    print(f"\nAll plots saved to: {output_dir.absolute()}")
    print("\nGenerated PNG files:")
    for f in sorted(output_dir.glob('*.png')):
        print(f"  - {f.name}")
    print("\nGenerated PDF files:")
    for f in sorted(output_dir.glob('*.pdf')):
        print(f"  - {f.name}")


if __name__ == '__main__':
    main()
