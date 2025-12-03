#!/usr/bin/env python3
"""
Test Category 2: Cross-Node Memory Access - Performance Counter Evidence

This script generates additional evidence beyond throughput/latency:
1. TLB miss count comparison (Local vs Remote)
2. NUMA allocation verification (confirms test correctness)

Outputs:
- category2_tlb_misses.png
- category2_numa_allocation_verification.png
"""

import os
import re
import matplotlib.pyplot as plt
import numpy as np

RESULTS_DIR = "numa_results_advanced/Test2"
MIN_SIZE_MB = 512  # Filter out small sizes where cache effects dominate

def format_size_label(size_mb):
    """Convert MB to GB if >= 1024 MB for clearer labels"""
    if size_mb >= 1024:
        return f'{size_mb // 1024} GB'
    else:
        return f'{size_mb} MB'

def parse_perf_counters(filepath):
    """Extract perf counters from .perf file"""
    try:
        with open(filepath + '.perf', 'r') as f:
            content = f.read()

        counters = {}

        # Parse cache counters
        cache_misses_match = re.search(r'([\d,]+)\s+cache-misses', content)
        cache_refs_match = re.search(r'([\d,]+)\s+cache-references', content)

        if cache_misses_match and cache_refs_match:
            counters['cache_misses'] = int(cache_misses_match.group(1).replace(',', ''))
            counters['cache_references'] = int(cache_refs_match.group(1).replace(',', ''))

            # Calculate cache miss rate
            if counters['cache_references'] > 0:
                counters['cache_miss_rate'] = (counters['cache_misses'] / counters['cache_references']) * 100
            else:
                counters['cache_miss_rate'] = 0

        # Parse TLB counters
        dtlb_load_match = re.search(r'([\d,]+)\s+dTLB-load-misses', content)
        dtlb_store_match = re.search(r'([\d,]+)\s+dTLB-store-misses', content)

        if dtlb_load_match and dtlb_store_match:
            counters['dtlb_load_misses'] = int(dtlb_load_match.group(1).replace(',', ''))
            counters['dtlb_store_misses'] = int(dtlb_store_match.group(1).replace(',', ''))
            counters['total_tlb_misses'] = counters['dtlb_load_misses'] + counters['dtlb_store_misses']

        return counters
    except:
        return {}

def parse_vmstat_delta(filepath):
    """Calculate NUMA counter deltas from vmstat_before and vmstat_after files"""
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

def collect_tlb_data():
    """Collect TLB data for all test configurations"""
    data = {
        'local': {},
        'remote_0to1': {},
        'remote_1to0': {}
    }

    for config in ['local', 'remote_0to1', 'remote_1to0']:
        for pattern in ['sequential', 'random', 'stride']:
            data[config][pattern] = {
                'sizes': [],
                'total_tlb_misses': []
            }

    # Scan all result files
    for filename in os.listdir(RESULTS_DIR):
        # Match: local_node0_*MB_*.txt, remote_node0to1_*MB_*.txt, remote_node1to0_*MB_*.txt
        match = re.match(r'(local_node0|remote_node0to1|remote_node1to0)_(\d+)MB_(sequential|random|stride)\.txt', filename)
        if match:
            config_raw = match.group(1)
            size_mb = int(match.group(2))
            pattern = match.group(3)

            # Skip small sizes and sizes > 64GB
            if size_mb < MIN_SIZE_MB or size_mb > 65536:
                continue

            # Map config name
            config_map = {
                'local_node0': 'local',
                'remote_node0to1': 'remote_0to1',
                'remote_node1to0': 'remote_1to0'
            }
            config = config_map[config_raw]

            filepath = os.path.join(RESULTS_DIR, filename)
            counters = parse_perf_counters(filepath)

            if counters and 'total_tlb_misses' in counters:
                data[config][pattern]['sizes'].append(size_mb)
                data[config][pattern]['total_tlb_misses'].append(counters['total_tlb_misses'])

    # Sort by size
    for config in data:
        for pattern in data[config]:
            if data[config][pattern]['sizes']:
                # Sort all lists together by size
                sorted_data = sorted(zip(
                    data[config][pattern]['sizes'],
                    data[config][pattern]['total_tlb_misses']
                ))

                data[config][pattern]['sizes'] = [x[0] for x in sorted_data]
                data[config][pattern]['total_tlb_misses'] = [x[1] for x in sorted_data]

    return data

