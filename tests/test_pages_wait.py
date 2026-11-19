"""Tests for scripts/pages_wait.py: fake GitHub API + fake clock, no network.

Run: python3 -m unittest discover -s tests -v
"""
import io, json, os, pathlib, sys, tempfile, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import pages_wait as pw  # noqa: E402

T0 = 1_800_000_000.0                       # fixed "now" for every test
ISO = lambda t: pw.iso(t)                  # epoch -> GitHub-style ISO string
HEAD = "b" * 40
OLD = "a" * 40


class Clock:
    def __init__(self, t=T0): self.t = t; self.sleeps = []
    def now(self): return self.t
    def sleep(self, s): self.sleeps.append(s); self.t += max(0, s)


def build(commit, status, created, updated=None, dur=36000):
    return {"commit": commit, "status": status, "created_at": ISO(created),
            "updated_at": ISO(updated if updated is not None else created + dur / 1000),
            "duration": dur if status == "built" else None}


class FakeAPI:
    """`timeline` is a list of (from_time, latest_build); latest = last entry with from_time <= now."""
    def __init__(self, clock, timeline, history=None, branch_head=HEAD, site=None):
        self.clock, self.timeline, self.branch_head, self.site = clock, timeline, branch_head, site
        self.history = history or [build(OLD, "built", T0 - 3600 + 60 * i) for i in range(5)]
        self.calls = []
    def latest(self):
        cur = None
        for t, b in self.timeline:
            if t <= self.clock.now(): cur = b
        return cur
    def __call__(self, path):
        self.calls.append(path)
        if path.endswith("/pages"):
            return {"source": {"branch": "gh-pages"}, "html_url": "https://example.test/site/"}
        if path.endswith("/branches/gh-pages"):
            return {"commit": {"sha": self.branch_head}}
        if "/commits/" in path:
            return {"sha": HEAD}
        if path.endswith("/pages/builds/latest"):
            return self.latest()
        if "/pages/builds" in path:
            cur = self.latest()
            return ([cur] if cur and cur not in self.history else []) + self.history
        raise AssertionError("unexpected path " + path)


def run(args, api, clock, head_fn=None):
    out = io.StringIO()
    with tempfile.TemporaryDirectory() as d:
        os.environ["MUSE_CORVA_CACHE"] = d
        code = pw.main(["--repo", "o/r"] + args, api=api, now=clock.now, sleep=clock.sleep,
                       out=lambda s: print(s, file=out), head=head_fn)
        log = pathlib.Path(d, "pages-wait.jsonl")
        rows = [json.loads(l) for l in log.read_text().splitlines()] if log.exists() else []
    return code, out.getvalue(), rows


class Schedule(unittest.TestCase):
    def test_shape_sparse_then_dense_then_tail(self):
        t = pw.probe_times(start=0, expected=60, offsets=[-10, -5, -2, 0, 2, 5, 10, 20, 40],
                           sparse=20, tail=60, timeout=300)
        self.assertEqual(t[:12], [0, 20, 40, 50, 55, 58, 60, 62, 65, 70, 80, 100])
        self.assertEqual(t[12:], [160, 220, 280])

    def test_past_points_dropped(self):
        t = pw.probe_times(start=100, expected=103, offsets=[-10, -5, -2, 0, 2, 5],
                           sparse=20, tail=60, timeout=100)
        self.assertEqual(t, [100, 101, 103, 105, 108, 168])
        self.assertEqual(t, sorted(t))

    def test_estimate_uses_median_duration_and_logged_queue(self):
        hist = [build(OLD, "built", 0, dur=d) for d in (34000, 38000, 40000)]
        self.assertAlmostEqual(pw.estimate(anchor=1000, builds=hist, log_rows=[]), 1038)
        self.assertAlmostEqual(pw.estimate(anchor=1000, builds=hist, log_rows=[{"queue_s": 4}, {"queue_s": 2}]), 1041)
        self.assertAlmostEqual(pw.estimate(anchor=1000, builds=[], log_rows=[]), 1040)


class Wait(unittest.TestCase):
    def test_already_built_stops_immediately(self):
        c = Clock(); api = FakeAPI(c, [(0, build(HEAD, "built", T0 - 100))])
        code, out, rows = run([], api, c)
        self.assertEqual(code, 0); self.assertEqual(c.sleeps, []); self.assertIn("already", out)

    def test_stops_when_target_built(self):
        c = Clock()
        api = FakeAPI(c, [(0, build(OLD, "built", T0 - 3000)),
                          (T0 + 2, build(HEAD, "building", T0 + 2)),
                          (T0 + 39, build(HEAD, "built", T0 + 2, T0 + 39))])
        code, out, rows = run([], api, c)
        self.assertEqual(code, 0)
        self.assertGreaterEqual(c.t, T0 + 39); self.assertLess(c.t, T0 + 60)
        self.assertEqual(len(rows), 1); self.assertEqual(rows[0]["commit"], HEAD)
        self.assertEqual(rows[0]["outcome"], "built")
        self.assertIn("duration_s", rows[0]); self.assertIn("error_s", rows[0])

    def test_change_backup_stops_on_other_commit(self):
        c = Clock(); other = "c" * 40
        api = FakeAPI(c, [(0, build(OLD, "built", T0 - 3000)),
                          (T0 + 30, build(other, "built", T0 - 5, T0 + 30))])
        code, out, rows = run([], api, c)
        self.assertEqual(code, 0); self.assertIn("changed", out)

    def test_no_change_ignores_other_commit(self):
        c = Clock(); other = "c" * 40
        api = FakeAPI(c, [(0, build(OLD, "built", T0 - 3000)),
                          (T0 + 30, build(other, "built", T0 - 5, T0 + 30))])
        code, out, rows = run(["--no-change", "--timeout", "200"], api, c)
        self.assertEqual(code, 2)

    def test_errored_exits_1(self):
        c = Clock()
        api = FakeAPI(c, [(0, build(OLD, "built", T0 - 3000)),
                          (T0 + 20, build(HEAD, "errored", T0 + 2, T0 + 20))])
        code, out, rows = run([], api, c)
        self.assertEqual(code, 1); self.assertEqual(rows[0]["outcome"], "errored")

    def test_timeout_exits_2(self):
        c = Clock(); api = FakeAPI(c, [(0, build(OLD, "built", T0 - 3000))])
        code, out, rows = run(["--timeout", "120"], api, c)
        self.assertEqual(code, 2); self.assertLessEqual(c.t, T0 + 121); self.assertIn("timeout", out)

    def test_dry_run_prints_schedule_without_polling(self):
        c = Clock(); api = FakeAPI(c, [(0, build(OLD, "built", T0 - 3000))])
        code, out, rows = run(["--dry-run"], api, c)
        self.assertEqual(code, 0); self.assertEqual(c.sleeps, []); self.assertIn("probes", out)
        self.assertFalse(any(p.endswith("/latest") for p in api.calls))

    def test_live_waits_for_last_modified(self):
        c = Clock(); built_at = T0 + 39
        api = FakeAPI(c, [(0, build(OLD, "built", T0 - 3000)),
                          (T0 + 39, build(HEAD, "built", T0 + 2, built_at))])
        def head(url):  # site serves the new build from +45s
            return {"last-modified": pw.http_date(built_at if c.t >= T0 + 45 else T0 - 3000), "age": "0"}
        code, out, rows = run(["--live"], api, c, head_fn=head)
        self.assertEqual(code, 0); self.assertGreaterEqual(c.t, T0 + 45); self.assertIn("live", out)
        self.assertIn("live_s", rows[0])


if __name__ == "__main__":
    unittest.main()
