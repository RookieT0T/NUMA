#!/usr/bin/env python3
"""
Test Category 1: Memory Pressure & Fallback Behavior
Comprehensive visualization covering all three findings

Findings:
1. Strict policies (membind) fail catastrophically when node capacity exceeded
2. Preferred policy provides graceful degradation under pressure
3. Random access patterns more sensitive to memory pressure than sequential

Outputs:
- category1_throughput_pressure.png (Throughput comparison)
- category1_latency_pressure.png (Latency comparison)
- category1_preferred_fallback_counters.png (Performance counter evidence)
"""

import os
import re
import subprocess
import matplotlib.pyplot as plt
import numpy as np

RESULTS_DIR = "numa_results_advanced/Test1"
MIN_SIZE_MB = 512  # Filter out small sizes where cache effects dominate

def get_node_capacity():
    """Detect NUMA node memory capacity using numactl"""
    try:
        result = subprocess.run(
            ["numactl", "--hardware"],
            capture_output=True,
            text=True,
            check=True
        )
        # Parse: "node 0 size: 98765 MB"
        match = re.search(r'node 0 size:\s+(\d+)\s+MB', result.stdout)
        if match:
            return int(match.group(1))
    except:
        pass
    return None

def format_size_label(size_mb):
    """Convert MB to GB if >= 1024 MB for clearer labels"""
    if size_mb >= 1024:
        return f'{size_mb // 1024} GB'
    else:
        return f'{size_mb} MB'

def parse_test_result(filepath):
    """Extract throughput and latency from test result file"""
    try:
        with open(filepath, 'r') as f:
            content = f.read()

        # Check if process was killed
        if 'Killed' in content or 'killed' in content:
            return None, None, True

        # Parse throughput
        throughput_match = re.search(r'Throughput:\s+([\d.]+)\s+MB/s', content)
        throughput = float(throughput_match.group(1)) if throughput_match else None

        # Parse latency
        latency_match = re.search(r'Average latency:\s+([\d.]+)\s+ns', content)
        latency = float(latency_match.group(1)) if latency_match else None

        return throughput, latency, False
    except FileNotFoundError:
        return None, None, True
    except Exception as e:
        return None, None, False

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

def collect_pressure_curve_data():
    """Collect data for pressure curve visualization"""
    data = {
        'membind': {},
        'preferred': {}
    }

    for policy in ['membind', 'preferred']:
        for pattern in ['sequential', 'random', 'stride']:
            data[policy][pattern] = {
                'sizes': [],
                'throughput': [],
                'latency': []
            }

    # Scan all result files
    for filename in sorted(os.listdir(RESULTS_DIR)):
        match = re.match(r'(membind|preferred)_node0_(\d+)MB_(sequential|random|stride)\.txt', filename)
        if match:
            policy = match.group(1)
            size_mb = int(match.group(2))
            pattern = match.group(3)

            filepath = os.path.join(RESULTS_DIR, filename)
            throughput, latency, was_killed = parse_test_result(filepath)

            # Only include sizes >= MIN_SIZE_MB to avoid cache-dominated behavior
            if not was_killed and throughput is not None and size_mb >= MIN_SIZE_MB:
                data[policy][pattern]['sizes'].append(size_mb)
                data[policy][pattern]['throughput'].append(throughput)
                data[policy][pattern]['latency'].append(latency if latency else 0)

    return data

