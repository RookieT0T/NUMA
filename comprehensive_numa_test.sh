#!/bin/bash
# advanced_numa_test.sh - Comprehensive NUMA characterization for OS project

BENCHMARK="./numa_test_advanced"
RESULTS="numa_results_advanced"
mkdir -p $RESULTS

# Create subdirectories for each test category
mkdir -p ${RESULTS}/Test1
mkdir -p ${RESULTS}/Test2
mkdir -p ${RESULTS}/Test3

# Get available memory per node (in MB)
NODE0_MEM=$(numactl --hardware | grep "node 0 size" | awk '{print $4}')
NODE1_MEM=$(numactl --hardware | grep "node 1 size" | awk '{print $4}')

echo "=========================================="
echo "Advanced NUMA Policy Characterization"
echo "=========================================="
echo "Node 0 Memory: ${NODE0_MEM} MB"
echo "Node 1 Memory: ${NODE1_MEM} MB"
echo ""

# Compile benchmark
gcc -O2 numa_test_advanced.c -o numa_test_advanced -lnuma
if [ $? -ne 0 ]; then
    echo "Compilation failed! Install libnuma-dev"
    exit 1
fi

# ==================================================
# Helper function to run tests with performance counters
# ==================================================
run_with_counters() {
    local output_file=$1
    shift  # Remove first arg, rest are command represented as "$@"

    # Capture vmstat before
    grep -E "numa_|pgmigrate" /proc/vmstat > ${output_file}.vmstat_before 2>/dev/null

    # Run with comprehensive perf counters
    # Hardware events: cache, TLB, page faults, L1 cache
    perf stat -e cache-misses,cache-references,page-faults,minor-faults,major-faults,dTLB-load-misses,dTLB-store-misses,L1-dcache-load-misses,L1-dcache-loads \
              -o ${output_file}.perf "$@" > $output_file 2>&1

    # Capture vmstat after
    grep -E "numa_|pgmigrate" /proc/vmstat > ${output_file}.vmstat_after 2>/dev/null

    # Append perf output to main result file
    echo "" >> $output_file
    echo "=== PERFORMANCE COUNTERS ===" >> $output_file
    cat ${output_file}.perf >> $output_file 2>/dev/null
}

# # ==================================================
# # TEST CATEGORY 1: Memory Pressure & Fallback Behavior with Access Patterns
# # ==================================================
# # To do list:
# # 1. memory pressure response curve: x-axis shows memory size; y-axis shows throughput and latency
# #    shows the breaking point where strict membind fails or slows v.s. preferred gracefully falls back
# # 2. access pattern sensitivity heatmap: rows show memory size; column show sequential, random, stride; color intensity shows performance degradation
# #    shows which access patterns are most affected by memory pressure
# echo "=========================================="
# echo "Category 1: Memory Pressure, Fallback & Access Patterns"
# echo "=========================================="

# # Generate test sizes from 512MB to 125% of node memory
# # Starting at 512MB to avoid cache-dominated behavior at small sizes
# TEST_SIZES=()
# CURRENT_SIZE=512
# MAX_SIZE=$((NODE0_MEM * 5 / 4))  # 125% of node memory

# # Generate exponentially spaced sizes
# while [ $CURRENT_SIZE -le $MAX_SIZE ]; do
#     TEST_SIZES+=($CURRENT_SIZE)
#     CURRENT_SIZE=$((CURRENT_SIZE * 2))
# done

# # Add 125% size if not already included
# if [ ${TEST_SIZES[-1]} -ne $MAX_SIZE ]; then
#     TEST_SIZES+=($MAX_SIZE)
# fi

# echo "Test sizes (MB): ${TEST_SIZES[@]}"
# echo ""

# # Access patterns to test
# ACCESS_PATTERNS=("sequential" "random" "stride")

# for size in "${TEST_SIZES[@]}"; do
#     echo ""
#     echo "=========================================="
#     echo "Testing with ${size}MB allocation"
#     echo "=========================================="

