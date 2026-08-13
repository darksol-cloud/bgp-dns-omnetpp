#!/usr/bin/env python3
"""
slide_plots.py - Generate presentation-sized figures for the WiSEE/STINT talk.

Same data as paper_plots.py, redrawn for a 16:9 slide: wide aspect, large fonts,
deck palette, and a background matching the Marp theme so the plots sit flat on
the slide.

Usage:
    python slide_plots.py [results/experiments_latest.csv] [results/exp14_latest.csv]

The Exp14 (intermittency) CSV is produced with:
    opp_scavetool export -o results/exp14_latest.csv -F CSV-S -T s results/Exp14_*.sca

Figures are written to plots/slides/ and are copied into doc/slides/figures/ for
the deck.
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Deck palette (see doc/slides/deck-*.md)
PAPER = '#fbfaf7'
INK = '#17202a'
MUTED = '#5b6570'
LINE = '#dfe5e8'
C_BGP = '#23395b'   # push
C_DNS = '#d96c55'   # pull
TEAL = '#0e7c7b'

matplotlib.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['DejaVu Sans'],
    'font.size': 15,
    'axes.labelsize': 15,
    'axes.titlesize': 17,
    'axes.titleweight': 'bold',
    'axes.labelcolor': INK,
    'axes.edgecolor': '#9aa5ac',
    'axes.facecolor': PAPER,
    'figure.facecolor': PAPER,
    'savefig.facecolor': PAPER,
    'text.color': INK,
    'xtick.color': MUTED,
    'ytick.color': MUTED,
    'xtick.labelsize': 13,
    'ytick.labelsize': 13,
    'legend.fontsize': 14,
    'legend.frameon': False,
    'lines.linewidth': 2.8,
    'lines.markersize': 9,
    'savefig.dpi': 200,
    'figure.dpi': 200,
})


def save(fig, out, name):
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / f'{name}.png', bbox_inches='tight', pad_inches=0.06)
    plt.close(fig)
    print(f'  {name}.png')


def tidy(ax):
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    ax.grid(True, axis='y', color=LINE, linewidth=1.0)
    ax.set_axisbelow(True)


def load(csv_path):
    df = pd.read_csv(csv_path, low_memory=False)
    df['cfg'] = df['run'].str.extract(r'^(Exp\d+_[A-Za-z0-9_]+)-')
    df['module'] = df['module'].astype(str)
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    return df


def total_bytes(sub, metric='messageBytesReceived:sum'):
    """Mean over runs of the network-wide byte count."""
    vals = []
    for _, rd in sub.groupby('run'):
        m = rd['module'].str.contains('node') & (rd['name'] == metric)
        vals.append(rd[m]['value'].sum())
    return float(np.mean(vals)) if vals else 0.0


def accuracy(sub, client=r'node\[99\]'):
    out = []
    for _, rd in sub.groupby('run'):
        s = rd[rd['module'].str.contains(client)]
        c = s[s['name'] == 'correctAnswers:sum']['value'].sum()
        st = s[s['name'] == 'staleAnswers:sum']['value'].sum()
        out.append(100 * c / (c + st) if c + st else np.nan)
    return float(np.nanmean(out)) if out else np.nan


# ---------------------------------------------------------------- scaling
def plot_scaling(df, out):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.4, 3.9))

    grids = ['5x5', '10x10', '15x15', '20x20']
    nodes = [25, 100, 225, 400]
    for proto, color, marker, label in [('Bgp', C_BGP, 'o', 'BGP (push)'),
                                        ('Dns', C_DNS, 's', 'DNS (pull)')]:
        y = [total_bytes(df[df['cfg'] == f'Exp2_Scale_{proto}_{g}']) / 1000 for g in grids]
        ax1.plot(nodes, y, marker=marker, color=color, label=label)
    ax1.set_yscale('log')
    ax1.set_xlabel('Nodes in the network')
    ax1.set_ylabel('Control traffic (KB)')
    ax1.set_title('Grows with the network')
    ax1.legend(loc='center right')
    ax1.text(390, 14000, '8.1 MB', ha='right', color=C_BGP,
             fontweight='bold', fontsize=14)
    ax1.text(200, 2.0, '8 KB, flat', color=C_DNS,
             fontweight='bold', fontsize=14)
    ax1.set_ylim(1, 60000)
    tidy(ax1)

    eids = [10, 50, 100, 200, 500]
    for proto, color, marker, label in [('Bgp', C_BGP, 'o', 'BGP (push)'),
                                        ('Dns', C_DNS, 's', 'DNS (pull)')]:
        sub = df[df['cfg'] == f'Exp3_Eids_{proto}']
        y = [total_bytes(sub[sub['M'].astype(str) == f'"1-{n}"']) / 1000 for n in eids]
        ax2.plot(eids, y, marker=marker, color=color, label=label)
    ax2.set_yscale('log')
    ax2.set_xlabel('Endpoint identifiers published')
    ax2.set_ylabel('Control traffic (KB)')
    ax2.set_title('...and with the namespace')
    ax2.text(490, 24000, '13.6 MB', ha='right', color=C_BGP,
             fontweight='bold', fontsize=14)
    ax2.set_ylim(1, 100000)
    tidy(ax2)

    fig.tight_layout()
    save(fig, out, 'slide_scaling')


# ------------------------------------------------------------------ churn
def plot_churn(df, out):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.4, 3.9))
    churn = [5, 10, 20, 60]

    for proto, color, marker, label in [('Bgp', C_BGP, 'o', 'BGP (push)'),
                                        ('Dns', C_DNS, 's', 'DNS (pull)')]:
        sub = df[df['cfg'] == f'Exp5_Churn_{proto}']
        y = [total_bytes(sub[sub['churnInt'] == c]) / 1000 for c in churn]
        ax1.plot(churn, y, marker=marker, color=color, label=label)
    ax1.set_yscale('log')
    ax1.invert_xaxis()
    ax1.set_xlabel('Seconds between binding changes')
    ax1.set_ylabel('Control traffic (KB)')
    ax1.set_title('Push pays for every change')
    ax1.legend(loc='upper left')
    ax1.text(9, 11000, '233$\\times$ DNS', ha='center', color=C_BGP,
             fontweight='bold', fontsize=14)
    ax1.set_ylim(8, 40000)
    tidy(ax1)

    for proto, color, marker, label in [('Bgp', C_BGP, 'o', 'BGP (push)'),
                                        ('Dns', C_DNS, 's', 'DNS (pull)')]:
        sub = df[df['cfg'] == f'Exp5_Churn_{proto}']
        y = [accuracy(sub[sub['churnInt'] == c]) for c in churn]
        ax2.plot(churn, y, marker=marker, color=color, label=label)
    ax2.invert_xaxis()
    ax2.set_ylim(0, 108)
    ax2.set_xlabel('Seconds between binding changes')
    ax2.set_ylabel('Answers that are correct (%)')
    ax2.set_title('Pull answers go stale')
    ax2.annotate('always right', xy=(20, 100), xytext=(45, 86),
                 color=C_BGP, fontweight='bold', fontsize=14)
    ax2.annotate('1 in 3 correct\n(TTL 60 s)', xy=(5, 33), xytext=(14, 12),
                 color=C_DNS, fontweight='bold', fontsize=14)
    tidy(ax2)

    fig.tight_layout()
    save(fig, out, 'slide_churn')


# ------------------------------------------------------------- deep space
def plot_delay(df, out):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.4, 3.9))

    delays = [0.01, 0.1, 1, 5, 10, 20]
    conv, lat = [], []
    for d in delays:
        b = df[(df['cfg'] == 'Exp8_DeepSpace_Bgp') & (df['delay'] == d)]
        gt = b[b['module'].str.contains('groundTruth')]
        v = gt[gt['name'] == 'avgInitialConvergenceTime']['value'].mean()
        if np.isnan(v):
            v = gt[gt['name'] == 'avgConvergenceTime']['value'].mean()
        conv.append(v)
        n = df[(df['cfg'] == 'Exp8_DeepSpace_Dns') & (df['delay'] == d)]
        cl = n[n['module'].str.contains(r'node\[24\]')]
        lat.append(cl[cl['name'] == 'dnsQueryLatency:mean']['value'].mean())

    ax1.plot(delays, conv, 'o-', color=C_BGP, label='BGP: converge once')
    ax1.plot(delays, lat, 's-', color=C_DNS, label='DNS: every query')
    ax1.set_xscale('log')
    ax1.set_yscale('log')
    ax1.set_xlabel('One-way link delay (s)')
    ax1.set_ylabel('Time to an answer (s)')
    ax1.set_title('Both scale with delay')
    ax1.legend(loc='upper left')
    tidy(ax1)

    q = np.arange(0, 11)
    ax2.plot(q, np.full_like(q, 160, dtype=float), '-', color=C_BGP,
             label='BGP: 160 s, once')
    ax2.plot(q, q * 400.0, '-', color=C_DNS, label='DNS: 400 s per query')
    ax2.fill_between(q, np.full_like(q, 160, dtype=float), q * 400.0,
                     where=(q * 400.0 > 160), alpha=0.13, color=C_DNS)
    ax2.axvline(0.4, color=MUTED, linestyle=':', linewidth=2)
    ax2.text(0.75, 300, 'break-even:\nless than one query',
             color=MUTED, fontsize=14)
    ax2.set_xlabel('Number of resolutions')
    ax2.set_ylabel('Cumulative wait (s)')
    ax2.set_title('At 20 s links, push wins immediately')
    ax2.legend(loc='upper left')
    tidy(ax2)

    fig.tight_layout()
    save(fig, out, 'slide_delay')


# -------------------------------------------------------------- scenarios
def plot_scenarios(df, out):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.4, 3.9))
    labels = ['Terrestrial\n5-30 ms', 'Lunar\n1.3 s', 'Mars\n12 min']

    # Overhead, as reported in the paper (single representative configuration).
    bgp_kb = [212.8, 23.8, 18.0]
    dns_kb = [16.4, 6.3, 5.3]
    x = np.arange(3)
    w = 0.36
    ax1.bar(x - w / 2, bgp_kb, w, color=C_BGP, label='BGP (push)')
    ax1.bar(x + w / 2, dns_kb, w, color=C_DNS, label='DNS (pull)')
    for i, (b, d) in enumerate(zip(bgp_kb, dns_kb)):
        ax1.text(i, max(b, d) + 16, f'{b / d:.1f}$\\times$'.replace('13.0', '13'),
                 ha='center', color=INK, fontweight='bold', fontsize=14)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels)
    ax1.set_ylabel('Control traffic (KB)')
    ax1.set_ylim(0, 260)
    ax1.set_title('Pull always costs less bandwidth')
    ax1.legend(loc='upper right')
    tidy(ax1)

    # Per-query resolution latency for pull (measured at the querying nodes).
    lat = [0.188, 2.8, 1500.0]
    ax2.bar(x, lat, 0.5, color=C_DNS)
    ax2.set_yscale('log')
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels)
    ax2.set_ylabel('Seconds per resolution')
    ax2.set_ylim(0.05, 20000)
    ax2.set_title('...and that stops mattering')
    for i, v in enumerate(lat):
        txt = '188 ms' if v < 1 else ('2.8 s' if v < 60 else '25 min')
        ax2.text(i, v * 1.5, txt, ha='center', color=INK,
                 fontweight='bold', fontsize=14)
    ax2.axhline(1.0, color=TEAL, linestyle='--', linewidth=2)
    ax2.text(-0.45, 1.4, 'human-scale', color=TEAL, fontsize=13,
             ha='left', fontweight='bold')
    tidy(ax2)

    fig.tight_layout()
    save(fig, out, 'slide_scenarios')


# ----------------------------------------------------------- intermittency
def plot_intermittency(csv_path, out):
    if not Path(csv_path).exists():
        print(f'  (skipped intermittency: {csv_path} not found)')
        return
    df = load(csv_path)
    sub = df[(df['cfg'] == 'Exp14_Lunar_Int_Dns') &
             (df['name'] == 'dnsQueryLatency:mean') &
             (df['module'].str.contains(r'earthDsn|rover\[1\]'))]
    duties, lats = [], []
    for duty, g in sub.groupby('duty'):
        duties.append(float(duty))
        lats.append(g['value'].mean())
    order = np.argsort(duties)
    duties = np.array(duties)[order]
    lats = np.array(lats)[order]

    fig, ax = plt.subplots(figsize=(7.6, 3.9))
    ax.plot(duties * 100, lats, 's-', color=C_DNS, label='DNS: per Earth-involved query')
    ax.axhline(1.6, color=C_BGP, linewidth=2.8, label='BGP: one-time convergence')
    ax.axhline(2.9, color=C_DNS, linestyle=':', linewidth=2)
    ax.text(48, 2.0, 'always-on baseline: 2.9 s', color=MUTED, fontsize=13, ha='center')
    ax.set_yscale('log')
    ax.set_xlabel('Trunk duty cycle (% of the time the link is up)')
    ax.set_ylabel('Seconds')
    ax.set_title('A scheduled trunk punishes pull, not push')
    ax.legend(loc='upper right')
    ax.text(27, 6.5, f'{lats[0] / 2.9:.0f}$\\times$ slower than an always-on trunk',
            color=C_DNS, fontweight='bold', fontsize=14)
    tidy(ax)
    fig.tight_layout()
    save(fig, out, 'slide_intermittency')


def main():
    csv = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('results/experiments_latest.csv')
    csv14 = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('results/exp14_latest.csv')
    out = Path('plots/slides')

    print(f'Loading {csv}')
    df = load(csv)
    print('Generating slide figures...')
    plot_scaling(df, out)
    plot_churn(df, out)
    plot_delay(df, out)
    plot_scenarios(df, out)
    plot_intermittency(csv14, out)
    print(f'\nWritten to {out.absolute()}')


if __name__ == '__main__':
    main()
