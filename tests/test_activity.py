"""Tests for scripts/activity.py: fake API + clock, no network.

Run: python3 -m unittest discover -s tests -v
"""
import io, json, pathlib, sys, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import activity as act  # noqa: E402

T0 = 1_800_000_000.0


def ev(i, t, kind="push", ref="refs/heads/main", before="a" * 40, after="b" * 40, who="mcint"):
    return {"id": i, "timestamp": act.iso(t), "activity_type": kind, "ref": ref,
            "before": before, "after": after, "actor": {"login": who}}


class Clock:
    def __init__(self, t=T0): self.t = t; self.sleeps = []
    def now(self): return self.t
    def sleep(self, s): self.sleeps.append(s); self.t += s


class FakeAPI:
    """events: list of (visible_from_time, event). API returns newest first."""
    def __init__(self, clock, events):
        self.clock, self.events, self.paths = clock, events, []
    def __call__(self, path):
        self.paths.append(path)
        vis = [e for t, e in self.events if t <= self.clock.now()]
        return sorted(vis, key=lambda e: e["timestamp"], reverse=True)


def run(args, api, clock):
    out = io.StringIO()
    code = act.main(["--repo", "o/r"] + args, api=api, now=clock.now, sleep=clock.sleep,
                    out=lambda s: print(s, file=out))
    return code, out.getvalue().splitlines()


class OneShot(unittest.TestCase):
    def setUp(self):
        self.c = Clock()
        self.api = FakeAPI(self.c, [(0, ev(i, T0 - 100 + i, after=str(i) * 40)) for i in range(1, 6)])

    def test_oldest_first_and_limit(self):
        code, lines = run(["--limit", "3"], self.api, self.c)
        self.assertEqual(code, 0); self.assertEqual(len(lines), 3)
        self.assertTrue(lines[0].endswith("mcint")); self.assertIn("4444444", lines[1])
        self.assertIn("3333333", lines[0]); self.assertIn("5555555", lines[2])
        self.assertIn("push", lines[0]); self.assertIn("main", lines[0])

    def test_ref_passed_through(self):
        run(["--ref", "gh-pages"], self.api, self.c)
        self.assertIn("ref=gh-pages", self.api.paths[0])

    def test_json_lines(self):
        code, lines = run(["--limit", "2", "--json"], self.api, self.c)
        objs = [json.loads(l) for l in lines]
        self.assertEqual([o["id"] for o in objs], [4, 5])


class Follow(unittest.TestCase):
    def test_prints_only_new_and_count_stops(self):
        c = Clock()
        api = FakeAPI(c, [(0, ev(1, T0 - 50)), (T0 + 25, ev(2, T0 + 25)), (T0 + 70, ev(3, T0 + 70))])
        code, lines = run(["--follow", "--limit", "0", "--count", "2"], api, c)
        self.assertEqual(code, 0)
        self.assertEqual(len(lines), 2)
        self.assertNotIn(act.iso(T0 - 50)[11:19], " ".join(lines))

    def test_backoff_doubles_to_cap_and_resets(self):
        c = Clock()
        api = FakeAPI(c, [(0, ev(1, T0 - 50)), (T0 + 200, ev(2, T0 + 200)), (T0 + 10_000, ev(3, T0 + 10_000))])
        run(["--follow", "--limit", "0", "--count", "1", "--interval", "10", "--max-interval", "40"], api, c)
        self.assertEqual(c.sleeps[:5], [10, 20, 40, 40, 40])
        c2 = Clock()
        api2 = FakeAPI(c2, [(0, ev(1, T0 - 50)), (T0 + 30, ev(2, T0 + 30)), (T0 + 35, ev(3, T0 + 35))])
        run(["--follow", "--limit", "0", "--count", "2", "--interval", "10", "--max-interval", "40"], api2, c2)
        self.assertEqual(c2.sleeps[:3], [10, 20, 10])   # reset to base after the event at +30

    def test_timeout_exits_2(self):
        c = Clock(); api = FakeAPI(c, [(0, ev(1, T0 - 50))])
        code, lines = run(["--follow", "--limit", "0", "--timeout", "100"], api, c)
        self.assertEqual(code, 2); self.assertLessEqual(c.t, T0 + 100)


if __name__ == "__main__":
    unittest.main()
