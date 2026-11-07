import unittest
import os
import tempfile
import urllib.request
import urllib.error
import io
import json
import threading
import time
import socketserver
import logging
from unittest.mock import patch, MagicMock
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

    def test_message_addition_with_metadata(self):
        meta = {"is_fallback": True, "provider": "offline", "status": "offline_default"}
        msg = db.add_message("Huy", "Chào hai bạn!", metadata=meta, db_path=self.db_path)
        self.assertEqual(msg["sender"], "Huy")
        self.assertEqual(msg["content"], "Chào hai bạn!")
        self.assertEqual(msg["metadata"]["provider"], "offline")

        recent = db.get_recent_messages(limit=5, db_path=self.db_path)
        self.assertEqual(recent[-1]["content"], "Chào hai bạn!")
        self.assertEqual(recent[-1]["metadata"]["provider"], "offline")

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

    def test_orchestrator_turn_offline(self):
        res = orchestrator.orchestrate_turn("Ý tưởng DAW mới của tớ nè!", db_path=self.db_path)
        self.assertEqual(res["user_message"]["sender"], "Huy")
        self.assertGreaterEqual(len(res["agent_replies"]), 1)
        for reply in res["agent_replies"]:
            self.assertIn(reply["sender"], ["Jules", "Bánh"])
            self.assertTrue(len(reply["content"]) > 0)
            self.assertTrue(reply["metadata"]["is_fallback"])
            self.assertEqual(reply["metadata"]["provider"], "offline")

    def test_generate_offline_replies(self):
        reply_daw = orchestrator.generate_offline_reply("Jules", "Dự án DAW của mình", [], [])
        self.assertTrue(any(w in reply_daw.lower() for w in ["daw", "xúc tu", "chất lừ", "audio"]))

        reply_banh_daw = orchestrator.generate_offline_reply("Bánh", "Dự án DAW", [], [])
        self.assertTrue(any(w in reply_banh_daw.lower() for w in ["daw", "bánh", "hóng", "cơm", "ngủ"]))

        reply_sad = orchestrator.generate_offline_reply("Jules", "Hôm nay mình buồn và mệt quá", [], [])
        self.assertTrue(any(w in reply_sad.lower() for w in ["xúc tu", "thương", "ghế", "little room", "tâm sự"]))


