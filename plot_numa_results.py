#!/usr/bin/env python3
"""
NUMA Performance Visualization Script
Parses NUMA test results and generates bandwidth and latency graphs.
"""

import os
import re
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict
from pathlib import Path

# Color scheme for different policies
COLORS = {
    'membind_node0': '#1f77b4',      # blue
    'local_node0': '#ff7f0e',         # orange
    'interleave_all': '#2ca02c',      # green
    'localalloc_node0': '#d62728',    # red
    'membind_strict': '#9467bd',      # purple
    'preferred_node0': '#8c564b',     # brown
    'preferred_node1': '#e377c2',     # pink
}

# Marker styles for different policies
MARKERS = {
    'membind_node0': 'o',
    'local_node0': 's',
    'interleave_all': '^',
    'localalloc_node0': 'D',
    'membind_strict': 'v',
    'preferred_node0': 'p',
    'preferred_node1': '*',
}


def parse_result_file(filepath):
    """
    Parse a single result file and extract throughput and latency.

    Returns:
        dict: {'throughput': float, 'latency': float, 'accesses': int}
    """
    with open(filepath, 'r') as f:
        content = f.read()

    result = {}

    # Extract throughput (MB/s)
    throughput_match = re.search(r'Throughput:\s+([\d.]+)\s+MB/s', content)
    if throughput_match:
        result['throughput'] = float(throughput_match.group(1))

    # Extract latency (ns)
    latency_match = re.search(r'Average latency:\s+([\d.]+)\s+ns per access', content)
    if latency_match:
        result['latency'] = float(latency_match.group(1))

    # Extract number of accesses
    accesses_match = re.search(r'\((\d+)\s+(?:random|strided)\s+accesses\)', content)
    if accesses_match:
        result['accesses'] = int(accesses_match.group(1))

    return result


def extract_info_from_filename(filename):
    """
    Extract policy, size (MB), and access pattern from filename.

    Example: membind_node0_1024MB_random.txt
    Returns: ('membind_node0', 1024, 'random')
    """
    # Remove .txt extension
    name = filename.replace('.txt', '')

    # Extract size in MB
    size_match = re.search(r'(\d+)MB', name)
    if not size_match:
        return None, None, None

    size_mb = int(size_match.group(1))

    # Extract access pattern (last component)
    parts = name.split('_')
    access_pattern = parts[-1]

    # Extract policy (everything before size)
    policy_end = name.find(f'{size_mb}MB')
    policy = name[:policy_end].rstrip('_')

    return policy, size_mb, access_pattern


def load_test_category_data(category_path):
    """
    Load all data from a test category directory.

    Returns:
        dict: {access_pattern: {policy: [(size_mb, throughput, latency), ...]}}
    """
    data = defaultdict(lambda: defaultdict(list))

    category_dir = Path(category_path)
    if not category_dir.exists():
        print(f"Warning: Directory {category_path} does not exist")
        return data

    for filepath in category_dir.glob('*.txt'):
        policy, size_mb, access_pattern = extract_info_from_filename(filepath.name)

        if policy is None:
            continue

        result = parse_result_file(filepath)

        if 'throughput' in result and 'latency' in result:
            data[access_pattern][policy].append(
                (size_mb, result['throughput'], result['latency'])
            )

    # Sort each policy's data by size
    for access_pattern in data:
        for policy in data[access_pattern]:
            data[access_pattern][policy].sort(key=lambda x: x[0])

    return data


def plot_category_graphs(category_name, data, output_dir):
    """
    Create 6 graphs for a category: 3 access patterns × 2 metrics (bandwidth, latency).

    Args:
        category_name: Name of the test category (e.g., "Test1")
        data: Dictionary with structure {access_pattern: {policy: [(size, bw, lat), ...]}}
        output_dir: Directory to save plots
    """
    access_patterns = ['sequential', 'random', 'stride']

    for access_pattern in access_patterns:
        if access_pattern not in data:
            print(f"Warning: No data for {access_pattern} in {category_name}")
            continue

        pattern_data = data[access_pattern]

        # Create bandwidth plot
        fig, ax = plt.subplots(figsize=(10, 6))

        for policy, points in sorted(pattern_data.items()):
            if not points:
                continue

            sizes = [p[0] for p in points]
            throughputs = [p[1] for p in points]

            color = COLORS.get(policy, '#000000')
            marker = MARKERS.get(policy, 'o')

            ax.plot(sizes, throughputs, marker=marker, color=color,
                   label=policy, linewidth=2, markersize=8)

        ax.set_xlabel('Memory Size (MB)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Throughput (MB/s)', fontsize=12, fontweight='bold')
        ax.set_title(f'{category_name}: {access_pattern.capitalize()} Access - Bandwidth',
                    fontsize=14, fontweight='bold')
        ax.set_xscale('log')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best', fontsize=10)

        # Save bandwidth plot
        output_path = os.path.join(output_dir,
                                  f'{category_name}_{access_pattern}_bandwidth.png')
        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        print(f"Saved: {output_path}")
        plt.close()

        # Create latency plot
        fig, ax = plt.subplots(figsize=(10, 6))

        for policy, points in sorted(pattern_data.items()):
            if not points:
                continue

            sizes = [p[0] for p in points]
            latencies = [p[2] for p in points]

            color = COLORS.get(policy, '#000000')
            marker = MARKERS.get(policy, 'o')

            ax.plot(sizes, latencies, marker=marker, color=color,
                   label=policy, linewidth=2, markersize=8)

        ax.set_xlabel('Memory Size (MB)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Average Latency (ns)', fontsize=12, fontweight='bold')
        ax.set_title(f'{category_name}: {access_pattern.capitalize()} Access - Latency',
                    fontsize=14, fontweight='bold')
        ax.set_xscale('log')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best', fontsize=10)

        # Save latency plot
        output_path = os.path.join(output_dir,
                                  f'{category_name}_{access_pattern}_latency.png')
        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        print(f"Saved: {output_path}")
        plt.close()


def main():
    """Main function to process all test categories and generate plots."""

    # Base directory
    base_dir = Path(__file__).parent / 'numa_results_advanced'
    output_dir = Path(__file__).parent / 'numa_plots'

    # Create output directory
    output_dir.mkdir(exist_ok=True)

    # Process each test category
    test_categories = ['Test1', 'Test2', 'Test3']

    print("=" * 60)
    print("NUMA Performance Visualization")
    print("=" * 60)

    for category in test_categories:
        category_path = base_dir / category

        if not category_path.exists():
            print(f"\nSkipping {category} (directory not found)")
            continue

        print(f"\nProcessing {category}...")
        print("-" * 60)

        # Load data
        data = load_test_category_data(category_path)

        if not data:
            print(f"No valid data found in {category}")
            continue

        # Generate plots
        plot_category_graphs(category, data, output_dir)

    print("\n" + "=" * 60)
    print(f"All plots saved to: {output_dir}")
    print("=" * 60)

    # Print summary
    print("\nSummary:")
    print(f"  Output directory: {output_dir}")
    print(f"  Plots generated for each category:")
    print(f"    - 3 bandwidth plots (sequential, random, stride)")
    print(f"    - 3 latency plots (sequential, random, stride)")
    print(f"  Total: 6 plots per category")


if __name__ == '__main__':
    main()