#     for pattern in "${ACCESS_PATTERNS[@]}"; do
#         echo ""
#         echo "  Access Pattern: $pattern"

#         # Test 1a: membind with various access patterns
#         echo "    - Strict membind to node 0"
#         run_with_counters ${RESULTS}/Test1/membind_node0_${size}MB_${pattern}.txt \
#             numactl --membind=0 --cpunodebind=0 $BENCHMARK $size $pattern

#         # Test 1b: preferred with overflow (should fallback gracefully)
#         echo "    - Preferred node 0 (may fallback)"
#         run_with_counters ${RESULTS}/Test1/preferred_node0_${size}MB_${pattern}.txt \
#             numactl --preferred=0 --cpunodebind=0 $BENCHMARK $size $pattern

#         sleep 0.5
#     done
# done

# # ==================================================
# # TEST CATEGORY 2: Cross-Node Access Patterns
# # ==================================================
# # To do list:
# # 1. NUMA penalty bar chart: grouped bars for each memory size; compare local and remote accesses; show performance degration; split by access pattern
# # 2. Access pattern impact on NUMA distance: memory allocation size on X; remote/local performance ratio on y; lines of each access pattern;
# echo ""
# echo "=========================================="
# echo "Category 2: Cross-Node Memory Access"
# echo "=========================================="

# for size in "${TEST_SIZES[@]}"; do
#     echo ""
#     echo "=========================================="
#     echo "Testing Cross-Node Access with ${size}MB"
#     echo "=========================================="

#     for pattern in "${ACCESS_PATTERNS[@]}"; do
#         echo ""
#         echo "  Access Pattern: $pattern"

#         # Test 2a: Local access (node 0 -> node 0)
#         echo "    - Testing local memory (node 0 -> node 0)"
#         run_with_counters ${RESULTS}/Test2/local_node0_${size}MB_${pattern}.txt \
#             numactl --membind=0 --cpunodebind=0 $BENCHMARK $size $pattern

#         # Test 2b: Remote access (node 0 -> node 1)
#         echo "    - Testing remote memory (node 0 -> node 1)"
#         run_with_counters ${RESULTS}/Test2/remote_node0to1_${size}MB_${pattern}.txt \
#             numactl --membind=1 --cpunodebind=0 $BENCHMARK $size $pattern

#         # Test 2c: Remote access (node 1 -> node 0)
#         echo "    - Testing remote memory (node 1 -> node 0)"
#         run_with_counters ${RESULTS}/Test2/remote_node1to0_${size}MB_${pattern}.txt \
#             numactl --membind=0 --cpunodebind=1 $BENCHMARK $size $pattern

#         sleep 0.5
#     done
# done

# # ==================================================
# # TEST CATEGORY 3: Policy Comparison Under Load
# # ==================================================
# echo ""
# echo "=========================================="
# echo "Category 3: Policy Performance Under Load"
# echo "=========================================="

# for size in "${TEST_SIZES[@]}"; do
#     echo ""
#     echo "=========================================="
#     echo "Testing Policy Comparison with ${size}MB"
#     echo "=========================================="

#     for pattern in "${ACCESS_PATTERNS[@]}"; do
#         echo ""
#         echo "  Access Pattern: $pattern"

#         # Test 3a: interleave vs local allocation
#         echo "    - Interleave across all nodes"
#         run_with_counters ${RESULTS}/Test3/interleave_all_${size}MB_${pattern}.txt \
#             numactl --interleave=all --cpunodebind=0 $BENCHMARK $size $pattern

#         echo "    - Local allocation"
#         run_with_counters ${RESULTS}/Test3/localalloc_node0_${size}MB_${pattern}.txt \
#             numactl --localalloc --cpunodebind=0 $BENCHMARK $size $pattern