def collect_numa_allocation_data():
    """Collect NUMA allocation data for random access pattern only"""
    # Only collect local and one remote case (skip symmetric remote_1to0)
    data = {
        'local': {'sizes': [], 'numa_local': [], 'numa_other': []},
        'remote_0to1': {'sizes': [], 'numa_local': [], 'numa_other': []}
    }

    # Scan files for random access pattern only
    for filename in os.listdir(RESULTS_DIR):
        match = re.match(r'(local_node0|remote_node0to1|remote_node1to0)_(\d+)MB_random\.txt', filename)
        if match:
            config_raw = match.group(1)
            size_mb = int(match.group(2))

            # Skip small sizes and sizes > 64GB
            if size_mb < MIN_SIZE_MB or size_mb > 65536:
                continue

            # Skip symmetric case (remote_1to0)
            if config_raw == 'remote_node1to0':
                continue

            config_map = {
                'local_node0': 'local',
                'remote_node0to1': 'remote_0to1'
            }
            config = config_map[config_raw]

            filepath = os.path.join(RESULTS_DIR, filename)
            vmstat_deltas = parse_vmstat_delta(filepath)

            if 'numa_local' in vmstat_deltas and 'numa_other' in vmstat_deltas:
                data[config]['sizes'].append(size_mb)
                data[config]['numa_local'].append(vmstat_deltas['numa_local'])
                data[config]['numa_other'].append(vmstat_deltas['numa_other'])

    # Sort by size
    for config in data:
        if data[config]['sizes']:
            sorted_data = sorted(zip(
                data[config]['sizes'],
                data[config]['numa_local'],
                data[config]['numa_other']
            ))

            data[config]['sizes'] = [x[0] for x in sorted_data]
            data[config]['numa_local'] = [x[1] for x in sorted_data]
            data[config]['numa_other'] = [x[2] for x in sorted_data]

    return data

