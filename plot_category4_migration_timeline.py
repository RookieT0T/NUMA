#!/usr/bin/env python3
"""
Test Category 4 - Script 1: Migration Timeline
Shows page distribution changing over time (Initial → Mid → Final)
"""

import os
import re
import matplotlib.pyplot as plt
import numpy as np

RESULTS_DIR = "numa_results_advanced/Test4"

def parse_migration_data(filepath):
    """Extract page distribution timeline from migration test output"""
    try:
        with open(filepath, 'r') as f:
            content = f.read()

        # Extract distributions
        initial_match = re.search(r'Initial distribution: Node0=(\d+)%, Node1=(\d+)%', content)
        mid_match = re.search(r'Mid-execution distribution: Node0=(\d+)%, Node1=(\d+)%', content)
        final_match = re.search(r'Final distribution: Node0=(\d+)%, Node1=(\d+)%', content)

        if initial_match and mid_match and final_match:
            return {
                'initial': {'node0': int(initial_match.group(1)), 'node1': int(initial_match.group(2))},
                'mid': {'node0': int(mid_match.group(1)), 'node1': int(mid_match.group(2))},
                'final': {'node0': int(final_match.group(1)), 'node1': int(final_match.group(2))}
            }
    except:
        pass

    return None

def collect_timeline_data():
    """Collect timeline data for auto-NUMA and pressure-induced tests"""
    data = {
        'auto_numa': {},      # {size: {pattern: timeline_data}}
        'pressure': {}         # {size: {pattern: timeline_data}}
    }

    for filename in sorted(os.listdir(RESULTS_DIR)):
        # Parse auto-NUMA files
        match = re.match(r'auto_numa_(\d+)MB_(sequential|random|stride)\.txt', filename)
        if match:
            size_mb = int(match.group(1))
            pattern = match.group(2)

            filepath = os.path.join(RESULTS_DIR, filename)
            timeline = parse_migration_data(filepath)

            if timeline:
                if size_mb not in data['auto_numa']:
                    data['auto_numa'][size_mb] = {}
                data['auto_numa'][size_mb][pattern] = timeline

        # Parse pressure-induced files
        match = re.match(r'pressure_migration_(\d+)MB_(sequential|random|stride)\.txt', filename)
        if match:
            size_mb = int(match.group(1))
            pattern = match.group(2)

            filepath = os.path.join(RESULTS_DIR, filename)
            timeline = parse_migration_data(filepath)

            if timeline:
                if size_mb not in data['pressure']:
                    data['pressure'][size_mb] = {}
                data['pressure'][size_mb][pattern] = timeline

    return data

def plot_migration_timeline():
    """Create migration timeline visualization"""
    data = collect_timeline_data()

    # Create figure with subplots for auto-NUMA and pressure-induced
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))

    test_types = [('auto_numa', 'Auto-NUMA Migration', axes[0]),
                  ('pressure', 'Pressure-Induced Migration', axes[1])]

    for test_type, title, ax in test_types:
        if not data[test_type]:
            ax.text(0.5, 0.5, 'No data available', ha='center', va='center',
                   transform=ax.transAxes, fontsize=12)
            ax.set_title(title, fontsize=14, fontweight='bold')
            continue

        # Use a representative size (e.g., 1024MB) and pattern (sequential)
        representative_size = 1024
        representative_pattern = 'sequential'

        if representative_size in data[test_type] and representative_pattern in data[test_type][representative_size]:
            timeline = data[test_type][representative_size][representative_pattern]

            # Prepare data for stacked area chart
            phases = ['Initial', 'Mid-Execution', 'Final']
            node0_percentages = [timeline['initial']['node0'],
                                timeline['mid']['node0'],
                                timeline['final']['node0']]
            node1_percentages = [timeline['initial']['node1'],
                                timeline['mid']['node1'],
                                timeline['final']['node1']]

            x = np.arange(len(phases))
            width = 0.6

            # Create stacked bar chart
            ax.bar(x, node0_percentages, width, label='Node 0', color='#2ca02c', alpha=0.8)
            ax.bar(x, node1_percentages, width, bottom=node0_percentages,
                  label='Node 1', color='#ff7f0e', alpha=0.8)

            # Add percentage labels on bars
            for i, (n0, n1) in enumerate(zip(node0_percentages, node1_percentages)):
                if n0 > 0:
                    ax.text(i, n0/2, f'{n0}%', ha='center', va='center',
                           fontweight='bold', fontsize=11, color='white')
                if n1 > 0:
                    ax.text(i, n0 + n1/2, f'{n1}%', ha='center', va='center',
                           fontweight='bold', fontsize=11, color='white')

            ax.set_xlabel('Execution Phase', fontsize=12, fontweight='bold')
            ax.set_ylabel('Page Distribution (%)', fontsize=12, fontweight='bold')
            ax.set_title(f'{title}\n({representative_size}MB, {representative_pattern} access)',
                        fontsize=14, fontweight='bold')
            ax.set_xticks(x)
            ax.set_xticklabels(phases)
            ax.set_ylim(0, 100)
            ax.legend(fontsize=11, loc='upper right')
            ax.grid(True, alpha=0.3, axis='y')

            # Add migration arrow annotation
            if node0_percentages[0] != node0_percentages[-1]:
                migration_amount = node0_percentages[-1] - node0_percentages[0]
                arrow_text = f'Migration:\n{abs(migration_amount)}% to Node {"0" if migration_amount > 0 else "1"}'
                ax.annotate(arrow_text, xy=(2, 50), xytext=(0.5, 50),
                           arrowprops=dict(arrowstyle='->', color='red', lw=2),
                           fontsize=10, fontweight='bold', color='red',
                           bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='red'))

    plt.tight_layout()
    plt.savefig('category4_migration_timeline.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: category4_migration_timeline.png")
    plt.show()

    # Print summary
    print("\n=== Migration Timeline Summary ===")
    for test_type in ['auto_numa', 'pressure']:
        if data[test_type]:
            print(f"\n{test_type.upper().replace('_', ' ')}:")
            for size in sorted(data[test_type].keys()):
                for pattern in data[test_type][size]:
                    timeline = data[test_type][size][pattern]
                    print(f"  {size}MB {pattern}: Node0 {timeline['initial']['node0']}% → "
                          f"{timeline['mid']['node0']}% → {timeline['final']['node0']}%")

if __name__ == '__main__':
    plot_migration_timeline()
