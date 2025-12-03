#!/usr/bin/env python3
"""
Test Category 4: NUMA Page Migration Visualizations
- Migration timeline showing page distribution over time
- Migration cost comparison (baseline vs static vs auto-migrated)
"""

import os
import re
import matplotlib.pyplot as plt
import numpy as np

RESULTS_DIR = "numa_results_advanced/Test4"

def parse_migration_timeline(filepath):
    """Parse migration test output to extract timeline data"""
    try:
        with open(filepath, 'r') as f:
            content = f.read()

        data = {
            'iteration': [],
            'time': [],
            'node0_pct': [],
            'node1_pct': [],
            'status': []
        }

        # Find the CSV section (match both old and new formats)
        csv_match = re.search(r'(Time\(s\)|Iteration), .*Node0%, Node1%, Status\n(.*?)Final distribution',
                             content, re.DOTALL)

        if csv_match:
            csv_lines = csv_match.group(2).strip().split('\n')
            for line in csv_lines:
                parts = line.split(',')
                if len(parts) >= 4:
                    try:
                        # New format: Iteration, IterTime(s), Node0%, Node1%, Status
                        # Old format: Time(s), Node0%, Node1%, Status
                        if len(parts) >= 5:  # New format
                            iteration = int(parts[0].strip())
                            iter_time = float(parts[1].strip())
                            node0 = int(parts[2].strip())
                            node1 = int(parts[3].strip())
                            status = parts[4].strip() if len(parts) > 4 else ''
                            data['iteration'].append(iteration)
                            data['time'].append(iter_time)  # Per-iteration time
                        else:  # Old format (no iteration number)
                            time_s = float(parts[0].strip())
                            node0 = int(parts[1].strip())
                            node1 = int(parts[2].strip())
                            status = parts[3].strip() if len(parts) > 3 else ''
                            data['iteration'].append(len(data['iteration']))  # Infer iteration
                            data['time'].append(time_s)

                        data['node0_pct'].append(node0)
                        data['node1_pct'].append(node1)
                        data['status'].append(status)
                    except ValueError:
                        continue

        # Also extract performance counters
        perf_counters = {}

        # Extract key performance counters
        dtlb_load_match = re.search(r'([\d,]+)\s+dTLB-load-misses', content)
        dtlb_store_match = re.search(r'([\d,]+)\s+dTLB-store-misses', content)
        page_faults_match = re.search(r'([\d,]+)\s+page-faults', content)
        cache_misses_match = re.search(r'([\d,]+)\s+cache-misses', content)
        time_elapsed_match = re.search(r'([\d.]+)\s+seconds time elapsed', content)
        user_time_match = re.search(r'([\d.]+)\s+seconds user', content)
        sys_time_match = re.search(r'([\d.]+)\s+seconds sys', content)

        if dtlb_load_match:
            perf_counters['dtlb_load_misses'] = int(dtlb_load_match.group(1).replace(',', ''))
        if dtlb_store_match:
            perf_counters['dtlb_store_misses'] = int(dtlb_store_match.group(1).replace(',', ''))
        if page_faults_match:
            perf_counters['page_faults'] = int(page_faults_match.group(1).replace(',', ''))
        if cache_misses_match:
            perf_counters['cache_misses'] = int(cache_misses_match.group(1).replace(',', ''))
        if time_elapsed_match:
            perf_counters['time_elapsed'] = float(time_elapsed_match.group(1))
        if user_time_match:
            perf_counters['user_time'] = float(user_time_match.group(1))
        if sys_time_match:
            perf_counters['sys_time'] = float(sys_time_match.group(1))

        data['perf_counters'] = perf_counters

        return data if data['time'] else None
    except:
        return None

