#!/usr/bin/env python3
"""
Test Category 2: NUMA Latency Penalty Bar Chart
Compare local vs remote memory access latency across different sizes and patterns
"""

import os
import re
import matplotlib.pyplot as plt
import numpy as np

RESULTS_DIR = "numa_results_advanced/Test2"

def parse_result_file(filepath):
    """Extract latency from result file"""
    try:
        with open(filepath, 'r') as f:
            content = f.read()

        latency_match = re.search(r'Average latency:\s+([\d.]+)\s+ns', content)
        return float(latency_match.group(1)) if latency_match else None
    except:
        return None

def collect_data():
    """Collect local vs remote access latency data"""
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
            latency = parse_result_file(filepath)

            if latency is not None:
                if size_mb not in data:
                    data[size_mb] = {}
                if pattern not in data[size_mb]:
                    data[size_mb][pattern] = {}

                if access_type == 'local':
                    data[size_mb][pattern]['local'] = latency
                else:
                    if node_info == '0to1':
                        data[size_mb][pattern]['remote_0to1'] = latency
                    elif node_info == '1to0':
                        data[size_mb][pattern]['remote_1to0'] = latency

    return data

def format_size_label(size_mb):
    """Convert MB to GB if >= 1024 MB for clearer labels"""
    if size_mb >= 1024:
        return f'{size_mb // 1024} GB'
    else:
        return f'{size_mb} MB'

def plot_latency_penalty():
    """Create NUMA latency penalty bar chart"""
    data = collect_data()
    sizes = sorted(data.keys())
    patterns = ['sequential', 'random', 'stride']

    # Create subplots for each access pattern
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    for ax, pattern in zip(axes, patterns):
        x = np.arange(len(sizes))
        width = 0.25

        local_latency = []
        remote_0to1_latency = []
        remote_1to0_latency = []

        for size in sizes:
            if pattern in data[size]:
                local_latency.append(data[size][pattern].get('local', 0))
                remote_0to1_latency.append(data[size][pattern].get('remote_0to1', 0))
                remote_1to0_latency.append(data[size][pattern].get('remote_1to0', 0))
            else:
                local_latency.append(0)
                remote_0to1_latency.append(0)
                remote_1to0_latency.append(0)

        # Plot bars
        ax.bar(x - width, local_latency, width, label='Local (node 0→0)', color='#2ca02c', alpha=0.8)
        ax.bar(x, remote_0to1_latency, width, label='Remote (node 0→1)', color='#ff7f0e', alpha=0.8)
        ax.bar(x + width, remote_1to0_latency, width, label='Remote (node 1→0)', color='#d62728', alpha=0.8)

        # Add arrows showing latency increase from local to remote
        for i in range(len(sizes)):
            if local_latency[i] > 0 and remote_0to1_latency[i] > 0:
                # Calculate latency penalty percentage (higher latency is worse)
                penalty = ((remote_0to1_latency[i] - local_latency[i]) / local_latency[i]) * 100

                # Draw arrow from local bar to remote bar
                arrow_x_start = x[i] - width
                arrow_x_end = x[i]
                arrow_y_start = local_latency[i]
                arrow_y_end = remote_0to1_latency[i]

                # Add arrow annotation
                ax.annotate('', xy=(arrow_x_end, arrow_y_end), xytext=(arrow_x_start, arrow_y_start),
                           arrowprops=dict(arrowstyle='->', color='blue', lw=1.0, alpha=0.8))

                # Add penalty percentage text
                label = f'{penalty:+.0f}%'
                mid_x = (arrow_x_start + arrow_x_end) / 2
                mid_y = (arrow_y_start + arrow_y_end) / 2
                ax.text(mid_x, mid_y, label,
                       fontsize=9, color='blue', fontweight='bold',
                       ha='center', va='bottom', bbox=dict(boxstyle='round,pad=0.3',
                       facecolor='white', edgecolor='blue', alpha=0.8))

        ax.set_xlabel('Memory Allocation Size', fontsize=12, fontweight='bold')
        ax.set_ylabel('Average Latency (ns)', fontsize=12, fontweight='bold')
        ax.set_title(f'{pattern.capitalize()} Access', fontsize=12, fontweight='bold')
        ax.set_xticks(x)
        ax.tick_params(axis='x', labelsize=13)
        ax.set_xticklabels([format_size_label(s) for s in sizes], rotation=45, ha='right')
        ax.legend(fontsize=12, loc='lower right')
        ax.grid(True, alpha=0.3, axis='y')

    plt.suptitle('NUMA Latency Penalty: Local vs Remote Memory Access',
                 fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig('category2_latency_penalty.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: category2_latency_penalty.png")
    plt.show()

    # Print NUMA latency penalty percentages
    print("\n=== NUMA Latency Penalty Analysis ===")
    for pattern in patterns:
        print(f"\n{pattern.upper()} Access Pattern:")
        for size in sizes:
            if pattern in data[size]:
                local = data[size][pattern].get('local', 0)
                remote = data[size][pattern].get('remote_0to1', 0)
                if local > 0 and remote > 0:
                    penalty = ((remote - local) / local) * 100
                    print(f"  {size:4d} MB: +{penalty:5.1f}% latency increase for remote access")

if __name__ == '__main__':
    plot_latency_penalty()
