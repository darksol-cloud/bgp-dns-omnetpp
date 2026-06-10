#!/usr/bin/env python3
"""
intermittency_plots.py - Figure for Experiment 14 (link intermittency, journal version)

Usage:
    python intermittency_plots.py [exp14.csv]

Reads the CSV-S export of the Exp14_* result files and produces
plots/fig_intermittent.pdf: mean DNS query latency vs. trunk duty cycle for the
lunar and Mars scenarios, with the first-order waiting-time model overlaid.
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

CSV = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/tmp/exp14.csv')

# Scenario parameters (must match experiments.ini Exp14 configs)
SCEN = {
    'Lunar': {
        'config': 'Exp14_Lunar_Int_Dns',
        'period': 600.0,
        'earth_nodes': ['LunarArtemisNetwork.earthDsn', 'LunarArtemisNetwork.rover[1]'],
        'local_nodes': ['LunarArtemisNetwork.gateway', 'LunarArtemisNetwork.rover[0]'],
        'base_rtt': (2.6 + 3.12) / 2,   # mean Earth-involved RTT at duty 1
        'local_rtt': (0.14 + 0.69) / 2,
        'bgp_conv': 1.6,                # one-time convergence (Exp12)
    },
    'Mars': {
        'config': 'Exp14_Mars_Int_Dns',
        'period': 1800.0,
        'earth_nodes': ['MarsExplorationNetwork.earthDsn', 'MarsExplorationNetwork.rover[1]'],
        'local_nodes': ['MarsExplorationNetwork.rover[0]', 'MarsExplorationNetwork.jezeroHabitat'],
        'base_rtt': (1440 + 1570) / 2,
        'local_rtt': (192.4 + 200) / 2,
        'bgp_conv': 120.0,              # one-time convergence (Exp13)
    },
}


def main():
    df = pd.read_csv(CSV)
    df['config'] = df['run'].str.split('-').str[0]
    lat = df[df['name'] == 'dnsQueryLatency:mean'].dropna(subset=['value'])

    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4))

    for ax, (name, p) in zip(axes, SCEN.items()):
        sub = lat[lat['config'] == p['config']]

        duties = [0.25, 0.5, 0.75, 1.0]
        earth_mean, earth_std, local_mean = [], [], []
        for d in duties:
            if d == 1.0:
                earth_mean.append(p['base_rtt'])
                earth_std.append(0)
                local_mean.append(p['local_rtt'])
            else:
                e = sub[(sub['duty'] == d) & (sub['module'].isin(p['earth_nodes']))]['value']
                l = sub[(sub['duty'] == d) & (sub['module'].isin(p['local_nodes']))]['value']
                earth_mean.append(e.mean())
                earth_std.append(e.std())
                local_mean.append(l.mean())

        ax.errorbar(duties, earth_mean, yerr=earth_std, marker='o', color='tab:red',
                    label='DNS, Earth-involved (measured)', zorder=3)
        ax.plot(duties, local_mean, marker='s', color='tab:blue',
                label='DNS, local (measured)')

        # First-order model: L = RTT + E[W], E[W] = (1-duty)^2 * period / 2
        dd = np.linspace(0.2, 1.0, 100)
        model = p['base_rtt'] + (1 - dd) ** 2 * p['period'] / 2
        ax.plot(dd, model, '--', color='tab:red', alpha=0.6,
                label=r'Model: RTT + $(1{-}\delta)^2 P/2$')

        ax.axhline(p['bgp_conv'], color='tab:green', linestyle=':',
                   label='BGP convergence (one-time)')

        ax.set_yscale('log')
        ax.set_xlabel(r'Trunk duty cycle $\delta$')
        ax.set_ylabel('Mean query latency (s)')
        ax.set_title(f'({chr(97 + list(SCEN).index(name))}) {name} '
                     f'(P = {int(p["period"])} s)')
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7, loc='best')

    fig.tight_layout()
    out = Path('plots/fig_intermittent.pdf')
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, bbox_inches='tight')
    fig.savefig(out.with_suffix('.png'), dpi=150, bbox_inches='tight')
    print(f'wrote {out}')

    # Console summary for the paper text
    for name, p in SCEN.items():
        sub = lat[lat['config'] == p['config']]
        print(f'--- {name}')
        for d in [0.25, 0.5, 0.75]:
            e = sub[(sub['duty'] == d) & (sub['module'].isin(p['earth_nodes']))]['value'].mean()
            print(f'  duty {d}: earth-involved mean {e:.1f} s '
                  f'({e / p["base_rtt"]:.1f}x the always-on RTT)')


if __name__ == '__main__':
    main()
