#!/bin/bash

# This boots the VM, runs numactl -H, prints output, and immediately returns to your host.
# Everything after -- is executed inside the VM as a command. This is super useful for quick testings.

# vng --cpus 8 -m 4G --numa 1G,cpus=0-1,cpus=3 --numa 3G,cpus=2,cpus=4-7 -- numactl -H

vng -r ~/linux --cpus 8 -m 4G --numa 1G,cpus=0-1,cpus=3 --numa 3G,cpus=2,cpus=4-7