#         echo "    - Strict membind to node 0"
#         run_with_counters ${RESULTS}/Test3/membind_strict_node0_${size}MB_${pattern}.txt \
#             numactl --membind=0 --cpunodebind=0 $BENCHMARK $size $pattern

#         # Test 3b: Preferred with different preferred nodes (mismatched CPU/memory)
#         echo "    - Preferred node 0, CPU on node 1"
#         run_with_counters ${RESULTS}/Test3/preferred_node0_cpu_node1_${size}MB_${pattern}.txt \
#             numactl --preferred=0 --cpunodebind=1 $BENCHMARK $size $pattern

#         echo "    - Preferred node 1, CPU on node 0"
#         run_with_counters ${RESULTS}/Test3/preferred_node1_cpu_node0_${size}MB_${pattern}.txt \
#             numactl --preferred=1 --cpunodebind=0 $BENCHMARK $size $pattern

#         sleep 0.5
#     done
# done

# ==================================================
# TEST CATEGORY 4: NUMA Page Migration
# ==================================================
echo ""
echo "=========================================="
echo "Category 4: NUMA Page Migration"
echo "=========================================="

# Check if auto-NUMA is enabled
AUTO_NUMA=$(cat /proc/sys/kernel/numa_balancing 2>/dev/null || echo "0")
echo "Auto-NUMA status: $AUTO_NUMA"
if [ "$AUTO_NUMA" != "1" ]; then
    echo "WARNING: Auto-NUMA is disabled. Enable with: echo 1 | sudo tee /proc/sys/kernel/numa_balancing"
fi

mkdir -p ${RESULTS}/Test4

# Migration test sizes - larger sizes to exceed typical TLB/cache coverage
# Use sizes that represent realistic workloads where migration matters
MIGRATION_SIZES=(16384)  # 16GB - significant enough to trigger migration

# Test 4a: Auto-NUMA Migration (Misallocated Pages)
echo ""
echo "Test 4a: Auto-NUMA Migration Timeline (16GB only)"
echo "--------------------------------------------------"
# Only test 16GB for detailed migration timeline (samples every iteration)
MIGRATION_TEST_SIZE=16384

echo "  Testing auto-NUMA migration with fine-grained timeline: ${MIGRATION_TEST_SIZE}MB"
# No memory policy - C code creates mismatch, Auto-NUMA fixes it
run_with_counters ${RESULTS}/Test4/auto_numa_${MIGRATION_TEST_SIZE}MB_timeline.txt \
    numactl --cpunodebind=0 $BENCHMARK $MIGRATION_TEST_SIZE migrate

sleep 1

# Test 4b: Migration Cost Comparison (simplified - removed pressure test)
echo ""
echo "Test 4c: Migration Cost Comparison"
echo "------------------------------------"
for size in "${MIGRATION_SIZES[@]}"; do
    echo "  Comparing migration cost: ${size}MB"

    # Baseline: Local allocation (best case)
    echo "    - Baseline local allocation"
    run_with_counters ${RESULTS}/Test4/baseline_local_${size}MB.txt \
        numactl --membind=0 --cpunodebind=0 $BENCHMARK $size sequential

    # Static remote: No migration allowed (disable auto-NUMA temporarily would be ideal, but we'll use membind)
    echo "    - Static remote (no migration)"
    run_with_counters ${RESULTS}/Test4/static_remote_${size}MB.txt \
        numactl --membind=1 --cpunodebind=0 $BENCHMARK $size sequential

    # Auto-NUMA: Start remote, allow migration
    echo "    - Auto-migrated (start remote, migrate to local)"
    # No memory policy - C code creates mismatch, Auto-NUMA fixes it
    run_with_counters ${RESULTS}/Test4/auto_migrated_${size}MB.txt \
        numactl --cpunodebind=0 $BENCHMARK $size migrate

    sleep 1
done

echo ""
echo "=========================================="
echo "All tests complete!"
echo "Results in: $RESULTS/"