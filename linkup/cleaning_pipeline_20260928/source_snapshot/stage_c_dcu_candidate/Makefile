HIPCC ?= hipcc
GPU_ARCH ?= gfx906
CXXFLAGS ?= -O3 -std=c++14

dcu_anchor_scan: dcu_anchor_scan.hip.cpp
	$(HIPCC) $(CXXFLAGS) --offload-arch=$(GPU_ARCH) $< -o $@

clean:
	rm -f dcu_anchor_scan

