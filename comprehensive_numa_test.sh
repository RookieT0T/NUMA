#!/bin/bash
# advanced_numa_test.sh - Comprehensive NUMA characterization for OS project

BENCHMARK="./numa_test_advanced"
RESULTS="numa_results_advanced"
mkdir -p $RESULTS

# Create subdirectories for each test category
mkdir -p ${RESULTS}/category1_memory_pressure
mkdir -p ${RESULTS}/category2_cross_node
mkdir -p ${RESULTS}/category3_policy_comparison

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
# TEST CATEGORY 1: Memory Pressure & Fallback Behavior with Access Patterns
# ==================================================
echo "=========================================="
echo "Category 1: Memory Pressure, Fallback & Access Patterns"
echo "=========================================="

# Generate test sizes from 128MB to 125% of node memory
TEST_SIZES=(128)
CURRENT_SIZE=256
MAX_SIZE=$((NODE0_MEM * 5 / 4))  # 125% of node memory

# Generate exponentially spaced sizes
while [ $CURRENT_SIZE -le $MAX_SIZE ]; do
    TEST_SIZES+=($CURRENT_SIZE)
    CURRENT_SIZE=$((CURRENT_SIZE * 2))
done

# Add 125% size if not already included
if [ ${TEST_SIZES[-1]} -ne $MAX_SIZE ]; then
    TEST_SIZES+=($MAX_SIZE)
fi

echo "Test sizes (MB): ${TEST_SIZES[@]}"
echo ""

# Access patterns to test
ACCESS_PATTERNS=("sequential" "random" "stride")

for size in "${TEST_SIZES[@]}"; do
    echo ""
    echo "=========================================="
    echo "Testing with ${size}MB allocation"
    echo "=========================================="

    for pattern in "${ACCESS_PATTERNS[@]}"; do
        echo ""
        echo "  Access Pattern: $pattern"

        # Test 1a: membind with various access patterns
        echo "    - Strict membind to node 0"
        numactl --membind=0 --cpunodebind=0 $BENCHMARK $size $pattern > ${RESULTS}/category1_memory_pressure/membind_node0_${size}MB_${pattern}.txt 2>&1

        # Test 1b: preferred with overflow (should fallback gracefully)
        echo "    - Preferred node 0 (may fallback)"
        numactl --preferred=0 --cpunodebind=0 $BENCHMARK $size $pattern > ${RESULTS}/category1_memory_pressure/preferred_node0_${size}MB_${pattern}.txt 2>&1

        sleep 0.5
    done
done

# ==================================================
# TEST CATEGORY 2: Cross-Node Access Patterns
# ==================================================
echo ""
echo "=========================================="
echo "Category 2: Cross-Node Memory Access"
echo "=========================================="

for size in "${TEST_SIZES[@]}"; do
    echo ""
    echo "=========================================="
    echo "Testing Cross-Node Access with ${size}MB"
    echo "=========================================="

    for pattern in "${ACCESS_PATTERNS[@]}"; do
        echo ""
        echo "  Access Pattern: $pattern"

        # Test 2a: Local access (node 0 -> node 0)
        echo "    - Testing local memory (node 0 -> node 0)"
        numactl --membind=0 --cpunodebind=0 $BENCHMARK $size $pattern > ${RESULTS}/category2_cross_node/local_node0_${size}MB_${pattern}.txt 2>&1

        # Test 2b: Remote access (node 0 -> node 1)
        echo "    - Testing remote memory (node 0 -> node 1)"
        numactl --membind=1 --cpunodebind=0 $BENCHMARK $size $pattern > ${RESULTS}/category2_cross_node/remote_node0to1_${size}MB_${pattern}.txt 2>&1

        # Test 2c: Remote access (node 1 -> node 0)
        echo "    - Testing remote memory (node 1 -> node 0)"
        numactl --membind=0 --cpunodebind=1 $BENCHMARK $size $pattern > ${RESULTS}/category2_cross_node/remote_node1to0_${size}MB_${pattern}.txt 2>&1

        sleep 0.5
    done
done

# ==================================================
# TEST CATEGORY 3: Policy Comparison Under Load
# ==================================================
echo ""
echo "=========================================="
echo "Category 3: Policy Performance Under Load"
echo "=========================================="

for size in "${TEST_SIZES[@]}"; do
    echo ""
    echo "=========================================="
    echo "Testing Policy Comparison with ${size}MB"
    echo "=========================================="

    for pattern in "${ACCESS_PATTERNS[@]}"; do
        echo ""
        echo "  Access Pattern: $pattern"

        # Test 3a: interleave vs local allocation
        echo "    - Interleave across all nodes"
        numactl --interleave=all --cpunodebind=0 $BENCHMARK $size $pattern > ${RESULTS}/category3_policy_comparison/interleave_all_${size}MB_${pattern}.txt 2>&1

        echo "    - Local allocation"
        numactl --localalloc --cpunodebind=0 $BENCHMARK $size $pattern > ${RESULTS}/category3_policy_comparison/localalloc_node0_${size}MB_${pattern}.txt 2>&1

        echo "    - Strict membind to node 0"
        numactl --membind=0 --cpunodebind=0 $BENCHMARK $size $pattern > ${RESULTS}/category3_policy_comparison/membind_strict_node0_${size}MB_${pattern}.txt 2>&1

        # Test 3b: Preferred with different preferred nodes (mismatched CPU/memory)
        echo "    - Preferred node 0, CPU on node 1"
        numactl --preferred=0 --cpunodebind=1 $BENCHMARK $size $pattern > ${RESULTS}/category3_policy_comparison/preferred_node0_cpu_node1_${size}MB_${pattern}.txt 2>&1

        echo "    - Preferred node 1, CPU on node 0"
        numactl --preferred=1 --cpunodebind=0 $BENCHMARK $size $pattern > ${RESULTS}/category3_policy_comparison/preferred_node1_cpu_node0_${size}MB_${pattern}.txt 2>&1

        sleep 0.5
    done
done

# # ==================================================
# # TEST CATEGORY 4: Multi-threaded NUMA Behavior
# # ==================================================
# echo ""
# echo "=========================================="
# echo "Category 4: Multi-threaded Workloads"
# echo "=========================================="

# # ==================================================
# # TEST CATEGORY 5: Page Migration and Auto-NUMA
# # ==================================================
# echo ""
# echo "=========================================="
# echo "Category 5: Dynamic Page Migration"
# echo "=========================================="

# # Check if auto-NUMA is enabled
# AUTO_NUMA=$(cat /proc/sys/kernel/numa_balancing 2>/dev/null)
# echo "Auto-NUMA status: $AUTO_NUMA"

# # Test 5a: Initial allocation on wrong node, let kernel migrate
# echo "Testing page migration (allocate on node 1, compute on node 0)..."
# numactl --membind=1 --cpunodebind=0 $BENCHMARK 2048 migrate > ${RESULTS}/page_migration_test.txt 2>&1

# # Monitor migration statistics
# grep -E "numa_hint|numa_pages_migrated|pgmigrate" /proc/vmstat > ${RESULTS}/vmstat_migration.txt

echo ""
echo "=========================================="
echo "All tests complete!"
echo "Results in: $RESULTS/"
echo "=========================================="

# Generate analysis summary
./analyze_numa_results.sh $RESULTS