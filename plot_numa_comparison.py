#!/usr/bin/env python3
"""
NUMA Performance Comparison Script
Generates comparison plots across different test categories.
"""

import os
import re
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict
from pathlib import Path


def parse_result_file(filepath):
    """Parse a single result file and extract throughput and latency."""
    with open(filepath, 'r') as f:
        content = f.read()

    result = {}
    throughput_match = re.search(r'Throughput:\s+([\d.]+)\s+MB/s', content)
    if throughput_match:
        result['throughput'] = float(throughput_match.group(1))

    latency_match = re.search(r'Average latency:\s+([\d.]+)\s+ns per access', content)
    if latency_match:
        result['latency'] = float(latency_match.group(1))

    return result


def extract_info_from_filename(filename):
    """Extract policy, size (MB), and access pattern from filename."""
    name = filename.replace('.txt', '')
    size_match = re.search(r'(\d+)MB', name)
    if not size_match:
        return None, None, None

    size_mb = int(size_match.group(1))
    parts = name.split('_')
    access_pattern = parts[-1]
    policy_end = name.find(f'{size_mb}MB')
    policy = name[:policy_end].rstrip('_')

    return policy, size_mb, access_pattern


def load_all_categories(base_dir):
    """
    Load data from all test categories.

    Returns:
        dict: {category: {access_pattern: {policy: [(size, throughput, latency)]}}}
    """
    all_data = {}
    base_path = Path(base_dir)

    for category_dir in sorted(base_path.glob('Test*')):
        category_name = category_dir.name
        category_data = defaultdict(lambda: defaultdict(list))

        for filepath in category_dir.glob('*.txt'):
            policy, size_mb, access_pattern = extract_info_from_filename(filepath.name)
            if policy is None:
                continue

            result = parse_result_file(filepath)
            if 'throughput' in result and 'latency' in result:
                category_data[access_pattern][policy].append(
                    (size_mb, result['throughput'], result['latency'])
                )

        # Sort by size
        for access_pattern in category_data:
            for policy in category_data[access_pattern]:
                category_data[access_pattern][policy].sort(key=lambda x: x[0])

        all_data[category_name] = category_data

    return all_data


def plot_cross_category_comparison(all_data, output_dir):
    """
    Create comparison plots showing the same policy across different categories.
    Useful for understanding how different NUMA configurations affect performance.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    # Collect all unique policies across all categories
    all_policies = set()
    for category_data in all_data.values():
        for pattern_data in category_data.values():
            all_policies.update(pattern_data.keys())

    access_patterns = ['sequential', 'random', 'stride']

    # For each policy, create a comparison across categories
    for policy in sorted(all_policies):
        for access_pattern in access_patterns:
            # Bandwidth comparison
            fig, ax = plt.subplots(figsize=(12, 7))

            for category, category_data in sorted(all_data.items()):
                if access_pattern not in category_data:
                    continue
                if policy not in category_data[access_pattern]:
                    continue

                points = category_data[access_pattern][policy]
                if not points:
                    continue

                sizes = [p[0] for p in points]
                throughputs = [p[1] for p in points]

                ax.plot(sizes, throughputs, marker='o', label=category,
                       linewidth=2, markersize=8)

            if ax.get_lines():  # Only save if there's data
                ax.set_xlabel('Memory Size (MB)', fontsize=12, fontweight='bold')
                ax.set_ylabel('Throughput (MB/s)', fontsize=12, fontweight='bold')
                ax.set_title(f'{policy}: {access_pattern.capitalize()} Access - Bandwidth Comparison',
                            fontsize=14, fontweight='bold')
                ax.set_xscale('log')
                ax.grid(True, alpha=0.3)
                ax.legend(loc='best', fontsize=11)

                output_path = output_dir / f'comparison_{policy}_{access_pattern}_bandwidth.png'
                plt.tight_layout()
                plt.savefig(output_path, dpi=150)
                print(f"Saved: {output_path}")
                plt.close()
            else:
                plt.close()

            # Latency comparison
            fig, ax = plt.subplots(figsize=(12, 7))

            for category, category_data in sorted(all_data.items()):
                if access_pattern not in category_data:
                    continue
                if policy not in category_data[access_pattern]:
                    continue

                points = category_data[access_pattern][policy]
                if not points:
                    continue

                sizes = [p[0] for p in points]
                latencies = [p[2] for p in points]

                ax.plot(sizes, latencies, marker='o', label=category,
                       linewidth=2, markersize=8)

            if ax.get_lines():  # Only save if there's data
                ax.set_xlabel('Memory Size (MB)', fontsize=12, fontweight='bold')
                ax.set_ylabel('Average Latency (ns)', fontsize=12, fontweight='bold')
                ax.set_title(f'{policy}: {access_pattern.capitalize()} Access - Latency Comparison',
                            fontsize=14, fontweight='bold')
                ax.set_xscale('log')
                ax.grid(True, alpha=0.3)
                ax.legend(loc='best', fontsize=11)

                output_path = output_dir / f'comparison_{policy}_{access_pattern}_latency.png'
                plt.tight_layout()
                plt.savefig(output_path, dpi=150)
                print(f"Saved: {output_path}")
                plt.close()
            else:
                plt.close()


def generate_summary_stats(all_data):
    """Generate summary statistics for each category."""
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)

    for category, category_data in sorted(all_data.items()):
        print(f"\n{category}:")
        print("-" * 80)

        for access_pattern in ['sequential', 'random', 'stride']:
            if access_pattern not in category_data:
                continue

            print(f"\n  {access_pattern.upper()} Access Pattern:")

            for policy, points in sorted(category_data[access_pattern].items()):
                if not points:
                    continue

                throughputs = [p[1] for p in points]
                latencies = [p[2] for p in points]

                avg_bw = np.mean(throughputs)
                max_bw = np.max(throughputs)
                min_bw = np.min(throughputs)

                avg_lat = np.mean(latencies)
                min_lat = np.min(latencies)
                max_lat = np.max(latencies)

                print(f"    {policy}:")
                print(f"      Bandwidth:  avg={avg_bw:7.2f} MB/s, "
                      f"min={min_bw:7.2f} MB/s, max={max_bw:7.2f} MB/s")
                print(f"      Latency:    avg={avg_lat:7.2f} ns,   "
                      f"min={min_lat:7.2f} ns,   max={max_lat:7.2f} ns")


def main():
    """Main function."""
    base_dir = Path(__file__).parent / 'numa_results_advanced'
    output_dir = Path(__file__).parent / 'numa_plots_comparison'

    print("="*80)
    print("NUMA Cross-Category Comparison Analysis")
    print("="*80)

    # Load all data
    print("\nLoading data from all categories...")
    all_data = load_all_categories(base_dir)

    if not all_data:
        print("No data found!")
        return

    print(f"Loaded data from {len(all_data)} categories")

    # Generate comparison plots
    print("\nGenerating cross-category comparison plots...")
    plot_cross_category_comparison(all_data, output_dir)

    # Generate summary statistics
    generate_summary_stats(all_data)

    print("\n" + "="*80)
    print(f"Comparison plots saved to: {output_dir}")
    print("="*80)


if __name__ == '__main__':
    main()
