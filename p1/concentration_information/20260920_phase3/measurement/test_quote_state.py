"""Synthetic fixtures required by MEASUREMENT_CONTRACT.md."""

from quote_state import Update, sample_endpoints, simple_midpoint_response


def one(updates, target=(20, "PRE")):
    return sample_endpoints(updates, [target])[0]


def main() -> None:
    fixtures = {}

    # No movement and sparse updates remain valid carried states.
    x = one([Update(10, "PRE", 100, 102, 5, 6)])
    assert x.status == "VALID_CARRIED" and x.midpoint == 101
    fixtures["no_movement"] = "PASS"
    fixtures["sparse_update"] = "PASS"

    # An invalid one-sided update invalidates the prior state rather than
    # silently carrying it through.
    x = one([
        Update(10, "PRE", 100, 102, 5, 6),
        Update(15, "PRE", 100, None, 5, None),
    ])
    assert x.status == "INVALID_UNDEFINED_OR_ZERO_SIDE" and x.midpoint is None
    fixtures["one_sided_withdrawal"] = "PASS"

    x = one([Update(20, "PRE", 101, 101, 3, 4)])
    assert x.status == "VALID_LOCKED_OBSERVED" and x.locked and x.midpoint == 101
    fixtures["locked"] = "PASS"

    x = one([Update(20, "PRE", 102, 101, 3, 4)])
    assert x.status == "INVALID_CROSSED" and x.midpoint is None
    fixtures["crossed"] = "PASS"

    # A PRE state cannot initialize RTH.
    x = one([Update(10, "PRE", 100, 102, 5, 6)], target=(20, "RTH"))
    assert x.status == "UNKNOWN_NO_PRIOR_STATE"
    fixtures["session_reset"] = "PASS"

    # Venue streams are sampled separately; no synthetic cross-venue state is
    # created from one venue's bid and another venue's ask.
    venue_a = one([Update(10, "PRE", 100, None, 5, None)])
    venue_b = one([Update(10, "PRE", None, 102, None, 5)])
    assert venue_a.midpoint is None and venue_b.midpoint is None
    fixtures["asynchronous_venues"] = "PASS"

    base, post = sample_endpoints(
        [Update(10, "PRE", 100, 102, 5, 6), Update(20, "PRE", 102, 104, 5, 6)],
        [(10, "PRE"), (20, "PRE")],
    )
    assert abs(simple_midpoint_response(base, post) - (103 / 101 - 1)) < 1e-15
    assert simple_midpoint_response(base, one([], target=(20, "RTH"))) is None
    fixtures["response_and_common_session"] = "PASS"

    print({"fixtures": fixtures, "passed": len(fixtures)})


if __name__ == "__main__":
    main()
