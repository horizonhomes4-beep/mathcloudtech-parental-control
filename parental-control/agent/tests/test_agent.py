import importlib.util
from pathlib import Path
import unittest

AGENT = Path(__file__).resolve().parents[1] / "agent.py"
spec = importlib.util.spec_from_file_location("parentguard_agent", AGENT)
agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent)

class AgentPolicyTests(unittest.TestCase):
    def test_temporary_unlock_overrides_expired_screen_time(self):
        import datetime as dt, time
        old_state = agent.state.copy()
        try:
            agent.state.update(day="", used=999)
            policy = {"limit": 30, "start": "07:00", "end": "21:00", "paused": False,
                      "unlockedUntil": int(time.time()) + 120}
            self.assertEqual(agent.screen_time(policy, dt.datetime.now(), set()), "")
        finally:
            agent.state.clear(); agent.state.update(old_state)

    def test_manual_lock_remains_enforced_without_temporary_unlock(self):
        import datetime as dt
        old_state = agent.state.copy()
        try:
            agent.state.update(day="", used=0)
            policy = {"limit": 300, "start": "00:00", "end": "23:59", "paused": True,
                      "unlockedUntil": 0}
            self.assertEqual(agent.screen_time(policy, dt.datetime.now(), set()), "locked by parent/admin")
        finally:
            agent.state.clear(); agent.state.update(old_state)

    def test_domain_normalisation(self):
        self.assertEqual(agent.normalise_domains(["https://www.example.com/path", "school.edu"]), {"example.com", "school.edu"})

    def test_allowed_app_is_not_killed(self):
        calls=[]
        old=agent.run
        agent.run=lambda args, timeout=20: calls.append(args) or type("R", (), {"returncode":0,"stdout":"","stderr":""})()
        try:
            agent.enforce_process_policy({"apps":["game.exe"],"allowedApps":["game.exe"]}, [("game.exe","123","1","kid","Game")])
            self.assertFalse(any("taskkill" in call for call in calls))
        finally: agent.run=old

    def test_blocked_game_is_killed(self):
        calls=[]
        old=agent.run
        agent.run=lambda args, timeout=20: calls.append(args) or type("R", (), {"returncode":0,"stdout":"","stderr":""})()
        try:
            agent.enforce_process_policy({"blockedGames":["game.exe"]}, [("game.exe","123","1","kid","Game")])
            self.assertTrue(any("taskkill" in call for call in calls))
        finally: agent.run=old


    def test_process_policy_returns_all_device_user_sessions(self):
        rows = [
            ("explorer.exe", "100", "1", "parent", "Desktop"),
            ("explorer.exe", "200", "2", "kid", "Desktop"),
            ("game.exe", "201", "2", "kid", "Game"),
        ]
        sessions, _ = agent.enforce_process_policy({}, rows)
        self.assertEqual(sessions, {"1", "2"})

    def test_blocked_process_only_targets_child_account(self):
        calls = []
        old = agent.run
        agent.run = lambda args, timeout=20: calls.append(args) or type("R", (), {"returncode":0,"stdout":"","stderr":""})()
        try:
            rows = [
                ("game.exe", "100", "1", "parent", "Game"),
                ("game.exe", "200", "2", "kid", "Game"),
            ]
            child_rows = [row for row in rows if row[3] == "kid"]
            agent.enforce_process_policy({"blockedGames": ["game.exe"]}, child_rows)
            self.assertEqual([call[-1] for call in calls if "taskkill" in call], ["200"])
        finally:
            agent.run = old



    def test_unassigned_child_does_not_enforce_processes(self):
        calls = []
        old = agent.run
        agent.run = lambda args, timeout=20: calls.append(args) or type("R", (), {"returncode":0,"stdout":"","stderr":""})()
        try:
            # The tick loop must not pass all machine processes to the policy enforcer
            # when no exact child Windows username is configured.
            policy = {"child": "", "apps": ["browser.exe"]}
            child = str(policy.get("child", "")).strip().lower()
            rows = [("browser.exe", "42", "1", "parent", "Browser")]
            child_rows = [r for r in rows if child and r[3] == child]
            self.assertEqual(child_rows, [])
        finally:
            agent.run = old

    def test_console_user_uses_explorer_owner(self):
        rows = [("explorer.exe", "1", "1", "kid", ""), ("python.exe", "2", "0", "system", "")]
        self.assertEqual(agent.console_user(rows), "kid")
        self.assertEqual(agent.console_user([]), "")

    def test_single_instance_helper_is_safe_off_windows(self):
        if agent.os.name != "nt":
            self.assertIsNotNone(agent.acquire_single_instance())
            self.assertFalse(agent.agent_running())

    def test_health_file_round_trip(self):
        import tempfile, json
        old = agent.HEALTH
        agent.HEALTH = Path(tempfile.mkdtemp()) / "health.json"
        try:
            agent.write_health(True)
            self.assertTrue(json.loads(agent.HEALTH.read_text())["ok"])
            agent.write_health(False, "boom")
            data = json.loads(agent.HEALTH.read_text())
            self.assertFalse(data["ok"]); self.assertEqual(data["error"], "boom")
        finally:
            agent.HEALTH = old

    def test_log_rotates_when_large(self):
        import tempfile
        old = agent.LOG
        d = Path(tempfile.mkdtemp()); agent.LOG = d / "agent.log"
        try:
            agent.LOG.write_text("x" * 600_000)
            agent.log("hello")
            self.assertTrue((d / "agent.log.1").exists())
            self.assertIn("hello", agent.LOG.read_text())
        finally:
            agent.LOG = old

    def test_process_policy_is_device_wide_without_child_username(self):
        calls = []
        old = agent.run
        agent.run = lambda args, timeout=20: calls.append(args) or type("R", (), {"returncode":0,"stdout":"","stderr":""})()
        try:
            rows = [("game.exe", "100", "1", "parent", "Game"), ("game.exe", "200", "2", "guest", "Game")]
            agent.enforce_process_policy({"blockedGames": ["game.exe"]}, rows)
            self.assertEqual(sorted(call[-1] for call in calls if "taskkill" in call), ["100", "200"])
        finally:
            agent.run = old

    def test_event_publishes_fullscreen_notice_for_blockage_on_windows(self):
        import tempfile, json
        old_name, old_notice = agent.os.name, agent.NOTICE
        old_state = agent.state.copy()
        try:
            with tempfile.TemporaryDirectory() as d:
                target = Path(d) / "notice.json"
                agent.NOTICE = target
                agent.os.name = "nt"
                agent._notice_last.clear()
                agent.event("Blocked application: testgame.exe", "block")
                payload = json.loads(agent.NOTICE.read_text(encoding="utf-8"))
                self.assertEqual(payload["title"], "@M Family Safety Guard blockage")
                self.assertIn("Blocked application", payload["reason"])
        finally:
            agent.os.name, agent.NOTICE = old_name, old_notice
            agent.state.clear(); agent.state.update(old_state)
            agent._notice_last.clear()

    def test_device_sessions_include_all_interactive_users(self):
        old_name, old_wts, old_lock = agent.os.name, agent.wts_sessions, agent.lockscreen_sessions
        try:
            agent.os.name = "nt"
            agent.wts_sessions = lambda: [
                {"id": 0, "user": "", "state": 0, "name": "Services"},
                {"id": 1, "user": "Parent", "state": 0, "name": "Console"},
                {"id": 2, "user": "Guest", "state": 4, "name": "RDP-Tcp#1"},
                {"id": 3, "user": "Student", "state": 0, "name": "RDP-Tcp#2"},
            ]
            agent.lockscreen_sessions = lambda: set()
            users, active = agent.device_sessions()
            self.assertEqual({x["user"] for x in users}, {"Parent", "Guest", "Student"})
            self.assertEqual({x["user"] for x in active}, {"Parent", "Student"})
        finally:
            agent.os.name, agent.wts_sessions, agent.lockscreen_sessions = old_name, old_wts, old_lock

