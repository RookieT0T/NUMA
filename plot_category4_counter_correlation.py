#!/usr/bin/env python3
"""
Test Category 4 - Script 3: Counter Correlation
Correlate migration events (from vmstat) with performance metrics
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

def parse_vmstat_delta(filepath):
    """Extract migration counters from vmstat before/after files"""
    try:
        vmstat_before = {}
        vmstat_after = {}

        # Read before
        with open(filepath + '.vmstat_before', 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) == 2:
                    vmstat_before[parts[0]] = int(parts[1])

        # Read after
        with open(filepath + '.vmstat_after', 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) == 2:
                    vmstat_after[parts[0]] = int(parts[1])

        # Calculate deltas
        deltas = {}
        for key in vmstat_after:
            if key in vmstat_before:
                deltas[key] = vmstat_after[key] - vmstat_before[key]

        return deltas
    except:
        return {}

def collect_correlation_data():
    """Collect data correlating migration events with performance"""
    data = []  # List of {scenario, size, throughput, numa_pages_migrated, numa_pte_updates}

    for filename in sorted(os.listdir(RESULTS_DIR)):
        # Parse all migration test files
        match = re.match(r'(auto_numa|pressure_migration|auto_migrated)_(\d+)MB(?:_(\w+))?\.txt', filename)
        if match:
            test_type = match.group(1)
            size_mb = int(match.group(2))
            pattern = match.group(3) if match.group(3) else 'sequential'

            filepath = os.path.join(RESULTS_DIR, filename)
            throughput = parse_throughput(filepath)
            vmstat_deltas = parse_vmstat_delta(filepath)

            if throughput is not None and vmstat_deltas:
                data.append({
                    'scenario': f'{test_type}\n{size_mb}MB\n{pattern}',
                    'scenario_short': f'{test_type[:6]}_{size_mb}',
                    'size': size_mb,
                    'test_type': test_type,
                    'throughput': throughput,
                    'numa_pages_migrated': vmstat_deltas.get('numa_pages_migrated', 0),
                    'numa_pte_updates': vmstat_deltas.get('numa_pte_updates', 0),
                    'pgmigrate_success': vmstat_deltas.get('pgmigrate_success', 0)
                })

    return data

def plot_counter_correlation():
    """Create counter correlation dual-axis plot"""
    data = collect_correlation_data()

    if not data:
        print("No data found for counter correlation analysis")
        return

    # Sort by test type and size for better visualization
    data_sorted = sorted(data, key=lambda x: (x['test_type'], x['size']))

    # Limit to reasonable number of scenarios for readability
    if len(data_sorted) > 15:
        # Take a subset: auto-numa and auto-migrated for each size
        data_sorted = [d for d in data_sorted if 'auto' in d['test_type']][:15]

    fig, ax1 = plt.subplots(figsize=(16, 7))

    x = np.arange(len(data_sorted))
    scenarios = [d['scenario_short'] for d in data_sorted]

    # Plot migration events on left y-axis
    color = 'tab:red'
    ax1.set_xlabel('Test Scenario', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Pages Migrated', fontsize=12, fontweight='bold', color=color)
    bars1 = ax1.bar(x - 0.2, [d['numa_pages_migrated'] for d in data_sorted],
                     width=0.4, label='Pages Migrated', color=color, alpha=0.7)
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.set_xticks(x)
    ax1.set_xticklabels(scenarios, rotation=45, ha='right', fontsize=9)
    ax1.grid(True, alpha=0.3, axis='y')

    # Plot throughput on right y-axis
    ax2 = ax1.twinx()
    color = 'tab:blue'
    ax2.set_ylabel('Throughput (MB/s)', fontsize=12, fontweight='bold', color=color)
    bars2 = ax2.bar(x + 0.2, [d['throughput'] for d in data_sorted],
                     width=0.4, label='Throughput', color=color, alpha=0.7)
    ax2.tick_params(axis='y', labelcolor=color)

    # Title and legend
    plt.title('Migration Activity vs Performance\n(Correlation between page migration and throughput)',
             fontsize=14, fontweight='bold', pad=20)

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=10)

    plt.tight_layout()
    plt.savefig('category4_counter_correlation.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: category4_counter_correlation.png")
    plt.show()

    # Print correlation analysis
    print("\n=== Counter Correlation Analysis ===")
    print("\nScenario                           | Pages Migrated | PTE Updates | Throughput | Migration/Perf Ratio")
    print("-" * 105)

    for d in data_sorted:
        ratio = d['numa_pages_migrated'] / d['throughput'] if d['throughput'] > 0 else 0
        print(f"{d['scenario_short']:35s} | {d['numa_pages_migrated']:14d} | "
              f"{d['numa_pte_updates']:11d} | {d['throughput']:10.1f} | {ratio:20.2f}")

    # Calculate correlation coefficient
    if len(data_sorted) > 3:
        migrations = np.array([d['numa_pages_migrated'] for d in data_sorted])
        throughputs = np.array([d['throughput'] for d in data_sorted])

        if np.std(migrations) > 0 and np.std(throughputs) > 0:
            correlation = np.corrcoef(migrations, throughputs)[0, 1]
            print(f"\nPearson Correlation Coefficient: {correlation:.3f}")

            if correlation > 0.5:
                print("→ POSITIVE correlation: More migration → Better performance")
            elif correlation < -0.5:
                print("→ NEGATIVE correlation: More migration → Worse performance (overhead dominates)")
            else:
                print("→ WEAK correlation: Migration impact varies by scenario")

if __name__ == '__main__':
    plot_counter_correlation()
