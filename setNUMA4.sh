#!/bin/bash

vng -r ~/NUMA/linux --cpus 16 -m 16G \
  --numa 4G,cpus=0-3 \
  --numa 4G,cpus=4-7 \
  --numa 4G,cpus=8-11 \
  --numa 4G,cpus=12-15
