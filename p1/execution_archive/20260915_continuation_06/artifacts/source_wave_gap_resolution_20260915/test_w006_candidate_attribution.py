#!/usr/bin/env python3
from run_w006_candidate_attribution import classify, DFA, JPM
assert classify({DFA}) == "DFA_ONLY"
assert classify({JPM}) == "JPM_ONLY"
assert classify({DFA,JPM}) == "BOTH_DFA_AND_JPM"
assert classify(set()).startswith("NEITHER")
assert classify({"S_OTHER"}).startswith("UNKNOWN")
print("5 fixtures PASS")