def parse_sequential_test(filepath):
    """Parse sequential test results for cost comparison"""
    try:
        with open(filepath, 'r') as f:
            content = f.read()

        # Extract throughput and time
        throughput_match = re.search(r'Throughput:\s+([\d.]+)\s+MB/s', content)
        latency_match = re.search(r'Average latency:\s+([\d.]+)\s+ns', content)
        time_match = re.search(r'time elapsed\s*\n\s+([\d.]+)\s+seconds', content)

        result = {}
        if throughput_match:
            result['throughput'] = float(throughput_match.group(1))
        if latency_match:
            result['latency'] = float(latency_match.group(1))
        if time_match:
            result['time'] = float(time_match.group(1))

        return result if result else None
    except:
        return None

def parse_migration_test(filepath):
    """Parse migration test results"""
    try:
        with open(filepath, 'r') as f:
            content = f.read()

        # Extract time from migration test
        time_match = re.search(r'Time:\s+([\d.]+)\s+seconds', content)
        elapsed_match = re.search(r'([\d.]+)\s+seconds time elapsed', content)

        result = {}
        if time_match:
            result['time'] = float(time_match.group(1))
        elif elapsed_match:
            result['time'] = float(elapsed_match.group(1))

        return result if result else None
    except:
        return None

def plot_migration_timeline():
    """Generate migration timeline visualization with two separate graphs"""
    # Collect data for all sizes
    sizes = []
    timelines = {}

    for filename in os.listdir(RESULTS_DIR):
        # Match both old and new naming patterns
        match = re.match(r'auto_(migrated|numa)_(\d+)MB(_timeline)?\.txt', filename)
        if match:
            size_mb = int(match.group(2))
            filepath = os.path.join(RESULTS_DIR, filename)
            data = parse_migration_timeline(filepath)

            if data and data['time']:
                sizes.append(size_mb)
                timelines[size_mb] = data

    if not sizes:
        print("No migration timeline data found")
        return

    sizes.sort()

    # Create visualization for each size
    for size_mb in sizes:
        data = timelines[size_mb]

        iterations = np.array(data['iteration'])
        iter_times = np.array(data['time'])
        node0 = np.array(data['node0_pct'])
        node1 = np.array(data['node1_pct'])
        statuses = data['status']

        # Create figure with 2 subplots (vertically stacked, equal height, tighter spacing)
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10),
                                        gridspec_kw={'height_ratios': [1, 1], 'hspace': 0.25})

        size_label = f"{size_mb // 1024} GB" if size_mb >= 1024 else f"{size_mb} MB"

        # ========== TOP PANEL: Per-Iteration Latency ==========

        # Plot per-iteration latency
        ax1.plot(iterations, iter_times, color='#1f77b4',
                linewidth=2.5, marker='o', markersize=2, label='Per-iteration Latency')

        ax1.set_ylabel('Latency per Iteration (seconds)', fontsize=12, fontweight='bold')
        ax1.set_title(f'Test Category 4: Auto-NUMA Migration Timeline ({size_label})\n' +
                     'Per-Iteration Access Latency',
                     fontsize=14, fontweight='bold', pad=15)
        ax1.grid(True, alpha=0.3, axis='both')
        ax1.set_xlim([0, iterations[-1]])

        # Add background coloring for status phases
        phase_colors = {
            'All_Remote': '#ffaaaa',  # Darker red
            'Migrating': '#ffee88',   # Darker yellow
            'All_Local': '#aaffaa'    # Darker green
        }

        current_status = None
        phase_start = 0

        for i, status in enumerate(statuses):
            if status != current_status:
                if current_status is not None and current_status in phase_colors:
                    # Draw the previous phase
                    ax1.axvspan(iterations[phase_start], iterations[i-1],
                               color=phase_colors[current_status], alpha=1, zorder=0)
                    ax2.axvspan(iterations[phase_start], iterations[i-1],
                               color=phase_colors[current_status], alpha=1, zorder=0)
                current_status = status
                phase_start = i

        # Draw the last phase
        if current_status in phase_colors:
            ax1.axvspan(iterations[phase_start], iterations[-1],
                       color=phase_colors[current_status], alpha=1, zorder=0)
            ax2.axvspan(iterations[phase_start], iterations[-1],
                       color=phase_colors[current_status], alpha=1, zorder=0)

        # Mark key transition points
        migration_start_iter = None
        migration_complete_iter = None

        for i, (n0, status) in enumerate(zip(node0, statuses)):
            if migration_start_iter is None and status == 'Migrating':
                migration_start_iter = iterations[i]
            if migration_complete_iter is None and status == 'All_Local':
                migration_complete_iter = iterations[i]
                break

        if migration_start_iter is not None:
            ax1.axvline(x=migration_start_iter, color='black', linestyle='--',
                       linewidth=2, alpha=0.8, label='Migration Start')

        if migration_complete_iter is not None:
            ax1.axvline(x=migration_complete_iter, color='black', linestyle='-.',
                       linewidth=2, alpha=0.8, label='Migration Complete')

        ax1.legend(fontsize=10, loc='upper right', framealpha=0.9)

        # Add phase explanation at the top
        phase_text = (
            "Red: All Remote (100% Node 1)  |  "
            "Yellow: Migrating  |  "
            "Green: All Local (100% Node 0)"
        )
        ax1.text(0.5, 0.9, phase_text, transform=ax1.transAxes,
                fontsize=10, horizontalalignment='center',
                bbox=dict(boxstyle='round', facecolor='white',
                         edgecolor='gray', alpha=0.9))

        # Add annotation showing speedup
        initial_latency = iter_times[0]
        final_latency = np.median(iter_times[-50:])  # Median of last 50 iterations
        speedup = initial_latency / final_latency

        # annotation_text = (
        #     f"Initial latency: {initial_latency:.3f}s (all remote)\n"
        #     f"Final latency: {final_latency:.3f}s (all local)\n"
        #     f"Speedup: {speedup:.1f}×"
        # )
        # ax1.text(0.98, 0.98, annotation_text, transform=ax1.transAxes,
        #         fontsize=10, verticalalignment='top', horizontalalignment='right',
        #         bbox=dict(boxstyle='round', facecolor='lightyellow',
        #                  edgecolor='black', alpha=0.9))

        # ========== BOTTOM PANEL: Page Distribution ==========

        # Plot stacked area for page distribution (use blue/orange to distinguish from red/yellow/green backgrounds)
        ax2.fill_between(iterations, node0, 100, color='#ff7f0e', alpha=1, label='Remote (Node 1)')  # Orange
        ax2.fill_between(iterations, 0, node0, color='#1f77b4', alpha=1, label='Local (Node 0)')  # Blue

        ax2.set_xlabel('Iteration', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Page Distribution (%)', fontsize=12, fontweight='bold')
        ax2.set_title('Page Distribution Over Time', fontsize=14, fontweight='bold', pad=15)
        ax2.set_ylim([0, 100])
        ax2.set_xlim([0, iterations[-1]])
        ax2.grid(True, alpha=0.3, axis='both')
        ax2.legend(fontsize=10, loc='center right', framealpha=0.9)

        # Mark transition points on bottom panel too
        if migration_start_iter is not None:
            ax2.axvline(x=migration_start_iter, color='black', linestyle='--',
                       linewidth=2, alpha=0.8)

        if migration_complete_iter is not None:
            ax2.axvline(x=migration_complete_iter, color='black', linestyle='-.',
                       linewidth=2, alpha=0.8)

        plt.tight_layout()
        filename = f'category4_migration_timeline_{size_mb}MB.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"✓ Saved: {filename}")
        plt.close()

def plot_migration_cost():
    """Generate migration cost comparison visualization"""
    sizes = []
    baseline_times = {}
    static_times = {}
    migrated_times = {}

    # Collect data
    for filename in os.listdir(RESULTS_DIR):
        baseline_match = re.match(r'baseline_local_(\d+)MB\.txt', filename)
        static_match = re.match(r'static_remote_(\d+)MB\.txt', filename)
        migrated_match = re.match(r'auto_migrated_(\d+)MB\.txt', filename)

        if baseline_match:
            size_mb = int(baseline_match.group(1))
            filepath = os.path.join(RESULTS_DIR, filename)
            result = parse_sequential_test(filepath)
            if result and 'time' in result:
                if size_mb not in sizes:
                    sizes.append(size_mb)
                baseline_times[size_mb] = result['time']

        elif static_match:
            size_mb = int(static_match.group(1))
            filepath = os.path.join(RESULTS_DIR, filename)
            result = parse_sequential_test(filepath)
            if result and 'time' in result:
                static_times[size_mb] = result['time']

        elif migrated_match:
            size_mb = int(migrated_match.group(1))
            filepath = os.path.join(RESULTS_DIR, filename)
            result = parse_migration_test(filepath)
            if result and 'time' in result:
                migrated_times[size_mb] = result['time']

    if not sizes:
        print("No migration cost data found")
        return

    sizes.sort()

    # Filter sizes that have all three measurements
    valid_sizes = [s for s in sizes if s in baseline_times and s in static_times and s in migrated_times]

    if not valid_sizes:
        print("No complete data sets found")
        return

    # Prepare data
    size_labels = [f"{s // 1024} GB" if s >= 1024 else f"{s} MB" for s in valid_sizes]
    baseline = [baseline_times[s] for s in valid_sizes]
    static = [static_times[s] for s in valid_sizes]
    migrated = [migrated_times[s] for s in valid_sizes]

    # Create bar chart
    fig, ax = plt.subplots(figsize=(14, 8))

    x = np.arange(len(valid_sizes))
    width = 0.25

    bars1 = ax.bar(x - width, baseline, width, label='Baseline Local\n(Mem=Node0, CPU=Node0)',
                   color='#2ca02c', alpha=0.8)
    bars2 = ax.bar(x, static, width, label='Static Remote\n(Mem=Node1, CPU=Node0, No Migration)',
                   color='#ff7f0e', alpha=0.8)
    bars3 = ax.bar(x + width, migrated, width, label='Auto-Migrated\n(Start Remote → Migrate to Local)',
                   color='#d62728', alpha=0.8)

    # Add value labels on bars
    def add_labels(bars):
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}s',
                   ha='center', va='bottom', fontsize=9, fontweight='bold')

    add_labels(bars1)
    add_labels(bars2)
    add_labels(bars3)

    # Add overhead percentages
    for i, size in enumerate(valid_sizes):
        base = baseline[i]
        mig = migrated[i]
        overhead_pct = ((mig - base) / base) * 100 if base > 0 else 0

        # Draw arrow from baseline to migrated
        y_pos = max(base, mig) * 1.1
        ax.annotate('', xy=(i + width, mig), xytext=(i - width, base),
                   arrowprops=dict(arrowstyle='<->', color='purple', lw=2, alpha=0.6))
        ax.text(i, y_pos, f'+{overhead_pct:.0f}%\noverhead',
               ha='center', va='bottom', fontsize=10, color='purple', fontweight='bold',
               bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                        edgecolor='purple', alpha=0.8))

    # Formatting
    ax.set_xlabel('Memory Size', fontsize=12, fontweight='bold')
    ax.set_ylabel('Execution Time (seconds)', fontsize=12, fontweight='bold')
    ax.set_title('Test Category 4: Migration Cost Comparison\nBaseline vs Static Remote vs Auto-Migrated',
                fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(size_labels, fontsize=11)
    ax.legend(fontsize=10, loc='upper left')
    ax.grid(True, alpha=0.3, axis='y')

    # Add explanation box
    explanation = ("Migration overhead includes:\n"
                  "• Manual page movement to remote node\n"
                  "• 50 iterations of full array access\n"
                  "• Auto-NUMA scanning & migration\n"
                  "• TLB shootdowns during migration")
    ax.text(0.98, 0.97, explanation,
           transform=ax.transAxes, fontsize=9,
           verticalalignment='top', horizontalalignment='right',
           bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))

    plt.tight_layout()
    plt.savefig('category4_migration_cost.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: category4_migration_cost.png")
    plt.close()

if __name__ == '__main__':
    print("Generating Test Category 4 visualizations...\n")
    plot_migration_timeline()
    plot_migration_cost()
    print("\n✓ Test Category 4 visualization complete!")
