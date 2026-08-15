#!/usr/bin/env python3
"""Claims must be derived from observations. A failing lane must not establish."""
from __future__ import annotations

import unittest

from synrix_receipt import _claims


def _ok_ack() -> dict:
    return {
        "scenario": "ack_unflushed_loss_witness",
        "passed": True,
        "write_acked": True,
        "killed_by_sigkill": True,
        "state_recovered": False,
        "recovery_timeout": False,
    }


def _ok_durable() -> dict:
    return {
        "scenario": "durable_sigkill",
        "passed": True,
        "write_acked": True,
        "killed_by_sigkill": True,
        "state_recovered": True,
        "recovery_timeout": False,
    }


def _ok_tail() -> dict:
    return {
        "scenario": "durable_torn_tail",
        "passed": True,
        "state_recovered": True,
        "tear_injected": True,
        "recovery_timeout": False,
    }


def _ok_wal(kind: str) -> dict:
    return {
        "scenario": f"wal_{kind}",
        "passed": True,
        "state_recovered": False,
        "recovery_timeout": False,
    }


def _ok_order() -> dict:
    return {
        "passed": True,
        "set_identical": True,
        "matches_expected_set": True,
        "reference_duplicates": 0,
        "shuffled_duplicates": 0,
    }


class TestConditionalClaims(unittest.TestCase):
    def test_all_green_establishes_five(self) -> None:
        claims = _claims({
            "durability": [
                _ok_ack(), _ok_durable(), _ok_tail(),
                _ok_wal("delete"), _ok_wal("zero"),
            ],
            "order_invariance": _ok_order(),
        })
        self.assertEqual(len(claims["established"]), 5)
        self.assertEqual(claims["not_established"], [])
        self.assertTrue(any("DURABLE" in s for s in claims["established"]))

    def test_failed_durable_is_not_established(self) -> None:
        durable = _ok_durable()
        durable["passed"] = False
        durable["state_recovered"] = False
        claims = _claims({
            "durability": [
                _ok_ack(), durable, _ok_tail(),
                _ok_wal("delete"), _ok_wal("zero"),
            ],
            "order_invariance": _ok_order(),
        })
        self.assertFalse(any("survived SIGKILL" in s for s in claims["established"]))
        hit = [s for s in claims["not_established"] if s.startswith("DURABLE")]
        self.assertEqual(len(hit), 1)
        self.assertIn("NOT ESTABLISHED", hit[0])
        self.assertIn("recovered=False", hit[0])

    def test_timeout_is_not_established(self) -> None:
        durable = _ok_durable()
        durable["passed"] = False
        durable["recovery_timeout"] = True
        claims = _claims({"durability": [durable], "order_invariance": {}})
        self.assertEqual(claims["established"], [])
        self.assertTrue(any("timeout=True" in s for s in claims["not_established"]))

    def test_missing_lanes_are_not_established(self) -> None:
        claims = _claims({"durability": [], "order_invariance": {}})
        self.assertEqual(claims["established"], [])
        self.assertEqual(len(claims["not_established"]), 5)
        self.assertTrue(all("NOT ESTABLISHED" in s for s in claims["not_established"]))


if __name__ == "__main__":
    raise SystemExit(unittest.main())