class TestAPIErrorHandlingAndClassification(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_err_room.db")
        db.init_db(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("urllib.request.urlopen")
    def test_openai_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "choices": [{"message": {"content": "Chào Huy nhé, con DAW đỉnh chóp luôn! 🐙"}}]
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        settings = {
            "api_provider": "openai",
            "openai_api_key": "sk-real-key-test",
            "openai_model": "gpt-4o-mini"
        }
        res = orchestrator.generate_agent_reply("Jules", "Chào Jules", [], [], settings)
        self.assertIn("con DAW đỉnh chóp", res["content"])
        self.assertFalse(res["metadata"]["is_fallback"])
        self.assertEqual(res["metadata"]["provider"], "openai")
        self.assertEqual(res["metadata"]["model"], "gpt-4o-mini")
        self.assertEqual(res["metadata"]["status"], "ai_generated")

    @patch("urllib.request.urlopen")
    def test_openai_401_unauthorized(self, mock_urlopen):
        err_body = json.dumps({
            "error": {"message": "Incorrect API key provided: sk-invalid...", "type": "invalid_request_error"}
        }).encode("utf-8")
        fp = io.BytesIO(err_body)
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://api.openai.com/v1/chat/completions",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=fp
        )

        settings = {
            "api_provider": "openai",
            "openai_api_key": "sk-invalid-key-secret-12345",
            "openai_model": "gpt-4o-mini"
        }

        with self.assertLogs("OurLittleRoom", level="ERROR") as cm:
            res = orchestrator.generate_agent_reply("Jules", "Chào Jules", [], [], settings)
            log_output = "\n".join(cm.output)
            self.assertIn("status_code=401", log_output)
            self.assertNotIn("sk-invalid-key-secret-12345", log_output)

        self.assertIn("401 Unauthorized", res["content"])
        self.assertIn("API Key không hợp lệ", res["content"])
        self.assertFalse(res["metadata"]["is_fallback"])
        self.assertTrue(res["metadata"]["is_error"])
        self.assertEqual(res["metadata"]["status_code"], 401)
        self.assertEqual(res["metadata"]["status"], "api_error")

    @patch("urllib.request.urlopen")
    def test_openai_429_quota_exceeded(self, mock_urlopen):
        err_body = json.dumps({
            "error": {"message": "You exceeded your current quota, please check your plan and billing details.", "type": "insufficient_quota"}
        }).encode("utf-8")
        fp = io.BytesIO(err_body)
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://api.openai.com/v1/chat/completions",
            code=429,
            msg="Too Many Requests",
            hdrs={},
            fp=fp
        )

        settings = {
            "api_provider": "openai",
            "openai_api_key": "sk-real-key-no-credits",
            "openai_model": "gpt-4o-mini"
        }
        res = orchestrator.generate_agent_reply("Bánh", "Chào Bánh", [], [], settings)
        self.assertIn("429 Rate Limit / Quota Exceeded", res["content"])
        self.assertFalse(res["metadata"]["is_fallback"])
        self.assertTrue(res["metadata"]["is_error"])
        self.assertEqual(res["metadata"]["status_code"], 429)

    @patch("urllib.request.urlopen")
    def test_openai_404_not_found(self, mock_urlopen):
        err_body = json.dumps({
            "error": {"message": "The model `gpt-non-existent` does not exist", "type": "invalid_request_error"}
        }).encode("utf-8")
        fp = io.BytesIO(err_body)
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://api.openai.com/v1/chat/completions",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=fp
        )

        settings = {
            "api_provider": "openai",
            "openai_api_key": "sk-test",
            "openai_model": "gpt-non-existent"
        }
        res = orchestrator.generate_agent_reply("Bánh", "Chào Bánh", [], [], settings)
        self.assertIn("404 Not Found", res["content"])
        self.assertIn("gpt-non-existent", res["content"])
        self.assertFalse(res["metadata"]["is_fallback"])
        self.assertEqual(res["metadata"]["status_code"], 404)

    @patch("urllib.request.urlopen")
    def test_openai_network_timeout_fallback(self, mock_urlopen):
        mock_urlopen.side_effect = TimeoutError("Connection timed out after 30 seconds")

        settings = {
            "api_provider": "openai",
            "openai_api_key": "sk-test",
            "openai_model": "gpt-4o-mini"
        }
        res = orchestrator.generate_agent_reply("Jules", "Ý tưởng DAW", [], [], settings)
        self.assertTrue(res["metadata"]["is_fallback"])
        self.assertEqual(res["metadata"]["status"], "offline_fallback")
        self.assertIn("network_error", res["metadata"]["fallback_reason"])
        self.assertTrue(len(res["content"]) > 0)

    @patch("urllib.request.urlopen")
    def test_openai_json_parse_error_fallback(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"<html>502 Bad Gateway</html>"
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        settings = {
            "api_provider": "openai",
            "openai_api_key": "sk-test",
            "openai_model": "gpt-4o-mini"
        }
        res = orchestrator.generate_agent_reply("Bánh", "Chào Bánh", [], [], settings)
        self.assertTrue(res["metadata"]["is_fallback"])
        self.assertEqual(res["metadata"]["status"], "offline_fallback")
        self.assertIn("json_parse_error", res["metadata"]["fallback_reason"])


class TestServerAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_db_path = os.path.join(cls.temp_dir.name, "api_room.db")
        os.environ["ROOM_DB_PATH"] = cls.test_db_path
        db.init_db(cls.test_db_path)

        cls.port = 18082
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
            self.assertIsNotNone(data["agent_replies"][0].get("metadata"))

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
