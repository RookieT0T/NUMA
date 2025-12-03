#!/usr/bin/env python3
"""
Test Category 2: NUMA Penalty Bar Chart
Compare local vs remote memory access performance across different sizes and patterns
"""

import os
import re
import matplotlib.pyplot as plt
import numpy as np

RESULTS_DIR = "numa_results_advanced/Test2"

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
    """Collect local vs remote access data"""
    data = {}  # {size: {pattern: {'local': X, 'remote_0to1': Y, 'remote_1to0': Z}}}

    for filename in sorted(os.listdir(RESULTS_DIR)):
        # Parse: local_node0_512MB_sequential.txt, remote_node0to1_512MB_sequential.txt
        match = re.match(r'(local|remote)_node(0|0to1|1to0)_(\d+)MB_(sequential|random|stride)\.txt', filename)
        if match:
            access_type = match.group(1)  # local or remote
            node_info = match.group(2)     # 0, 0to1, or 1to0
            size_mb = int(match.group(3))
            pattern = match.group(4)

            filepath = os.path.join(RESULTS_DIR, filename)
            throughput = parse_result_file(filepath)

            if throughput is not None:
                if size_mb not in data:
                    data[size_mb] = {}
                if pattern not in data[size_mb]:
                    data[size_mb][pattern] = {}

                if access_type == 'local':
                    data[size_mb][pattern]['local'] = throughput
                else:
                    if node_info == '0to1':
                        data[size_mb][pattern]['remote_0to1'] = throughput
                    elif node_info == '1to0':
                        data[size_mb][pattern]['remote_1to0'] = throughput

    return data

def format_size_label(size_mb):
    """Convert MB to GB if >= 1024 MB for clearer labels"""
    if size_mb >= 1024:
        return f'{size_mb // 1024} GB'
    else:
        return f'{size_mb} MB'

def plot_numa_penalty():
    """Create NUMA penalty bar chart"""
    data = collect_data()
    sizes = sorted(data.keys())
    patterns = ['sequential', 'random', 'stride']

    # Create subplots for each access pattern
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    for ax, pattern in zip(axes, patterns):
        x = np.arange(len(sizes))
        width = 0.25

        local_perf = []
        remote_0to1_perf = []
        remote_1to0_perf = []

        for size in sizes:
            if pattern in data[size]:
                local_perf.append(data[size][pattern].get('local', 0))
                remote_0to1_perf.append(data[size][pattern].get('remote_0to1', 0))
                remote_1to0_perf.append(data[size][pattern].get('remote_1to0', 0))
            else:
                local_perf.append(0)
                remote_0to1_perf.append(0)
                remote_1to0_perf.append(0)

        # Plot bars
        ax.bar(x - width, local_perf, width, label='Local (node 0→0)', color='#2ca02c', alpha=0.8)
        ax.bar(x, remote_0to1_perf, width, label='Remote (node 0→1)', color='#ff7f0e', alpha=0.8)
        ax.bar(x + width, remote_1to0_perf, width, label='Remote (node 1→0)', color='#d62728', alpha=0.8)

        # Add arrows showing penalty drop from local to remote
        for i in range(len(sizes)):
            if local_perf[i] > 0 and remote_0to1_perf[i] > 0:
                # Calculate penalty percentage
                penalty = ((local_perf[i] - remote_0to1_perf[i]) / local_perf[i]) * 100

                # Draw arrow from local bar to remote bar
                arrow_x_start = x[i] - width
                arrow_x_end = x[i]
                arrow_y_start = local_perf[i]
                arrow_y_end = remote_0to1_perf[i]

                # Add arrow annotation
                ax.annotate('', xy=(arrow_x_end, arrow_y_end), xytext=(arrow_x_start, arrow_y_start),
                           arrowprops=dict(arrowstyle='->', color='blue', lw=1.0, alpha=0.6))

                # Add penalty percentage text
                mid_x = (arrow_x_start + arrow_x_end) / 2
                mid_y = (arrow_y_start + arrow_y_end) / 2
                ax.text(mid_x, mid_y, f'-{penalty:.0f}%',
                       fontsize=6, color='blue', fontweight='bold',
                       ha='center', va='bottom', bbox=dict(boxstyle='round,pad=0.3',
                       facecolor='white', edgecolor='blue', alpha=0.6))

        ax.set_xlabel('Memory Size', fontsize=11, fontweight='bold')
        ax.set_ylabel('Throughput (MB/s)', fontsize=11, fontweight='bold')
        ax.set_title(f'{pattern.capitalize()} Access', fontsize=12, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels([format_size_label(s) for s in sizes], rotation=45, ha='right')
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3, axis='y')

    plt.suptitle('NUMA Penalty: Local vs Remote Memory Access',
                 fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig('category2_numa_penalty.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: category2_numa_penalty.png")
    plt.show()

    # Print NUMA penalty percentages
    print("\n=== NUMA Penalty Analysis ===")
    for pattern in patterns:
        print(f"\n{pattern.upper()} Access Pattern:")
        for size in sizes:
            if pattern in data[size]:
                local = data[size][pattern].get('local', 0)
                remote = data[size][pattern].get('remote_0to1', 0)
                if local > 0 and remote > 0:
                    penalty = ((local - remote) / local) * 100
                    print(f"  {size:4d} MB: {penalty:5.1f}% performance drop for remote access")

if __name__ == '__main__':
    plot_numa_penalty()
