# P1 SEC/N-PORT working files

Current Gate0 authority in this directory:

- `nport_gate0_event_level.csv`
- `nport_gate0_failure_list.csv`
- `nport_gate0_summary.csv`
- `gate0_predecessor_continuity.csv`
- `nport_gate0.py` and supporting HTTP/date code

The old `build_nport_convexp.py`, its logs/crosswalk/NEED_HUMAN outputs, and
denominator-recovery files are retained only to reproduce the legacy
131-event/389-stock ConvExp baseline. Current treatment construction begins
with `p1/exposure/build_nport_pre_holdings.py` and uses the selected Gate0 PRE
reports; POST holdings are never used in treatment.
