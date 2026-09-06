# Source inventory self-review

Review role: execution-agent self-review, not independent scientific review  
Reviewed: 2026-09-06

I checked `source_inventory.json` against the extracted V3 package, the clean
local worktree, Git object identity, SCC filesystem metadata, read-only SHA-256
checks, IPUMS DDI variable lists, and current scheduler state.

The inventory passes the three G01 acceptance checks:

1. supplied and repository files are identified by verified filenames and
   hashes where a file exists;
2. an absent input is distinguished from an input that is present but
   restricted, inaccessible, or not yet verified; and
3. historical `/mnt/data/...` PDF locators are not treated as current code or
   data evidence.

The inventory does not claim that `EARNWEEK2` is unavailable from IPUMS merely
because it is absent from the authorized extracts. It records that ACS
microdata, exact BCC membership, proprietary ADP outcomes, and a selected
adoption-analysis input are not currently supplied. No private absolute path
or credential is needed in the public inventory.
