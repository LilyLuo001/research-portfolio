#!/usr/bin/env bash
set -euo pipefail

: "${YAX_ACS_DATA_ROOT:?set YAX_ACS_DATA_ROOT under /projectnb/econdept}"

case "$YAX_ACS_DATA_ROOT" in
  /projectnb/econdept/*) ;;
  *) echo "YAX_ACS_DATA_ROOT must be under /projectnb/econdept" >&2; exit 2 ;;
esac

mkdir -p "$YAX_ACS_DATA_ROOT"
for year in 2017 2018 2019 2021 2022 2023 2024; do
  target="$YAX_ACS_DATA_ROOT/acs1_pums_${year}_csv_pus.zip"
  url="https://www2.census.gov/programs-surveys/acs/data/pums/${year}/1-Year/csv_pus.zip"
  if [[ ! -s "$target" ]]; then
    # SCC's system curl predates --retry-all-errors. Standard --retry still
    # covers transient HTTP failures on the Census download endpoint.
    curl --fail --location --retry 8 \
      --connect-timeout 30 --output "$target.partial" "$url"
    mv "$target.partial" "$target"
  fi
  unzip -tq "$target"
done

(
  cd "$YAX_ACS_DATA_ROOT"
  shasum -a 256 acs1_pums_*_csv_pus.zip > ACS_INPUT_SHA256.txt
)
