"""Independent arithmetic; only pinned, explicit metadata projections are parsed."""
from pathlib import Path
import importlib.util
import hashlib
import json
from collections import Counter, defaultdict
from datetime import time
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

design = module('design_specs', ROOT/'design/build_design.py')
nominal = module('nominal_specs', ROOT/'nominal_clock/count_v1_metadata_pool.py')
manifest = {}

def read(path, expected, columns):
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual == expected, path
    assert columns
    frame = pd.read_csv(path, usecols=columns, dtype=str)
    if 'permno' in columns:
        numeric = pd.to_numeric(frame['permno'], errors='raise')
        assert numeric.notna().all() and numeric.mod(1).eq(0).all()
        frame['permno'] = numeric.astype('int64').astype(str)
    manifest[str(path)] = {'sha256': actual, 'usecols': columns}
    return frame

def source(key):
    item = design.INPUTS[key]
    return read(item['path'], item['expected'], item['usecols'])

def flag(x):
    assert str(x).lower() in ['true', 'false']
    return str(x).lower() == 'true'

def band(value):
    try:
        clock = time.fromisoformat(str(value).strip())
        return time(9, 30) <= clock <= time(15)
    except ValueError:
        return False

v1, overlap, inter, events, acq = [source(k) for k in ['v1_population', 'overlap_clean_pool', 'clean_analyst_intersection', 'event_metadata', 'acquisition_union']]
keys = ['wave_id', 'permno', 'provisional_tier']
assert not any(f.duplicated(keys).any() for f in [v1, overlap, inter])
v1_supported = {tuple(r[k] for k in keys) for r in v1.to_dict('records') if flag(r['has_8pre_4post'])}
overlap_map = {tuple(r[k] for k in keys): flag(r['proposed_overlap_clean']) for r in overlap.to_dict('records')}
inter_map = {tuple(r[k] for k in keys): r for r in inter.to_dict('records')}
assert v1_supported == set(overlap_map) == set(inter_map)
assert all(overlap_map[k] == flag(r['proposed_overlap_clean']) for k, r in inter_map.items())
assert all(flag(r['clean_and_analyst12']) == (flag(r['proposed_overlap_clean']) and flag(r['all_12_events_min2'])) for r in inter_map.values())
counts = dict(v1=len(v1), support=len(v1_supported), clean=sum(overlap_map.values()), all12=sum(flag(r['all_12_events_min2']) for r in inter_map.values()), clean_all12=sum(flag(r['clean_and_analyst12']) for r in inter_map.values()))
assert list(counts.values()) == [2592, 2088, 508, 895, 182]
tiers, v2 = source('v2_tier_projection'), source('v2_population')
assert not tiers.duplicated(['wave_id', 'permno']).any()
tierkeys = {(r.wave_id, r.permno): r.provisional_tier.lower() for r in tiers.itertuples()}
tailkeys = {k for k, tier in tierkeys.items() if tier in ['high', 'low']}
represented_v1 = {(r.wave_id, r.permno) for r in v1.itertuples()}
represented_v2 = {(r.wave_id, r.permno) for r in v2.itertuples()}
assert represented_v1 <= tailkeys and represented_v2 <= set(tierkeys)
missing_tail = Counter(f'{wave}/{tierkeys[(wave, permno)]}' for wave, permno in tailkeys - represented_v1)
universe = dict(projected_all_tiers=len(tierkeys), projected_tail=len(tailkeys), represented_v1=len(represented_v1), tail_not_represented=len(tailkeys-represented_v1), represented_v2=len(represented_v2), v2_supported=sum(flag(x) for x in v2.has_8pre_4post), all_tiers_not_represented=len(set(tierkeys)-represented_v2), missing_tail_by_wave_tier=missing_tail)
assert [universe[k] for k in ['projected_all_tiers','projected_tail','represented_v1','tail_not_represented','represented_v2','all_tiers_not_represented']] == [4191,2794,2592,202,4186,5]
assert universe['v2_supported'] == 3246

frames = {}
for name, (filename, expected, columns) in nominal.SPECS.items():
    frames[name] = read(nominal.MD/filename, expected, columns)
eventkeys = nominal.KEYS
pool_rows = frames['pool'].to_dict('records')
analyst_rows = frames['analyst'].to_dict('records')
pool_map = {tuple(r[k] for k in eventkeys): r for r in pool_rows}
analyst_map = {tuple(r[k] for k in eventkeys): flag(r['analyst_min2']) for r in analyst_rows}
assert len(pool_map) == len(pool_rows) == len(analyst_map) == len(analyst_rows) == 29729
assert set(pool_map) == set(analyst_map)
stages = {s: Counter() for s in ['all_capped', 'supported', 'clean', 'clean_all12']}
both_sides = defaultdict(lambda: defaultdict(set))
for key, row in pool_map.items():
    stock_key = key[:3]
    entry = inter_map.get(stock_key)
    names = ['all_capped']
    if entry:
        names.append('supported')
        if flag(entry['proposed_overlap_clean']):
            names.append('clean')
            if flag(entry['all_12_events_min2']):
                names.append('clean_all12')
    in_band, min2 = band(row['anntims']), analyst_map[key]
    for name in names:
        stages[name].update(rows=1, nominal=int(in_band), nominal_min2=int(in_band and min2))
    if 'clean' in names and in_band and min2:
        both_sides[(row['wave_id'], row['provisional_tier'])][row['event_side']].add(row['permno'])
