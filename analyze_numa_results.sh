#!/bin/bash
RESULTS_DIR=$1

if [ -z "$RESULTS_DIR" ]; then
    echo "Usage: $0 <results_directory>"
    exit 1
fi

REPORT="${RESULTS_DIR}/ANALYSIS_REPORT.txt"

echo "================================================" > $REPORT
echo "NUMA Performance Analysis Report" >> $REPORT
echo "Generated: $(date)" >> $REPORT
echo "================================================" >> $REPORT
echo "" >> $REPORT

# Category 1: Memory Overflow Analysis
echo "1. MEMORY PRESSURE & FALLBACK BEHAVIOR" >> $REPORT
echo "----------------------------------------" >> $REPORT
for file in ${RESULTS_DIR}/membind_node0_*MB.txt; do
    if [ -f "$file" ]; then
        size=$(basename $file | grep -oP '\d+(?=MB)')
        time=$(grep "Time:" $file | awk '{print $2}')
        echo "  Size: ${size}MB - Time: ${time}s" >> $REPORT
    fi
done
echo "" >> $REPORT

# Category 2: Latency Comparison
echo "2. LOCAL VS REMOTE LATENCY" >> $REPORT
echo "----------------------------" >> $REPORT
local_lat=$(grep "Average latency:" ${RESULTS_DIR}/latency_local_node0.txt 2>/dev/null | awk '{print $3}')
remote_lat=$(grep "Average latency:" ${RESULTS_DIR}/latency_remote_node0to1.txt 2>/dev/null | awk '{print $3}')
if [ ! -z "$local_lat" ] && [ ! -z "$remote_lat" ]; then
    overhead=$(echo "scale=2; ($remote_lat - $local_lat) / $local_lat * 100" | bc)
    echo "  Local latency:  ${local_lat} ns" >> $REPORT
    echo "  Remote latency: ${remote_lat} ns" >> $REPORT
    echo "  Overhead:       ${overhead}%" >> $REPORT
fi
echo "" >> $REPORT

# Category 3: Policy Comparison
echo "3. POLICY PERFORMANCE COMPARISON" >> $REPORT
echo "----------------------------------" >> $REPORT
for policy in interleave localalloc membind; do
    file="${RESULTS_DIR}/${policy}*.txt"
    if ls $file 1> /dev/null 2>&1; then
        time=$(grep "Time:" $file | head -1 | awk '{print $2}')
        echo "  $policy: ${time}s" >> $REPORT
    fi
done
echo "" >> $REPORT

# Category 4: Multi-threaded Performance
echo "4. MULTI-THREADED PERFORMANCE" >> $REPORT
echo "-------------------------------" >> $REPORT
for file in ${RESULTS_DIR}/multithread_*.txt; do
    if [ -f "$file" ]; then
        config=$(basename $file .txt | sed 's/multithread_//')
        time=$(grep "Total parallel time:" $file | awk '{print $4}')
        echo "  $config: ${time}s" >> $REPORT
    fi
done
echo "" >> $REPORT

# Summary
echo "5. KEY FINDINGS" >> $REPORT
echo "----------------" >> $REPORT
echo "  See detailed results in individual test files" >> $REPORT
echo "  Memory pressure tests show fallback behavior" >> $REPORT
echo "  Remote access overhead quantified" >> $REPORT
echo "  Policy differences under various workloads measured" >> $REPORT
echo "" >> $REPORT

cat $REPORT
echo ""
echo "Full report saved to: $REPORT"
