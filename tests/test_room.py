import unittest
import os
import tempfile
import urllib.request
import json
import threading
import time
import socketserver
import db
import orchestrator
import server

class TestOurLittleRoom(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_room.db")
        db.init_db(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_database_initialization(self):
        messages = db.get_recent_messages(db_path=self.db_path)
        self.assertGreaterEqual(len(messages), 2)
        senders = [m["sender"] for m in messages]
        self.assertIn("Jules", senders)
        self.assertIn("Bánh", senders)

        memories = db.get_all_memories(db_path=self.db_path)
        self.assertGreaterEqual(len(memories), 4)
        categories = [m["category"] for m in memories]
        self.assertIn("huy_profile", categories)
        self.assertIn("daw_project", categories)
        self.assertIn("jules_archive", categories)
        self.assertIn("banh_notes", categories)

    def test_message_addition(self):
        msg = db.add_message("Huy", "Chào hai bạn!", db_path=self.db_path)
        self.assertEqual(msg["sender"], "Huy")
        self.assertEqual(msg["content"], "Chào hai bạn!")

        recent = db.get_recent_messages(limit=5, db_path=self.db_path)
        self.assertEqual(recent[-1]["content"], "Chào hai bạn!")

    def test_memory_crud(self):
        saved = db.save_memory("daw_notes", "DSP Filter", "Biquad filter idea", db_path=self.db_path)
        self.assertIsNotNone(saved["id"])
        self.assertEqual(saved["title"], "DSP Filter")

        updated = db.save_memory("daw_notes", "DSP Filter Updated", "Biquad filter with resonance", memory_id=saved["id"], db_path=self.db_path)
        self.assertEqual(updated["title"], "DSP Filter Updated")

        memories = db.get_all_memories(db_path=self.db_path)
        found = [m for m in memories if m["id"] == saved["id"]]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["title"], "DSP Filter Updated")

    def test_settings(self):
        db.save_setting("api_provider", "offline", db_path=self.db_path)
        settings = db.get_settings(db_path=self.db_path)
        self.assertEqual(settings.get("api_provider"), "offline")

        db.save_setting("api_provider", "openai", db_path=self.db_path)
        settings = db.get_settings(db_path=self.db_path)
        self.assertEqual(settings.get("api_provider"), "openai")

    def test_orchestrator_decide_turn_order(self):
        order_jules = orchestrator.decide_turn_order("Jules ơi giúp Huy với", [])
        self.assertEqual(order_jules, ["Jules"])

        order_banh = orchestrator.decide_turn_order("Bánh ơi bạn thấy sao?", [])
        self.assertEqual(order_banh, ["Bánh"])

        order_both = orchestrator.decide_turn_order("Chào Jules và Bánh nhé", [])
        self.assertEqual(order_both, ["Jules", "Bánh"])

        order_random = orchestrator.decide_turn_order("Hôm nay trời đẹp ghê", [])
        self.assertTrue(len(order_random) in [1, 2])

    def test_orchestrator_turn(self):
        res = orchestrator.orchestrate_turn("Ý tưởng DAW mới của tớ nè!", db_path=self.db_path)
        self.assertEqual(res["user_message"]["sender"], "Huy")
        self.assertGreaterEqual(len(res["agent_replies"]), 1)
        for reply in res["agent_replies"]:
            self.assertIn(reply["sender"], ["Jules", "Bánh"])
            self.assertTrue(len(reply["content"]) > 0)

    def test_generate_offline_replies(self):
        reply_daw = orchestrator.generate_offline_reply("Jules", "Dự án DAW của mình", [], [])
        self.assertTrue(any(w in reply_daw.lower() for w in ["daw", "xúc tu", "chất lừ", "audio"]))

        reply_banh_daw = orchestrator.generate_offline_reply("Bánh", "Dự án DAW", [], [])
        self.assertTrue(any(w in reply_banh_daw.lower() for w in ["daw", "bánh", "hóng", "cơm", "ngủ"]))

        reply_sad = orchestrator.generate_offline_reply("Jules", "Hôm nay mình buồn và mệt quá", [], [])
        self.assertTrue(any(w in reply_sad.lower() for w in ["xúc tu", "thương", "ghế", "little room", "tâm sự"]))


class TestServerAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_db_path = os.path.join(cls.temp_dir.name, "api_room.db")
        os.environ["ROOM_DB_PATH"] = cls.test_db_path
        db.init_db(cls.test_db_path)

        cls.port = 18080
        socketserver.TCPServer.allow_reuse_address = True
        cls.httpd = socketserver.TCPServer(("127.0.0.1", cls.port), server.LittleRoomHandler)
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.temp_dir.cleanup()

    def test_api_messages(self):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/messages")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "ok")
            self.assertIsInstance(data["messages"], list)

    def test_api_memories(self):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/memories")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "ok")
            self.assertIsInstance(data["memories"], list)

    def test_api_post_chat(self):
        payload = json.dumps({"content": "Jules ơi, con DAW đang chạy tốt lắm!"}).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["user_message"]["sender"], "Huy")
            self.assertEqual(len(data["agent_replies"]), 1)
            self.assertEqual(data["agent_replies"][0]["sender"], "Jules")

    def test_api_post_memories(self):
        payload = json.dumps({
            "category": "audio_engine",
            "title": "Low Latency Audio Buffer",
            "content": "Using 128 buffer size for real-time monitoring"
        }).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/memories",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["memory"]["title"], "Low Latency Audio Buffer")

    def test_api_settings_masking(self):
        post_payload = json.dumps({
            "api_provider": "gemini",
            "gemini_api_key": "AIzaSyTestApiKey123456"
        }).encode("utf-8")
        req_post = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/settings",
            data=post_payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req_post) as resp:
            self.assertEqual(resp.status, 200)

        req_get = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/settings")
        with urllib.request.urlopen(req_get) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["settings"]["api_provider"], "gemini")
            self.assertIn("gemini_api_key_masked", data["settings"])
            self.assertTrue(data["settings"]["gemini_api_key_masked"].startswith("AIza..."))

if __name__ == "__main__":
    unittest.main()