clean_both = {f'{wave}/{tier}': len(both_sides[(wave, tier)]['PRE'] & both_sides[(wave, tier)]['POST']) for wave, tier in sorted({(r['wave_id'], r['provisional_tier']) for r in pool_rows})}
assert stages['all_capped'] == {'rows': 29729, 'nominal': 465, 'nominal_min2': 207}
assert stages['clean'] == {'rows': 6096, 'nominal': 101, 'nominal_min2': 38}
assert all(n == 0 for key, n in clean_both.items() if key.lower().endswith('/high'))

clock_fields = ['association_id', 'announcement_times_all', 'sue_analyst_min2_coverage', 'sample_period']
spec = design.INPUTS['event_metadata']
clocks = read(spec['path'], spec['expected'], clock_fields)
assert len(clocks) == clocks.association_id.nunique() == 852
union = Counter(rows=len(clocks))
for row in clocks.to_dict('records'):
    if band(row['announcement_times_all']):
        union.update(nominal=1, nominal_min2=int(flag(row['sue_analyst_min2_coverage'])))
        union[row['sample_period']] += 1
assert union == {'rows':852, 'nominal':18, 'nominal_min2':5, 'PRE':12, 'POST':6}

# Independent enumeration of stock-quarter cells, using release quarters only.
event_rows = events.to_dict('records')
by_wave_regime = defaultdict(list)
for r in event_rows:
    r['quarter'] = r['announcement_date'][:4] + 'Q' + str((int(r['announcement_date'][5:7])-1)//3+1)
    by_wave_regime[(r['wave_id'], r['sample_period'])].append(r)
calendar = Counter()
for (wave, regime), rows in by_wave_regime.items():
    high = {r['quarter'] for r in rows if r['tier'].upper() == 'HIGH'}
    low = {r['quarter'] for r in rows if r['tier'].upper() == 'LOW'}
    observed = {(r['permno'], r['quarter']) for r in rows}
    stocks = set(acq.loc[acq.wave_id.eq(wave), 'permno'])
    calendar['excluded_quarters'] += len(high ^ low)
    for quarters, prefix in [(high | low, 'all'), (high & low, 'common')]:
        calendar[prefix+'_cells'] += len(stocks) * len(quarters)
        calendar[prefix+'_missing'] += sum((s, q) not in observed for s in stocks for q in quarters)
assert calendar == {'excluded_quarters':4,'all_cells':910,'all_missing':59,'common_cells':860,'common_missing':13}

# BFS on event indices, with shared stock/date adjacency; no copied union-find.
def components(include_wave=False):
    incidence = defaultdict(set)
    for i, r in enumerate(event_rows):
        relations = [('stock', r['permno']), ('date', r['announcement_date'])]
        if include_wave:
            relations.append(('wave', r['wave_id']))
        for relation in relations:
            incidence[relation].add(i)
    neighbors = defaultdict(set)
    for nodes in incidence.values():
        first = min(nodes)
        for other in nodes:
            neighbors[first].add(other)
            neighbors[other].add(first)
    unseen = set(range(len(event_rows)))
    sizes = []
    while unseen:
        queue, found = [unseen.pop()], set()
        while queue:
            node = queue.pop()
            if node in found:
                continue
            found.add(node)
            queue.extend(neighbors[node] - found)
        unseen -= found
        sizes.append(len(found))
    return sorted(sizes, reverse=True)

base, proxy = components(), components(True)
assert base == [828,12,12] and proxy == [852]
code_hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.rglob('*.py'))}
result = {'status':'INDEPENDENT_METADATA_COUNTS_REPRODUCED', 'source_universe':universe, 'attrition':counts, 'capped_nominal_stages':stages, 'clean_nominal_min2_both_sides_by_wave_tier':clean_both, 'union_nominal':union, 'calendar':calendar, 'base_component_sizes':base, 'wave_proxy_component_sizes':proxy, 'input_projections':manifest, 'code_hashes':code_hashes, 'requested_model_effort_acceptance_telemetry':'NOT_OBSERVED', 'network_or_scc':False, 'financial_or_response_values_parsed':False}
(ROOT/'review/INDEPENDENT_VERIFICATION_RECEIPT.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['input_projections','code_hashes']}, indent=2))