def plot_tlb_misses():
    """Generate TLB miss count comparison"""
    data = collect_tlb_data()

    fig, axes = plt.subplots(1, 3, figsize=(20, 6))
    patterns = ['sequential', 'random', 'stride']
    pattern_titles = ['Sequential Access', 'Random Access', 'Stride Access']

    for idx, pattern in enumerate(patterns):
        ax = axes[idx]

        # Get all unique sizes
        all_sizes = sorted(set(
            data['local'][pattern]['sizes'] +
            data['remote_0to1'][pattern]['sizes'] +
            data['remote_1to0'][pattern]['sizes']
        ))

        if not all_sizes:
            continue

        # Prepare data
        local_vals = []
        remote_0to1_vals = []
        remote_1to0_vals = []

        for size in all_sizes:
            # Local
            if size in data['local'][pattern]['sizes']:
                idx_local = data['local'][pattern]['sizes'].index(size)
                local_vals.append(data['local'][pattern]['total_tlb_misses'][idx_local])
            else:
                local_vals.append(0)

            # Remote 0→1
            if size in data['remote_0to1'][pattern]['sizes']:
                idx_r01 = data['remote_0to1'][pattern]['sizes'].index(size)
                remote_0to1_vals.append(data['remote_0to1'][pattern]['total_tlb_misses'][idx_r01])
            else:
                remote_0to1_vals.append(0)

            # Remote 1→0
            if size in data['remote_1to0'][pattern]['sizes']:
                idx_r10 = data['remote_1to0'][pattern]['sizes'].index(size)
                remote_1to0_vals.append(data['remote_1to0'][pattern]['total_tlb_misses'][idx_r10])
            else:
                remote_1to0_vals.append(0)

        # Create grouped bar chart
        x = np.arange(len(all_sizes))
        width = 0.25

        bars1 = ax.bar(x - width, local_vals, width, label='Local (node 0→0)',
                       color='#2ca02c', alpha=0.8)
        bars2 = ax.bar(x, remote_0to1_vals, width, label='Remote (node 0→1)',
                       color='#ff7f0e', alpha=0.8)
        bars3 = ax.bar(x + width, remote_1to0_vals, width, label='Remote (node 1→0)',
                       color='#d62728', alpha=0.8)

        # Add degradation arrows for first and last memory sizes only
        # (98GB is already filtered out in data collection)
        last_idx = len(all_sizes) - 1

        # Draw arrows for first and last positions
        for i in [0, last_idx]:
            if i < len(all_sizes):
                local_val = local_vals[i]
                remote_val = remote_0to1_vals[i]

                if local_val > 0 and remote_val > 0:
                    # Calculate percentage increase from local to remote
                    increase_pct = ((remote_val - local_val) / local_val) * 100

                    # Draw arrow from local bar to remote bar
                    arrow_props = dict(arrowstyle='->', color='red', lw=2.5, alpha=0.7)
                    ax.annotate('',
                               xy=(i, remote_val),
                               xytext=(i - width, local_val),
                               arrowprops=arrow_props)

                    # Add label
                    mid_y = (local_val + remote_val) / 2
                    ax.text(i - width/2, mid_y, f'↑{increase_pct:.0f}%',
                           fontsize=10, color='red', fontweight='bold',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                                    edgecolor='red', alpha=0.9, linewidth=2))

        # Formatting
        ax.set_xlabel('Memory Size', fontsize=11, fontweight='bold')
        ax.set_ylabel('Total TLB Misses (load + store)', fontsize=11, fontweight='bold')
        ax.set_title(pattern_titles[idx], fontsize=12, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels([format_size_label(s) for s in all_sizes], rotation=45, ha='right')
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3, axis='y')

    plt.suptitle('Test Category 2: TLB Misses - Local vs Remote Memory Access',
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig('category2_tlb_misses.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: category2_tlb_misses.png")
    plt.close()

def plot_numa_allocation_verification():
    """Generate NUMA allocation verification for random access pattern"""
    data = collect_numa_allocation_data()

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    configs = ['local', 'remote_0to1']
    config_titles = [
        'Local (CPU node 0, Mem node 0)',
        'Remote (CPU node 0, Mem node 1)'
    ]

    for idx, (config, title) in enumerate(zip(configs, config_titles)):
        ax = axes[idx]

        if not data[config]['sizes']:
            continue

        sizes = data[config]['sizes']
        numa_local = data[config]['numa_local']
        numa_other = data[config]['numa_other']

        # Create discrete x positions
        x = np.arange(len(sizes))
        width = 0.6

        # Stacked bar chart
        bars1 = ax.bar(x, numa_local, width, label='numa_local',
                       color='#2ca02c', alpha=0.8)
        bars2 = ax.bar(x, numa_other, width, bottom=numa_local,
                       label='numa_other', color='#d62728', alpha=0.8)

        # Add percentage labels in black for better clarity
        for i, (local, other) in enumerate(zip(numa_local, numa_other)):
            total = local + other
            if total > 0:
                local_pct = (local / total) * 100
                other_pct = (other / total) * 100

                # Label for numa_local
                if local_pct > 5:  # Only show if significant
                    ax.text(i, local / 2, f'{local_pct:.0f}%',
                           ha='center', va='center', fontsize=9, fontweight='bold', color='black')

                # Label for numa_other
                if other_pct > 5:  # Only show if significant
                    ax.text(i, local + other / 2, f'{other_pct:.0f}%',
                           ha='center', va='center', fontsize=9, fontweight='bold', color='black')

        # Formatting
        ax.set_xlabel('Memory Size', fontsize=11, fontweight='bold')
        ax.set_ylabel('Allocation Count (Delta)', fontsize=11, fontweight='bold')
        ax.set_title(title, fontsize=11, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels([format_size_label(s) for s in sizes], rotation=45, ha='right')
        ax.legend(fontsize=9, loc='upper right')
        ax.grid(True, alpha=0.3, axis='y')

    plt.suptitle('Test Category 2: NUMA Allocation Verification (Random Access Pattern)\n' +
                 'Confirms Correct CPU/Memory Binding',
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig('category2_numa_allocation_verification.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: category2_numa_allocation_verification.png")
    plt.close()

if __name__ == '__main__':
    print("Generating Category 2 performance counter visualizations...")
    print()

    # Generate visualizations
    plot_tlb_misses()
    plot_numa_allocation_verification()

    print()
    print("✓ Category 2 performance counter visualization complete!")
    print("  - category2_tlb_misses.png")
    print("  - category2_numa_allocation_verification.png")
