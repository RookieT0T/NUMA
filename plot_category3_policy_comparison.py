#!/usr/bin/env python3
"""
Test Category 3 - Experiment 1: Policy Performance Comparison
Compare interleave, localalloc, membind, and preferred policies
"""

import os
import re
import matplotlib.pyplot as plt
import numpy as np

RESULTS_DIR = "numa_results_advanced/Test3"

def parse_result_file(filepath):
    """Extract throughput from result file"""
    try:
        with open(filepath, 'r') as f:
            content = f.read()

        throughput_match = re.search(r'Throughput:\s+([\d.]+)\s+MB/s', content)
        return float(throughput_match.group(1)) if throughput_match else None
    except:
        return None

def collect_data():
    """Collect data for different policies"""
    data = {}  # {size: {pattern: {policy: throughput}}}

    for filename in sorted(os.listdir(RESULTS_DIR)):
        # Parse filenames: interleave_all_512MB_sequential.txt, localalloc_node0_512MB_sequential.txt, etc.
        patterns = [
            (r'interleave_all_(\d+)MB_(sequential|random|stride)\.txt', 'interleave'),
            (r'wt_interleave_all_(\d+)MB_(sequential|random|stride)\.txt', 'wt-interleave'),
            (r'localalloc_node0_(\d+)MB_(sequential|random|stride)\.txt', 'localalloc'),
            (r'membind_strict_node0_(\d+)MB_(sequential|random|stride)\.txt', 'membind'),
            (r'preferred_node0_cpu_node1_(\d+)MB_(sequential|random|stride)\.txt', 'preferred'),
        ]

        for pattern_regex, policy_name in patterns:
            match = re.match(pattern_regex, filename)
            if match:
                size_mb = int(match.group(1))
                access_pattern = match.group(2)

                filepath = os.path.join(RESULTS_DIR, filename)
                throughput = parse_result_file(filepath)

                if throughput is not None:
                    if size_mb not in data:
                        data[size_mb] = {}
                    if access_pattern not in data[size_mb]:
                        data[size_mb][access_pattern] = {}
                    data[size_mb][access_pattern][policy_name] = throughput

    return data

def format_size_label(size_mb):
    """Convert MB to GB if >= 1024 MB for clearer labels"""
    if size_mb >= 1024:
        return f'{size_mb // 1024} GB'
    else:
        return f'{size_mb} MB'

def plot_policy_comparison():
    """Create policy comparison plots"""
    data = collect_data()
    sizes = sorted(data.keys())
    patterns = ['sequential', 'random', 'stride']
    policies = ['interleave', 'wt-interleave', 'localalloc', 'membind', 'preferred']

    colors = {
        'interleave': '#1f77b4',
        'wt-interleave': '#000000',
        'localalloc': '#2ca02c',
        'membind': '#d62728',
        'preferred': '#ff7f0e'
    }

    # Better labels for policies with clarification
    policy_labels = {
        'interleave': 'Interleave',
        'wt-interleave': 'Weighted Interleave',
        'localalloc': 'Local Alloc',
        'membind': 'Membind',
        'preferred': 'Preferred (CPU≠Mem)'  # Clarify CPU and memory are on different nodes
    }

    # Create subplots for each access pattern
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    for ax, pattern in zip(axes, patterns):
        # Use discrete x positions for categorical labels (same as Category 2)
        x = np.arange(len(sizes))

        for policy in policies:
            policy_data = []
            for size in sizes:
                if pattern in data[size] and policy in data[size][pattern]:
                    policy_data.append(data[size][pattern][policy])
                else:
                    policy_data.append(None)

            # Plot using discrete x positions
            if any(d is not None for d in policy_data):
                # Replace None with NaN for plotting
                plot_data = [d if d is not None else np.nan for d in policy_data]
                ax.plot(x, plot_data, 'o-', linewidth=2, markersize=8,
                       label=policy_labels[policy], color=colors[policy])

        ax.set_xlabel('Memory Size', fontsize=11, fontweight='bold')
        ax.set_ylabel('Throughput (MB/s)', fontsize=11, fontweight='bold')
        ax.set_title(f'{pattern.capitalize()} Access', fontsize=12, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels([format_size_label(s) for s in sizes], rotation=45, ha='right')
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)

    plt.suptitle('NUMA Policy Performance Comparison',
                 fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig('category3_policy_comparison.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: category3_policy_comparison.png")
    plt.show()

if __name__ == '__main__':
    plot_policy_comparison()