def collect_preferred_counter_data():
    """Collect performance counter data for preferred policy, random access"""
    # Collect data with size as key for proper sorting
    raw_data = {}

    # Parse preferred_node0_*MB_random.txt files
    for filename in os.listdir(RESULTS_DIR):
        match = re.match(r'preferred_node0_(\d+)MB_random\.txt', filename)
        if match:
            size_mb = int(match.group(1))
            filepath = os.path.join(RESULTS_DIR, filename)

            throughput, _, was_killed = parse_test_result(filepath)
            # Only include sizes >= MIN_SIZE_MB to avoid cache-dominated behavior
            if was_killed or throughput is None or size_mb < MIN_SIZE_MB:
                continue

            vmstat_deltas = parse_vmstat_delta(filepath)

            raw_data[size_mb] = {
                'numa_miss': vmstat_deltas.get('numa_miss', 0),
                'numa_foreign': vmstat_deltas.get('numa_foreign', 0),
                'numa_pages_migrated': vmstat_deltas.get('numa_pages_migrated', 0)
            }

    # Sort by size and build final data structure
    data = {
        'sizes': [],
        'numa_miss': [],
        'numa_foreign': [],
        'numa_pages_migrated': []
    }

    for size_mb in sorted(raw_data.keys()):
        data['sizes'].append(size_mb)
        data['numa_miss'].append(raw_data[size_mb]['numa_miss'])
        data['numa_foreign'].append(raw_data[size_mb]['numa_foreign'])
        data['numa_pages_migrated'].append(raw_data[size_mb]['numa_pages_migrated'])

    return data