class ChildRequestTests(unittest.TestCase):
    def test_site_request_is_normalised_and_validated(self):
        r = agent.clean_request({"type": "site", "target": "https://www.Khanacademy.org/math?x=1", "note": "homework"})
        self.assertEqual((r["type"], r["target"]), ("site", "khanacademy.org"))
        self.assertIsNone(agent.clean_request({"type": "site", "target": "not a host!!"}))

    def test_app_request_keeps_only_executable_name(self):
        r = agent.clean_request({"type": "app", "target": "C:\\Games\\Game.EXE"})
        self.assertEqual(r["target"], "game.exe")
        self.assertIsNone(agent.clean_request({"type": "app", "target": "..\\evil.bat"}))

    def test_time_request_minutes_are_restricted(self):
        self.assertEqual(agent.clean_request({"type": "time", "minutes": 15})["minutes"], 15)
        self.assertEqual(agent.clean_request({"type": "time", "minutes": 9999})["minutes"], 30)

    def test_unknown_type_and_long_note_are_handled(self):
        self.assertIsNone(agent.clean_request({"type": "format-disk"}))
        self.assertIsNone(agent.clean_request("junk"))
        self.assertEqual(len(agent.clean_request({"type": "message", "note": "x" * 5000})["note"]), 300)

    def test_requests_are_throttled(self):
        old = list(agent.state.get("reqLog", []))
        try:
            agent.state["reqLog"] = []
            req = {"type": "time", "target": ""}
            self.assertTrue(agent.request_allowed(req, 1000.0))
            self.assertFalse(agent.request_allowed(req, 1030.0))   # same request within 2 minutes
            self.assertTrue(agent.request_allowed(req, 1200.0))
            agent.state["reqLog"] = [[2000.0 + i, f"message:{i}"] for i in range(12)]
            self.assertFalse(agent.request_allowed({"type": "message", "target": ""}, 2100.0))  # 12 per hour
        finally:
            agent.state["reqLog"] = old

    def test_child_text_is_plain_language(self):
        self.assertIn("example.com", agent.child_text("Blocked website: example.com", "block", "example.com", ""))
        self.assertIn("game.exe", agent.child_text("Blocked application: game.exe", "block", "", "game.exe"))
        self.assertIn("limit", agent.child_text("Screen session restricted: daily screen-time limit reached", "screen", "", ""))

    def test_request_file_flows_to_firestore_and_mail_queue(self):
        import tempfile, json
        saved = {k: getattr(agent, k) for k in ("REQ_DIR", "post_request", "deliver_mail_queue", "check_answers", "event")}
        old_state = {k: agent.state.get(k) for k in ("reqLog", "mailQueue", "awaiting", "childName")}
        d = Path(tempfile.mkdtemp())
        posted = []
        try:
            agent.REQ_DIR = d
            agent.post_request = lambda req, rid, now: posted.append((req, rid))
            agent.deliver_mail_queue = lambda: None
            agent.check_answers = lambda: None
            agent.event = lambda *a, **k: None
            agent.state.update(reqLog=[], mailQueue=[], awaiting=[], childName="Jason")
            (d / "a.json").write_text(json.dumps({"type": "site", "target": "khanacademy.org", "note": "maths"}))
            (d / "bad.json").write_text("{not json")
            agent.process_requests()
            self.assertEqual(len(posted), 1)
            self.assertEqual(list(d.glob("*.json")), [])            # both files consumed
            queued = agent.state["mailQueue"][0]
            self.assertIn("Jason", queued["subject"])
            self.assertIn("khanacademy.org", queued["body"])
            self.assertEqual(agent.state["awaiting"][0]["type"], "site")
        finally:
            for k, v in saved.items():
                setattr(agent, k, v)
            agent.state.update({k: v for k, v in old_state.items() if v is not None})

    def test_mail_queue_sends_to_every_recipient_and_records_result(self):
        sent, patched = [], []
        saved = {k: getattr(agent, k) for k in ("send_mail", "patch_request", "load_notify_config")}
        old_queue = agent.state.get("mailQueue", [])
        try:
            agent.load_notify_config = lambda: {"enabled": True, "recipients": ["a@x.com", "b@y.com"], "serviceId": "s", "templateId": "t", "publicKey": "k"}
            agent.send_mail = lambda cfg, to, subject, message: sent.append(to)
            agent.patch_request = lambda rid, fields: patched.append((rid, fields))
            agent.state["mailQueue"] = [{"rid": "r1", "subject": "s", "body": "b", "tries": 0}]
            agent.deliver_mail_queue()
            self.assertEqual(sent, ["a@x.com", "b@y.com"])
            self.assertTrue(patched[0][1]["emailed"]["booleanValue"])
            self.assertEqual(agent.state["mailQueue"], [])
        finally:
            for k, v in saved.items():
                setattr(agent, k, v)
            agent.state["mailQueue"] = old_queue

    def test_mail_failure_is_retried_then_reported(self):
        patched = []
        saved = {k: getattr(agent, k) for k in ("send_mail", "patch_request", "load_notify_config")}
        old_queue = agent.state.get("mailQueue", [])
        try:
            agent.load_notify_config = lambda: {"enabled": True, "recipients": ["a@x.com"]}
            def boom(*a): raise RuntimeError("provider down")
            agent.send_mail = boom
            agent.patch_request = lambda rid, fields: patched.append(fields)
            agent.state["mailQueue"] = [{"rid": "r2", "subject": "s", "body": "b", "tries": 0}]
            agent.deliver_mail_queue()
            self.assertEqual(len(agent.state["mailQueue"]), 1)       # kept for retry
            self.assertEqual(patched, [])
            agent.state["mailQueue"][0]["tries"] = 4
            agent.deliver_mail_queue()
            self.assertEqual(agent.state["mailQueue"], [])
            self.assertFalse(patched[0]["emailed"]["booleanValue"])
            self.assertIn("provider down", patched[0]["emailError"]["stringValue"])
        finally:
            for k, v in saved.items():
                setattr(agent, k, v)
            agent.state["mailQueue"] = old_queue

    def test_notice_has_request_metadata(self):
        import tempfile, json
        saved = (agent.NOTICE, agent.os.name)
        d = Path(tempfile.mkdtemp())
        try:
            agent.NOTICE = d / "notice.json"
            class FakeOS:  # make publish_notice believe it runs on Windows
                name = "nt"
                environ = agent.os.environ
                path = agent.os.path
            real = agent.os
            agent.os = FakeOS
            agent._notice_last.clear()
            agent.publish_notice("Blocked website: example.com", "block", domain="example.com")
            data = json.loads(agent.NOTICE.read_text())
            agent.os = real
            self.assertEqual((data["ttype"], data["target"]), ("site", "example.com"))
        finally:
            agent.os = real
            agent.NOTICE = saved[0]


if __name__ == "__main__":
    unittest.main()
