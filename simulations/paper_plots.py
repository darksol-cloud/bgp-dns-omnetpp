#!/usr/bin/env python3
"""
paper_plots.py - Generate publication-quality plots for the IEEE paper.

Usage:
    python paper_plots.py [results/experiments_latest.csv]

Generates plots in simulations/plots/paper/ suitable for inclusion in the LaTeX document.
All plots use IEEE-friendly formatting: single-column width (~3.5in) or double-column (~7in).
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import sys
import re
from pathlib import Path

# IEEE-friendly style
matplotlib.rcParams.update({
    'font.family': 'serif',
    'font.size': 8,
    'axes.labelsize': 8,
    'axes.titlesize': 8,
    'legend.fontsize': 6.5,
    'xtick.labelsize': 7,
    'ytick.labelsize': 7,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'lines.linewidth': 1.5,
    'lines.markersize': 5,
})

# Color scheme (colorblind-friendly)
C_BGP = '#2E86AB'
C_DNS = '#A23B72'
HATCH_BGP = None
HATCH_DNS = '//'

# IEEE column widths
# Figures are drawn at the width they are rendered at (one IEEE column), so
# that in-figure text keeps its nominal point size in the compiled paper.
COL_W = 3.45  # single-column width in inches
DBL_W = 7.16  # double-column width in inches


def save(output_dir, name):
    plt.savefig(output_dir / f'{name}.pdf', bbox_inches='tight')
    plt.savefig(output_dir / f'{name}.png', bbox_inches='tight')
    plt.close()
    print(f'  Saved {name}.pdf')


def load_data(csv_path):
    df = pd.read_csv(csv_path)
    df['experiment'] = df['run'].apply(
        lambda x: re.match(r'(Exp\d+_[^-]+)', x).group(1) if re.match(r'(Exp\d+_[^-]+)', x) else x)
    df['protocol'] = df['experiment'].apply(lambda x: 'BGP' if 'Bgp' in x else 'DNS')
    df['exp_num'] = df['experiment'].apply(
        lambda x: int(re.search(r'Exp(\d+)', x).group(1)) if re.search(r'Exp(\d+)', x) else 0)
    df['grid_size'] = df['experiment'].apply(
        lambda x: re.search(r'(\d+x\d+)', x).group(1) if re.search(r'(\d+x\d+)', x) else None)
    df['num_nodes'] = df['grid_size'].apply(lambda x: int(x.split('x')[0])**2 if x else None)
    if 'M' in df.columns:
        df['M_clean'] = df['M'].apply(lambda x: str(x).strip('"').strip() if pd.notna(x) else None)
        df['num_eids'] = df['M_clean'].apply(
            lambda x: int(x.split('-')[1]) if x and '-' in str(x) and x != 'nan' else None)
    else:
        df['num_eids'] = np.nan
    if 'churnInt' in df.columns:
        df['churn_interval'] = pd.to_numeric(df['churnInt'], errors='coerce')
    else:
        df['churn_interval'] = np.nan
    if 'TTL' in df.columns:
        df['ttl'] = pd.to_numeric(df['TTL'], errors='coerce')
    else:
        df['ttl'] = np.nan
    if 'zipf' in df.columns:
        df['zipf_alpha'] = pd.to_numeric(df['zipf'], errors='coerce')
    else:
        df['zipf_alpha'] = np.nan
    if 'delay' in df.columns:
        df['link_delay'] = pd.to_numeric(df['delay'], errors='coerce')
    else:
        df['link_delay'] = np.nan
    return df


def sum_node_bytes(subset, metric='messageBytesSent:sum'):
    mask = (subset['module'].str.contains('node')) & (subset['name'] == metric)
    return pd.to_numeric(subset[mask]['value'], errors='coerce').sum()


def sum_per_run(df_filtered, metric='messageBytesSent:sum', module='node'):
    vals = []
    for run in df_filtered['run'].unique():
        run_data = df_filtered[df_filtered['run'] == run]
        mask = (run_data['module'].str.contains(module)) & (run_data['name'] == metric)
        vals.append(pd.to_numeric(run_data[mask]['value'], errors='coerce').sum())
    return np.mean(vals) if vals else 0, np.std(vals) if len(vals) > 1 else 0


# =========================================================================
# Fig 1: Scalability (Network Size + EID Count) - double column
# =========================================================================
def plot_scalability(df, out):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(COL_W, 1.22))

    # --- Panel (a): Network size scalability ---
    for protocol, color, marker, label in [('BGP', C_BGP, 'o', 'BGP (push)'),
                                            ('DNS', C_DNS, 's', 'DNS (pull)')]:
        nodes_list, bytes_list = [], []
        for grid in ['5x5', '10x10', '15x15', '20x20']:
            pdata = df[(df['exp_num'] == 2) & (df['protocol'] == protocol) & (df['grid_size'] == grid)]
            n = int(grid.split('x')[0])**2
            mean_b, _ = sum_per_run(pdata, 'messageBytesReceived:sum')
            nodes_list.append(n)
            bytes_list.append(mean_b)
        ax1.plot(nodes_list, bytes_list, marker=marker, color=color, label=label)

    ax1.set_xlabel('Number of nodes ($N$)')
    ax1.set_ylabel('Total bytes')
    ax1.set_yscale('log')
    ax1.legend(handlelength=1.0, borderpad=0.3, labelspacing=0.2)
    ax1.set_title('(a) Network size scalability')

    # --- Panel (b): EID count scalability ---
    for protocol, color, marker, label in [('BGP', C_BGP, 'o', 'BGP (push)'),
                                            ('DNS', C_DNS, 's', 'DNS (pull)')]:
        eids_list, bytes_list = [], []
        for ne in [10, 50, 100, 200, 500]:
            pdata = df[(df['exp_num'] == 3) & (df['protocol'] == protocol) & (df['num_eids'] == ne)]
            mean_b, _ = sum_per_run(pdata, 'messageBytesReceived:sum')
            eids_list.append(ne)
            bytes_list.append(mean_b)
        ax2.plot(eids_list, bytes_list, marker=marker, color=color, label=label)

    ax2.set_xlabel('Number of EIDs ($M$)')
    ax2.set_ylabel('Total bytes')
    ax2.set_yscale('log')
    ax2.set_title('(b) EID count scalability')

    plt.tight_layout()
    save(out, 'fig_scalability')


# =========================================================================
# Fig 2: Churn resilience - overhead and accuracy
# =========================================================================
def plot_churn(df, out):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(COL_W, 1.22))

    churn_vals = [5, 10, 20, 60]

    # --- Panel (a): Overhead under churn ---
    for protocol, color, marker, label in [('BGP', C_BGP, 'o', 'BGP'),
                                            ('DNS', C_DNS, 's', 'DNS')]:
        bytes_list = []
        for ci in churn_vals:
            pdata = df[(df['exp_num'] == 5) & (df['protocol'] == protocol) & (df['churn_interval'] == ci)]
            mean_b, _ = sum_per_run(pdata, 'messageBytesReceived:sum')
            bytes_list.append(mean_b)
        ax1.plot(churn_vals, bytes_list, marker=marker, color=color, label=label)

    ax1.set_xlabel('Churn interval (s)')
    ax1.set_ylabel('Total bytes')
    ax1.set_yscale('log')
    ax1.invert_xaxis()
    ax1.legend(handlelength=1.0, borderpad=0.3, labelspacing=0.2)
    ax1.set_title('(a) Overhead vs. churn')

    # --- Panel (b): Accuracy under churn ---
    for protocol, color, marker, label in [('BGP', C_BGP, 'o', 'BGP'),
                                            ('DNS', C_DNS, 's', 'DNS')]:
        acc_list = []
        for ci in churn_vals:
            pdata = df[(df['exp_num'] == 5) & (df['protocol'] == protocol) & (df['churn_interval'] == ci)]
            client_data = pdata[pdata['module'].str.contains(r'node\[99\]')]
            correct = pd.to_numeric(
                client_data[client_data['name'] == 'correctAnswers:sum']['value'], errors='coerce').sum()
            stale = pd.to_numeric(
                client_data[client_data['name'] == 'staleAnswers:sum']['value'], errors='coerce').sum()
            total = correct + stale
            acc_list.append((correct / total * 100) if total > 0 else 0)
        ax2.plot(churn_vals, acc_list, marker=marker, color=color, label=label)

    ax2.set_xlabel('Churn interval (s)')
    ax2.set_ylabel('Accuracy (%)')
    ax2.set_ylim([0, 105])
    ax2.invert_xaxis()
    ax2.set_title('(b) Accuracy vs. churn')

    plt.tight_layout()
    save(out, 'fig_churn')


# =========================================================================
# Fig 3: DNS staleness (TTL sweep) and cache effectiveness
# =========================================================================
def plot_dns_analysis(df, out):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(DBL_W, 2.4))

    # --- Panel (a): Staleness vs TTL ---
    ttls = [15, 30, 60, 120]
    accuracies = []
    for ttl in ttls:
        dns_data = df[(df['exp_num'] == 6) & (df['protocol'] == 'DNS') & (df['ttl'] == ttl)]
        client_data = dns_data[dns_data['module'].str.contains(r'node\[99\]')]
        correct = pd.to_numeric(
            client_data[client_data['name'] == 'correctAnswers:sum']['value'], errors='coerce').sum()
        stale = pd.to_numeric(
            client_data[client_data['name'] == 'staleAnswers:sum']['value'], errors='coerce').sum()
        total = correct + stale
        accuracies.append((correct / total * 100) if total > 0 else 0)

    # BGP baseline
    bgp_data = df[(df['exp_num'] == 6) & (df['protocol'] == 'BGP')]
    bgp_client = bgp_data[bgp_data['module'].str.contains(r'node\[99\]')]
    bgp_c = pd.to_numeric(bgp_client[bgp_client['name'] == 'correctAnswers:sum']['value'], errors='coerce').sum()
    bgp_s = pd.to_numeric(bgp_client[bgp_client['name'] == 'staleAnswers:sum']['value'], errors='coerce').sum()
    bgp_acc = (bgp_c / (bgp_c + bgp_s) * 100) if (bgp_c + bgp_s) > 0 else 100

    ax1.plot(ttls, accuracies, 's-', color=C_DNS, label='DNS')
    ax1.axhline(y=bgp_acc, color=C_BGP, linestyle='--', label=f'BGP ({bgp_acc:.0f}%)')
    ax1.set_xlabel('DNS TTL (s)')
    ax1.set_ylabel('Accuracy (%)')
    ax1.set_ylim([0, 105])
    ax1.legend(handlelength=1.0, borderpad=0.3, labelspacing=0.2)
    ax1.set_title('(a) Accuracy vs. TTL (churn=10 s)')

    # --- Panel (b): Cache hit rate vs Zipf alpha ---
    zipf_vals = [0, 0.5, 1.0, 1.5, 2.0]
    hit_rates = []
    for z in zipf_vals:
        zdata = df[(df['exp_num'] == 7) & (df['zipf_alpha'] == z)]
        client = zdata[zdata['module'].str.contains(r'node\[99\]')]
        hits = pd.to_numeric(client[client['name'] == 'dnsCacheHits:sum']['value'], errors='coerce').sum()
        misses = pd.to_numeric(client[client['name'] == 'dnsCacheMisses:sum']['value'], errors='coerce').sum()
        total = hits + misses
        hit_rates.append((hits / total * 100) if total > 0 else 0)

    ax2.plot(zipf_vals, hit_rates, 's-', color=C_DNS)
    for x, y in zip(zipf_vals, hit_rates):
        ax2.annotate(f'{y:.0f}%', xy=(x, y), xytext=(0, 6), textcoords='offset points', ha='center', fontsize=7)
    ax2.set_xlabel('Zipf $\\alpha$')
    ax2.set_ylabel('Cache hit rate (%)')
    ax2.set_ylim([0, 50])
    ax2.set_title('(b) Cache effectiveness')

    plt.tight_layout()
    save(out, 'fig_dns_analysis')


# =========================================================================
# Fig 4: Deep-space latency and churn
# =========================================================================
def plot_deepspace(df, out):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(COL_W, 1.22))

    # --- Panel (a): Convergence/query time vs link delay ---
    delays = [0.01, 0.1, 1, 5, 10, 20]
    bgp_conv, dns_lat = [], []
    for d in delays:
        # BGP convergence
        bdata = df[(df['exp_num'] == 8) & (df['protocol'] == 'BGP') & (df['link_delay'] == d)]
        gt = bdata[bdata['module'].str.contains('groundTruth')]
        cv = pd.to_numeric(gt[gt['name'] == 'avgInitialConvergenceTime']['value'], errors='coerce').mean()
        if pd.isna(cv):
            cv = pd.to_numeric(gt[gt['name'] == 'avgConvergenceTime']['value'], errors='coerce').mean()
        bgp_conv.append(cv if not pd.isna(cv) else 0)

        # DNS query latency
        ddata = df[(df['exp_num'] == 8) & (df['protocol'] == 'DNS') & (df['link_delay'] == d)]
        cl = ddata[ddata['module'].str.contains(r'node\[24\]')]
        ql = pd.to_numeric(cl[cl['name'] == 'dnsQueryLatency:mean']['value'], errors='coerce').mean()
        dns_lat.append(ql if not pd.isna(ql) else 0)

    ax1.plot(delays, bgp_conv, 'o-', color=C_BGP, label='BGP conv.')
    ax1.plot(delays, dns_lat, 's-', color=C_DNS, label='DNS RTT')
    ax1.set_xlabel('Link delay (s)')
    ax1.set_ylabel('Time (s)')
    ax1.set_xscale('log')
    ax1.set_yscale('log')
    ax1.legend(loc='upper left', handlelength=1.0, borderpad=0.3, labelspacing=0.2)
    ax1.set_title('(a) Latency vs. delay')

    # --- Panel (b): Accuracy under deep-space churn ---
    # Group by conv/churn ratio
    ratios, bgp_acc, dns_acc = [], [], []
    for d in [5, 10, 20]:
        for ci in [20, 60, 120]:
            ratio = (8 * d) / ci
            ratios.append(ratio)
            for protocol in ['BGP', 'DNS']:
                pdata = df[(df['exp_num'] == 10) & (df['protocol'] == protocol) &
                           (df['link_delay'] == d) & (df['churn_interval'] == ci)]
                client = pdata[pdata['module'].str.contains(r'node\[24\]')]
                correct = pd.to_numeric(
                    client[client['name'] == 'correctAnswers:sum']['value'], errors='coerce').sum()
                stale = pd.to_numeric(
                    client[client['name'] == 'staleAnswers:sum']['value'], errors='coerce').sum()
                total = correct + stale
                acc = (correct / total * 100) if total > 0 else 0
                if protocol == 'BGP':
                    bgp_acc.append(acc)
                else:
                    dns_acc.append(acc)

    # Sort by ratio for clean plot
    order = np.argsort(ratios)
    ratios_sorted = np.array(ratios)[order]
    bgp_sorted = np.array(bgp_acc)[order]
    dns_sorted = np.array(dns_acc)[order]

    ax2.plot(ratios_sorted, bgp_sorted, 'o-', color=C_BGP, label='BGP')
    ax2.plot(ratios_sorted, dns_sorted, 's-', color=C_DNS, label='DNS')
    ax2.axvline(x=1.0, color='gray', linestyle=':', alpha=0.7)
    ax2.annotate('conv = churn', xy=(1.3, 71.5), fontsize=5, color='gray',
                 ha='left', va='bottom')
    ax2.set_xlabel('Conv./churn ratio $R$')
    ax2.set_ylabel('Accuracy (%)')
    ax2.set_ylim([70, 105])
    ax2.set_title('(b) Accuracy vs. $R$')

    plt.tight_layout()
    save(out, 'fig_deepspace')


# =========================================================================
# Fig 5: Realistic scenarios - three panels
# =========================================================================
def plot_realistic(df, out):
    fig, axes = plt.subplots(1, 3, figsize=(COL_W, 1.22))

    # --- Panel (a): Terrestrial overhead ---
    ax = axes[0]
    churn_labels = []
    bgp_bytes_vals, dns_bytes_vals = [], []
    exp11 = df[df['exp_num'] == 11]
    for ci in sorted(exp11['churn_interval'].dropna().unique()):
        churn_labels.append(f'{int(ci)}s')
        for protocol in ['BGP', 'DNS']:
            pdata = exp11[(exp11['protocol'] == protocol) & (exp11['churn_interval'] == ci)]
            vals = []
            for run in pdata['run'].unique():
                rd = pdata[pdata['run'] == run]
                mask = (rd['module'].str.contains(r'(command|relay|team|drone)')) & \
                       (rd['name'] == 'messageBytesSent:sum')
                vals.append(pd.to_numeric(rd[mask]['value'], errors='coerce').sum())
            mean_v = np.mean(vals) if vals else 0
            if protocol == 'BGP':
                bgp_bytes_vals.append(mean_v / 1000)
            else:
                dns_bytes_vals.append(mean_v / 1000)

    x = np.arange(len(churn_labels))
    w = 0.32
    ax.bar(x - w/2, bgp_bytes_vals, w, color=C_BGP, label='BGP')
    ax.bar(x + w/2, dns_bytes_vals, w, color=C_DNS, label='DNS')
    ax.set_xlabel('Churn interval')
    ax.set_ylabel('Overhead (KB)')
    ax.set_xticks(x)
    ax.set_xticklabels(churn_labels)
    ax.legend(fontsize=6, handlelength=1.0, borderpad=0.3, labelspacing=0.2)
    ax.set_title('(a) Terrestrial')

    # --- Panel (b): Lunar amortized cost ---
    ax = axes[1]
    # Estimated values for lunar scenario
    bgp_conv = 1.6   # seconds
    dns_query = 0.6   # seconds per query (lunar-local)
    n_queries = np.arange(1, 21)
    ax.plot(n_queries, np.full_like(n_queries, bgp_conv, dtype=float), '-',
            color=C_BGP, label='BGP (conv.)')
    ax.plot(n_queries, n_queries * dns_query, '-',
            color=C_DNS, label='DNS (query)')

    breakeven = bgp_conv / dns_query
    ax.axvline(x=breakeven, color='gray', linestyle=':', alpha=0.7)
    ax.annotate(f'break-even\n{breakeven:.1f} queries', xy=(9.5, 2.4),
                fontsize=5.5, ha='left', color='gray')
    ax.set_xlabel('Queries')
    ax.set_ylabel('Cum. time (s)', fontsize=7)
    ax.set_title('(b) Lunar')

    # --- Panel (c): Mars cumulative cost ---
    ax = axes[2]
    bgp_conv_mars = 120   # 2 min
    dns_query_mars = 240  # 4 min per Mars-local query
    n_q = np.arange(1, 16)
    ax.plot(n_q, np.full_like(n_q, bgp_conv_mars/60, dtype=float), '-',
            color=C_BGP, label='BGP (conv.)')
    ax.plot(n_q, n_q * dns_query_mars / 60, '-',
            color=C_DNS, label='DNS (query)')

    ax.fill_between(n_q, np.full_like(n_q, bgp_conv_mars/60, dtype=float),
                     n_q * dns_query_mars / 60, alpha=0.15, color=C_DNS)
    ax.set_xlabel('Queries')
    ax.set_ylabel('Cum. time (min)', fontsize=7)
    ax.set_title('(c) Mars')

    plt.tight_layout()
    save(out, 'fig_realistic')


# =========================================================================
# Fig 6: Cross-scenario latency comparison
# =========================================================================
def plot_crossover(df, out):
    fig, ax = plt.subplots(figsize=(COL_W, 2.6))

    # Representative one-way delays (s)
    delays = np.logspace(-2, 3, 50)  # 10ms to 1000s

    # BGP: convergence = D * d (one-time), then 0 per query
    # DNS: query = 2 * D * d (per query)
    # For a "typical" diameter D ~ 8
    D = 8
    bgp_amortized_10 = D * delays / 10   # amortized over 10 queries
    dns_total_10 = 10 * 2 * D * delays

    ax.loglog(delays, D * delays, '-', color=C_BGP, label='BGP (one-time convergence)')
    ax.loglog(delays, 2 * D * delays, '--', color=C_DNS, label='DNS (per-query RTT)')

    # Mark scenario regions
    ax.axvspan(0.005, 0.05, alpha=0.1, color='green')
    ax.axvspan(0.5, 2, alpha=0.1, color='orange')
    ax.axvspan(100, 1000, alpha=0.1, color='red')

    ax.text(0.015, 0.3, 'Terrestrial', fontsize=7, rotation=90, va='bottom', color='green')
    ax.text(0.8, 0.3, 'Lunar', fontsize=7, rotation=90, va='bottom', color='orange')
    ax.text(300, 0.3, 'Mars', fontsize=7, rotation=90, va='bottom', color='red')

    ax.set_xlabel('One-way link delay (s)')
    ax.set_ylabel('Time cost (s)')
    ax.legend(fontsize=7, loc='upper left')

    plt.tight_layout()
    save(out, 'fig_crossover')


# =========================================================================
# Table data helper: summary results
# =========================================================================
def print_summary_table(df):
    print("\n=== Summary Table Data (for LaTeX) ===\n")
    # Exp1 baseline
    for protocol in ['BGP', 'DNS']:
        p = df[(df['exp_num'] == 1) & (df['protocol'] == protocol)]
        m, _ = sum_per_run(p, 'messageBytesSent:sum')
        print(f"  Exp1 {protocol}: {m/1000:.1f} KB")

    # Exp2 scalability at 400 nodes
    for protocol in ['BGP', 'DNS']:
        p = df[(df['exp_num'] == 2) & (df['protocol'] == protocol) & (df['grid_size'] == '20x20')]
        m, _ = sum_per_run(p, 'messageBytesSent:sum')
        print(f"  Exp2 {protocol} (20x20): {m/1000:.1f} KB")

    # Exp4 latency
    for protocol in ['BGP', 'DNS']:
        p = df[(df['exp_num'] == 4) & (df['protocol'] == protocol)]
        gt = p[p['module'].str.contains('groundTruth')]
        conv = pd.to_numeric(gt[gt['name'] == 'avgConvergenceTime']['value'], errors='coerce').mean()
        cl = p[p['module'].str.contains(r'node\[99\]')]
        ql = pd.to_numeric(cl[cl['name'] == 'dnsQueryLatency:mean']['value'], errors='coerce').mean()
        dl = pd.to_numeric(cl[cl['name'] == 'discoveryLatency:mean']['value'], errors='coerce').mean()
        print(f"  Exp4 {protocol}: conv={conv:.3f}s  query_lat={ql:.3f}s  disc_lat={dl:.3f}s")


def main():
    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])
    else:
        csv_path = Path('results/experiments_latest.csv')

    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}")
        sys.exit(1)

    out = Path('plots/paper')
    out.mkdir(parents=True, exist_ok=True)

    print(f"Loading data from: {csv_path}")
    df = load_data(csv_path)
    print(f"Loaded {len(df)} records\n")

    print("Generating paper figures...")
    plot_scalability(df, out)
    plot_churn(df, out)
    plot_dns_analysis(df, out)
    plot_deepspace(df, out)
    plot_realistic(df, out)
    plot_crossover(df, out)

    print_summary_table(df)

    print(f"\nAll paper figures saved to: {out.absolute()}")


if __name__ == '__main__':
    main()