def plot_throughput_pressure():
    """Generate throughput comparison across patterns and policies"""
    data = collect_pressure_curve_data()
    node_capacity = get_node_capacity()

    fig, axes = plt.subplots(1, 3, figsize=(20, 6))
    patterns = ['sequential', 'random', 'stride']
    pattern_titles = ['Sequential Access', 'Random Access', 'Stride Access']

    for idx, pattern in enumerate(patterns):
        ax = axes[idx]

        # Get all unique sizes for this pattern (union of membind and preferred)
        all_sizes = sorted(set(data['membind'][pattern]['sizes'] + data['preferred'][pattern]['sizes']))

        if not all_sizes:
            continue

        # Prepare data for grouped bar chart
        membind_vals = []
        preferred_vals = []

        for size in all_sizes:
            # Find membind value
            if size in data['membind'][pattern]['sizes']:
                idx_mb = data['membind'][pattern]['sizes'].index(size)
                membind_vals.append(data['membind'][pattern]['throughput'][idx_mb])
            else:
                membind_vals.append(0)  # No data (killed)

            # Find preferred value
            if size in data['preferred'][pattern]['sizes']:
                idx_pf = data['preferred'][pattern]['sizes'].index(size)
                preferred_vals.append(data['preferred'][pattern]['throughput'][idx_pf])
            else:
                preferred_vals.append(0)

        # Create discrete x positions
        x = np.arange(len(all_sizes))
        width = 0.35

        # Plot bars
        bars1 = ax.bar(x - width/2, membind_vals, width, label='Membind (Strict)',
                       color='#ff7f0e', alpha=0.8)
        bars2 = ax.bar(x + width/2, preferred_vals, width, label='Preferred (Fallback)',
                       color='#2ca02c', alpha=0.8)

        # Add degradation arrow for preferred policy
        if len(preferred_vals) >= 2:
            # Arrow from first to last
            baseline_val = preferred_vals[0]
            final_val = preferred_vals[-1]
            if baseline_val > 0 and final_val > 0:
                degradation_pct = ((baseline_val - final_val) / baseline_val) * 100

                # Draw arrow
                arrow_props = dict(arrowstyle='->', color='red', lw=2.5, alpha=0.7)
                ax.annotate('',
                           xy=(len(all_sizes)-1 + width/2, final_val),
                           xytext=(0 + width/2, baseline_val),
                           arrowprops=arrow_props)

                # Add label
                mid_x = len(all_sizes) / 2
                mid_y = (baseline_val + final_val) / 2
                ax.text(mid_x, mid_y, f'↓{degradation_pct:.0f}%',
                       fontsize=13, color='red', fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                                edgecolor='red', alpha=0.9, linewidth=2))

        # Formatting
        ax.set_xlabel('Memory Size', fontsize=13, fontweight='bold')
        ax.set_ylabel('Throughput (MB/s)', fontsize=13, fontweight='bold')
        ax.set_title(pattern_titles[idx], fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.tick_params(axis='x', labelsize=13)
        ax.set_xticklabels([format_size_label(s) for s in all_sizes], rotation=45, ha='right')
        ax.legend(fontsize=14)
        ax.grid(True, alpha=0.3, axis='y')

        # Add pivot point if detected
        if node_capacity:
            # Find the position closest to node capacity
            for i, size in enumerate(all_sizes):
                if size >= node_capacity:
                    ax.axvline(x=i-0.5, color='gray', linestyle=':', linewidth=2, alpha=0.7)
                    break

    plt.suptitle('Throughput - Memory Pressure & Fallback Behavior',
                 fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig('category1_throughput_pressure.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: category1_throughput_pressure.png")
    plt.close()

def plot_latency_pressure():
    """Generate latency comparison across patterns and policies"""
    data = collect_pressure_curve_data()
    node_capacity = get_node_capacity()

    fig, axes = plt.subplots(1, 3, figsize=(20, 6))
    patterns = ['sequential', 'random', 'stride']
    pattern_titles = ['Sequential Access', 'Random Access', 'Stride Access']

    for idx, pattern in enumerate(patterns):
        ax = axes[idx]

        # Get all unique sizes
        all_sizes = sorted(set(data['membind'][pattern]['sizes'] + data['preferred'][pattern]['sizes']))

        if not all_sizes:
            continue

        # Prepare data
        membind_vals = []
        preferred_vals = []

        for size in all_sizes:
            if size in data['membind'][pattern]['sizes']:
                idx_mb = data['membind'][pattern]['sizes'].index(size)
                membind_vals.append(data['membind'][pattern]['latency'][idx_mb])
            else:
                membind_vals.append(0)

            if size in data['preferred'][pattern]['sizes']:
                idx_pf = data['preferred'][pattern]['sizes'].index(size)
                preferred_vals.append(data['preferred'][pattern]['latency'][idx_pf])
            else:
                preferred_vals.append(0)

        # Create discrete x positions
        x = np.arange(len(all_sizes))
        width = 0.35

        # Plot bars
        bars1 = ax.bar(x - width/2, membind_vals, width, label='Membind (Strict)',
                       color='#ff7f0e', alpha=0.8)
        bars2 = ax.bar(x + width/2, preferred_vals, width, label='Preferred (Fallback)',
                       color='#2ca02c', alpha=0.8)

        # Add degradation arrow for preferred policy
        if len(preferred_vals) >= 2:
            baseline_val = preferred_vals[0]
            final_val = preferred_vals[-1]
            if baseline_val > 0 and final_val > 0:
                increase_pct = ((final_val - baseline_val) / baseline_val) * 100

                # Draw arrow
                arrow_props = dict(arrowstyle='->', color='red', lw=2.5, alpha=0.7)
                ax.annotate('',
                           xy=(len(all_sizes)-1 + width/2, final_val),
                           xytext=(0 + width/2, baseline_val),
                           arrowprops=arrow_props)

                # Add label
                mid_x = len(all_sizes) / 2
                mid_y = (baseline_val + final_val) / 2
                ax.text(mid_x, mid_y, f'↑{increase_pct:.0f}%',
                       fontsize=13, color='red', fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.4', facecolor='white',
                                edgecolor='red', alpha=0.9, linewidth=2))

        # Formatting
        ax.set_xlabel('Memory Allocation Size', fontsize=13, fontweight='bold')
        ax.set_ylabel('Average Latency (ns)', fontsize=13, fontweight='bold')
        ax.set_title(pattern_titles[idx], fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.tick_params(axis='x', labelsize=13)
        ax.set_xticklabels([format_size_label(s) for s in all_sizes], rotation=45, ha='right')
        ax.legend(fontsize=14)
        ax.grid(True, alpha=0.3, axis='y')

        # Add pivot point if detected
        if node_capacity:
            for i, size in enumerate(all_sizes):
                if size >= node_capacity:
                    ax.axvline(x=i-0.5, color='gray', linestyle=':', linewidth=2, alpha=0.7)
                    break

    plt.suptitle('Latency - Memory Pressure & Fallback Behavior',
                 fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig('category1_latency_pressure.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: category1_latency_pressure.png")
    plt.close()

def plot_preferred_fallback_counters():
    """Generate performance counter bar charts (Finding 2)"""
    data = collect_preferred_counter_data()
    node_capacity = get_node_capacity()

    if not data['sizes']:
        print("No data found for preferred policy random access tests")
        return

    fig, axes = plt.subplots(1, 3, figsize=(20, 6))

    counters = [
        ('numa_miss', 'numa_miss', 'NUMA Miss (Wanted Local, Got Remote)', '#ff7f0e'),
        ('numa_foreign', 'numa_foreign', 'NUMA Foreign (Remote Allocation Satisfied)', '#d62728'),
        ('numa_pages_migrated', 'numa_pages_migrated', 'NUMA Pages Migrated', '#9467bd')
    ]

    # Create discrete x positions
    x = np.arange(len(data['sizes']))

    for idx, (key, label, title, color) in enumerate(counters):
        ax = axes[idx]

        # Plot bar chart
        bars = ax.bar(x, data[key], color=color, alpha=0.8, edgecolor='black', linewidth=0.5)

        # Add value labels on bars
        for i, (bar, val) in enumerate(zip(bars, data[key])):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                       f'{val:,}', ha='center', va='bottom', fontsize=12)

        # Add pivot point (node capacity) if detected
        if node_capacity:
            # Find the position where size >= node capacity
            pivot_idx = None
            for i, size in enumerate(data['sizes']):
                if size >= node_capacity:
                    pivot_idx = i
                    break

            if pivot_idx is not None:
                # Draw vertical line before the pivot point
                ax.axvline(x=pivot_idx - 0.5, color='red', linestyle='--',
                          linewidth=2.5, alpha=0.7, label=f'Node Capacity ({format_size_label(node_capacity)})')

                # Add text annotation (only on first subplot to avoid clutter)
                # if idx == 0:
                #     ax.text(pivot_idx - 0.5, ax.get_ylim()[1] * 0.95,
                #            f'Pivot: {format_size_label(node_capacity)}\nFallback begins →',
                #            fontsize=9, ha='right', va='top', color='red', fontweight='bold',
                #            bbox=dict(boxstyle='round,pad=0.4', facecolor='yellow',
                #                    edgecolor='red', alpha=0.8, linewidth=1.5))

        # Formatting
        ax.set_xlabel('Memory Allocation Size', fontsize=13, fontweight='bold')
        ax.set_ylabel('Counter Value (Delta)', fontsize=13, fontweight='bold')
        ax.set_title(title, fontsize=13, fontweight='bold')
        ax.set_xticks(x)
        ax.tick_params(axis='x', labelsize=13)
        ax.set_xticklabels([format_size_label(s) for s in data['sizes']], rotation=45, ha='right')
        ax.grid(True, alpha=0.3, axis='y')
        if node_capacity and idx == 0:
            ax.legend(fontsize=14, loc='upper left')

    plt.suptitle('Performance Counter Evidence - Preferred Policy Fallback Under Random Access', fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig('category1_preferred_fallback_counters.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: category1_preferred_fallback_counters.png")
    plt.close()

if __name__ == '__main__':
    print("Generating Category 1 visualizations...")
    print()

    # Generate all visualizations
    plot_throughput_pressure()
    plot_latency_pressure()
    plot_preferred_fallback_counters()

    print()
    print("✓ Category 1 visualization complete!")
    print("  - category1_throughput_pressure.png")
    print("  - category1_latency_pressure.png")
    print("  - category1_preferred_fallback_counters.png")
