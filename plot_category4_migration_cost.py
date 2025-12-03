#!/usr/bin/env python3
"""
Test Category 4 - Script 2: Migration Cost Analysis
Compare performance: local vs static-remote vs auto-migrated
"""

import os
import re
import matplotlib.pyplot as plt
import numpy as np

RESULTS_DIR = "numa_results_advanced/Test4"

def parse_throughput(filepath):
    """Extract throughput from result file"""
    try:
        with open(filepath, 'r') as f:
            content = f.read()

        throughput_match = re.search(r'Throughput:\s+([\d.]+)\s+MB/s', content)
        return float(throughput_match.group(1)) if throughput_match else None
    except:
        return None

def collect_cost_data():
    """Collect data for migration cost comparison"""
    data = {}  # {size: {'baseline': X, 'static_remote': Y, 'auto_migrated': Z}}

    for filename in sorted(os.listdir(RESULTS_DIR)):
        # Parse baseline local files
        match = re.match(r'baseline_local_(\d+)MB\.txt', filename)
        if match:
            size_mb = int(match.group(1))
            filepath = os.path.join(RESULTS_DIR, filename)
            throughput = parse_throughput(filepath)

            if throughput is not None:
                if size_mb not in data:
                    data[size_mb] = {}
                data[size_mb]['baseline'] = throughput

        # Parse static remote files
        match = re.match(r'static_remote_(\d+)MB\.txt', filename)
        if match:
            size_mb = int(match.group(1))
            filepath = os.path.join(RESULTS_DIR, filename)
            throughput = parse_throughput(filepath)

            if throughput is not None:
                if size_mb not in data:
                    data[size_mb] = {}
                data[size_mb]['static_remote'] = throughput

        # Parse auto-migrated files
        match = re.match(r'auto_migrated_(\d+)MB\.txt', filename)
        if match:
            size_mb = int(match.group(1))
            filepath = os.path.join(RESULTS_DIR, filename)
            throughput = parse_throughput(filepath)

            if throughput is not None:
                if size_mb not in data:
                    data[size_mb] = {}
                data[size_mb]['auto_migrated'] = throughput

    return data

def format_size_label(size_mb):
    """Convert MB to GB if >= 1024 MB for clearer labels"""
    if size_mb >= 1024:
        return f'{size_mb // 1024} GB'
    else:
        return f'{size_mb} MB'

def plot_migration_cost():
    """Create migration cost comparison bar chart"""
    data = collect_cost_data()
    sizes = sorted(data.keys())

    if not sizes:
        print("No data found for migration cost analysis")
        return

    fig, ax = plt.subplots(figsize=(12, 7))

    x = np.arange(len(sizes))
    width = 0.25

    baseline_perf = []
    static_remote_perf = []
    auto_migrated_perf = []

    for size in sizes:
        baseline_perf.append(data[size].get('baseline', 0))
        static_remote_perf.append(data[size].get('static_remote', 0))
        auto_migrated_perf.append(data[size].get('auto_migrated', 0))

    # Plot bars
    ax.bar(x - width, baseline_perf, width, label='Baseline Local (Best Case)',
           color='#2ca02c', alpha=0.8)
    ax.bar(x, static_remote_perf, width, label='Static Remote (No Migration)',
           color='#d62728', alpha=0.8)
    ax.bar(x + width, auto_migrated_perf, width, label='Auto-Migrated (Kernel Optimization)',
           color='#1f77b4', alpha=0.8)

    # Add value labels on bars
    for i in range(len(sizes)):
        if baseline_perf[i] > 0:
            ax.text(i - width, baseline_perf[i], f'{baseline_perf[i]:.0f}',
                   ha='center', va='bottom', fontsize=8, fontweight='bold')
        if static_remote_perf[i] > 0:
            ax.text(i, static_remote_perf[i], f'{static_remote_perf[i]:.0f}',
                   ha='center', va='bottom', fontsize=8, fontweight='bold')
        if auto_migrated_perf[i] > 0:
            ax.text(i + width, auto_migrated_perf[i], f'{auto_migrated_perf[i]:.0f}',
                   ha='center', va='bottom', fontsize=8, fontweight='bold')

    ax.set_xlabel('Memory Size', fontsize=12, fontweight='bold')
    ax.set_ylabel('Throughput (MB/s)', fontsize=12, fontweight='bold')
    ax.set_title('Migration Cost Analysis: Is Migration Worth It?',
                fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([format_size_label(s) for s in sizes])
    ax.legend(fontsize=10, loc='upper right')
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig('category4_migration_cost.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: category4_migration_cost.png")
    plt.show()

    # Print analysis
    print("\n=== Migration Cost Analysis ===")
    for size in sizes:
        baseline = data[size].get('baseline', 0)
        static_remote = data[size].get('static_remote', 0)
        auto_migrated = data[size].get('auto_migrated', 0)

        if baseline > 0 and static_remote > 0 and auto_migrated > 0:
            remote_penalty = ((baseline - static_remote) / baseline) * 100
            migration_benefit = ((auto_migrated - static_remote) / static_remote) * 100
            migration_efficiency = (auto_migrated / baseline) * 100

            print(f"\n{format_size_label(size)}:")
            print(f"  Baseline Local:      {baseline:.1f} MB/s")
            print(f"  Static Remote:       {static_remote:.1f} MB/s (- {remote_penalty:.1f}% penalty)")
            print(f"  Auto-Migrated:       {auto_migrated:.1f} MB/s")
            print(f"  Migration Benefit:   +{migration_benefit:.1f}% over static remote")
            print(f"  Migration Efficiency: {migration_efficiency:.1f}% of baseline")

            if migration_efficiency > 90:
                print(f"  → Migration is HIGHLY EFFECTIVE (recovered >{migration_efficiency-100:.0f}% of penalty)")
            elif migration_efficiency > 70:
                print(f"  → Migration is MODERATELY EFFECTIVE")
            else:
                print(f"  → Migration has LIMITED BENEFIT")

if __name__ == '__main__':
    plot_migration_cost()
