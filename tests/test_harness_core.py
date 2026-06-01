from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.contracts import openapi_spec
from harness.queue import JobQueue
from harness.state import SessionState, validate_session_id
from harness.validation import validate_task
from scripts.harness_server import HarnessRequestHandler
from scripts.study_cli import (
    advance_learning_state,
    agent_reply,
    api_key_send_allowed,
    build_learning_outline,
    clean_goal,
    conversation_user_level,
    ensure_learning_state,
    expert_intake_reply,
    infer_user_level,
    learning_outline_prompt,
    make_task,
    should_execute,
)
from scripts.harness_mcp import resolve_export_output, tool_definitions


class HarnessCoreTests(unittest.TestCase):
    def test_validate_task_requires_domain_and_goal(self) -> None:
        self.assertTrue(validate_task({}))
        self.assertEqual(validate_task({"domain": "AI", "goal": "Research"}), [])
        self.assertTrue(validate_task({"domain": "AI", "goal": "Research", "approved_tools": ["github_search"]}))

    def test_validate_task_rejects_oversized_fields(self) -> None:
        errors = validate_task({"domain": "AI", "goal": "x" * 4001})
        self.assertIn("goal must be at most 4000 characters.", errors)
        errors = validate_task({"domain": "x" * 121, "goal": "Research"})
        self.assertIn("domain must be at most 120 characters.", errors)

    def test_http_auth_requires_token_or_explicit_dev_override(self) -> None:
        old_token = os.environ.pop("HARNESS_API_TOKEN", None)
        old_allow = os.environ.pop("HARNESS_ALLOW_UNAUTHENTICATED", None)
        try:
            handler = object.__new__(HarnessRequestHandler)
            handler.headers = {}
            self.assertFalse(handler.is_authorized())
            os.environ["HARNESS_ALLOW_UNAUTHENTICATED"] = "1"
            self.assertTrue(handler.is_authorized())
            os.environ.pop("HARNESS_ALLOW_UNAUTHENTICATED", None)
            os.environ["HARNESS_API_TOKEN"] = "test-token"
            handler.headers = {"Authorization": "Bearer test-token"}
            self.assertTrue(handler.is_authorized())
        finally:
            if old_token is not None:
                os.environ["HARNESS_API_TOKEN"] = old_token
            else:
                os.environ.pop("HARNESS_API_TOKEN", None)
            if old_allow is not None:
                os.environ["HARNESS_ALLOW_UNAUTHENTICATED"] = old_allow
            else:
                os.environ.pop("HARNESS_ALLOW_UNAUTHENTICATED", None)

    def test_custom_api_base_requires_explicit_allow_flag(self) -> None:
        self.assertTrue(
            api_key_send_allowed(
                {
                    "provider": "deepseek",
                    "base_url": "https://api.deepseek.com",
                }
            )
        )
        self.assertFalse(
            api_key_send_allowed(
                {
                    "provider": "custom",
                    "base_url": "https://example.com/v1",
                }
            )
        )
        self.assertTrue(
            api_key_send_allowed(
                {
                    "provider": "custom",
                    "base_url": "https://example.com/v1",
                    "allow_untrusted_base_url": True,
                }
            )
        )

    def test_expert_intake_asks_user_level_before_tasks(self) -> None:
        reply = expert_intake_reply("我想成为量化投资专家")
        self.assertIsNotNone(reply)
        self.assertIn("了解程度", reply or "")
        self.assertIn("完全 0 基础", reply or "")
        self.assertIn("找工作", reply or "")

    def test_low_level_expert_intake_starts_with_foundation(self) -> None:
        reply = expert_intake_reply("我是零基础小白，想成为产品开发专家")
        self.assertIsNotNone(reply)
        self.assertIn("不会一上来安排复杂任务", reply or "")
        self.assertIn("先给一句话定义", reply or "")
        self.assertIn("3 个最小词", reply or "")
        self.assertIn("通俗比喻", reply or "")
        self.assertIn("我只确认一个信息", reply or "")
        self.assertNotIn("10 个核心术语卡", reply or "")

    def test_beginner_followup_stays_simple_for_job_search(self) -> None:
        history = [
            {"role": "user", "content": "我是完全0基础小白，想成为产品开发专家"},
            {"role": "assistant", "content": expert_intake_reply("我是完全0基础小白，想成为产品开发专家") or ""},
        ]
        reply = agent_reply("我想用于求职，每天只能学30分钟，我应该先做什么？", None, history)
        self.assertIn("先不选复杂岗位", reply)
        self.assertIn("问题、办法、试试", reply)
        self.assertIn("不确定", reply)
        self.assertNotIn("产品开发工程师", reply)

    def test_beginner_can_ask_for_childlike_explanation(self) -> None:
        history = [
            {"role": "user", "content": "我是完全0基础小白，想成为产品开发专家"},
            {"role": "assistant", "content": expert_intake_reply("我是完全0基础小白，想成为产品开发专家") or ""},
        ]
        reply = agent_reply("这些词我还是听不懂，你能像讲给小学生一样讲吗？", None, history)
        self.assertIn("小学生也能懂", reply)
        self.assertIn("发现问题，想办法，试试看", reply)
        self.assertIn("小麻烦", reply)

    def test_childlike_explanation_uses_domain_specific_coffee_context(self) -> None:
        history = [
            {"role": "user", "content": "我想学习咖啡萃取时间，但是我是完全0基础小白。"},
            {
                "role": "assistant",
                "content": "我们先讲咖啡萃取时间。萃取时间会影响咖啡的酸、甜、苦，和水温、粉水比、冲煮变量有关。",
            },
        ]
        reply = agent_reply("听不懂，像讲给小学生一样讲", None, history)
        self.assertIn("咖啡", reply)
        self.assertIn("咖啡粉", reply)
        self.assertIn("热水", reply)
        self.assertIn("萃取时间", reply)
        self.assertNotIn("作业本", reply)

    def test_learning_state_creates_internal_outline_for_new_subject(self) -> None:
        state = ensure_learning_state(None, "我想学习咖啡萃取时间", [])
        self.assertIsNotNone(state)
        self.assertEqual(state["subject"], "咖啡萃取时间")
        self.assertEqual(state["phases"][0]["name"], "定位目标与基础水平")
        self.assertIn("咖啡粉", state["terms"])
        self.assertEqual(len(state["phases"]), 6)

    def test_learning_outline_prompt_is_internal_and_stage_based(self) -> None:
        state = build_learning_outline("AI 优化简历与产品岗求职", "做过简单调研", "一周内投产品岗位")
        prompt = learning_outline_prompt(state)
        self.assertIn("内部学习引导大纲", prompt)
        self.assertIn("不要一次性完整展示", prompt)
        self.assertIn("当前阶段", prompt)
        self.assertIn("简历现状", prompt)

    def test_learning_state_resets_when_user_changes_subject(self) -> None:
        state = ensure_learning_state(None, "我想学习咖啡萃取时间", [])
        state = ensure_learning_state(state, "我想学习 AI 优化简历", [])
        self.assertEqual(state["subject"], "AI 优化简历与产品岗求职")
        self.assertIn("岗位", state["terms"])

    def test_learning_phase_does_not_jump_on_continue_only(self) -> None:
        state = build_learning_outline("咖啡萃取时间", "0基础", "学会判断萃取时间")
        same_state = advance_learning_state(state, "继续讲")
        next_state = advance_learning_state(state, "我明白了")
        self.assertEqual(same_state["current_phase"], 0)
        self.assertEqual(next_state["current_phase"], 1)

    def test_childlike_reply_can_use_learning_state_subject(self) -> None:
        state = build_learning_outline("咖啡萃取时间", "0基础", "听懂萃取时间")
        reply = agent_reply("听不懂，像讲给小学生一样讲", None, [], state)
        self.assertIn("咖啡", reply)
        self.assertIn("萃取时间", reply)
        self.assertNotIn("作业本", reply)

    def test_learning_context_starts_plan_after_purpose_and_time(self) -> None:
        first = "我想成为 Harness Engineering 专家"
        purpose = "我是为了创业"
        current = "我每天投入2小时，是指构建一个能自主完成任务的 AI 代理这种方向。"
        history = [
            {"role": "user", "content": first},
            {"role": "assistant", "content": "你学它是为了找工作、做项目、创业，还是做研究？"},
            {"role": "user", "content": purpose},
            {"role": "assistant", "content": "每天大概能投入多久？"},
        ]
        state = ensure_learning_state(None, first, [])
        state = ensure_learning_state(state, purpose, history[:2])
        reply = agent_reply(current, None, history, state)
        self.assertIn("信息够了", reply)
        self.assertIn("5-12 天", reply)
        self.assertIn("创业", reply)
        self.assertIn("2小时", reply)
        self.assertNotIn("更喜欢和人聊天", reply)
        self.assertNotIn("你现在对这个领域是 0 基础", reply)

    def test_level_answer_uses_known_context_instead_of_reasking(self) -> None:
        history = [
            {"role": "user", "content": "我想成为 Harness Engineering 专家"},
            {"role": "assistant", "content": "你目前是哪档：完全 0 基础 / 听过概念 / 做过简单调研 / 有项目或从业经验？"},
            {"role": "user", "content": "我是为了创业，每天投入2小时"},
            {"role": "assistant", "content": "收到"},
        ]
        state = ensure_learning_state(None, "我想成为 Harness Engineering 专家", [])
        state = ensure_learning_state(state, "我是为了创业，每天投入2小时", history[:2])
        reply = agent_reply("0基础", None, history, state)
        self.assertIn("信息够了", reply)
        self.assertIn("基础：0基础", reply)
        self.assertNotIn("你学它是为了找工作、做项目、创业", reply)
        self.assertNotIn("每天大概能投入多久", reply)

    def test_task_infers_user_level_from_goal(self) -> None:
        self.assertEqual(infer_user_level("我是小白，想成为 AI 产品专家"), "0基础")
        task = make_task("我是有项目经验的产品经理，想成为 AI 产品专家")
        self.assertEqual(task["user_level"], "有相关项目经验")

    def test_mid_level_followup_keeps_resume_context(self) -> None:
        history = [
            {"role": "user", "content": "你好，我想用 AI 优化简历，准备一周内投产品岗位。"},
            {
                "role": "assistant",
                "content": "你之前用AI工具改过简历吗？你是已经有过产品相关经验，还是0经验转行？",
            },
        ]
        reply = agent_reply("我不算小白，用过 ChatGPT，但不知道怎么系统学，每天大概 1 小时。", None, history)
        self.assertIn("AI 优化简历", reply)
        self.assertIn("简历草稿", reply)
        self.assertNotIn("这个领域就是把一个想法", reply)

    def test_execute_detection_ignores_regular_generate_questions(self) -> None:
        self.assertFalse(should_execute("我想了解怎么生成一份更好的简历"))
        self.assertFalse(should_execute("能不能讲讲生成式 AI 是什么"))
        self.assertFalse(should_execute("帮我看看应该怎么开始，不要生成文件"))
        self.assertTrue(should_execute("开始执行：我想用 AI 优化简历"))
        self.assertTrue(should_execute("我希望先在本地试试。开始执行：我想用 AI 优化简历"))
        self.assertTrue(should_execute("/run 我想用 AI 优化简历"))

    def test_clean_goal_preserves_non_command_generate_words(self) -> None:
        text = "我想了解怎么生成一份更好的简历"
        self.assertEqual(clean_goal(text), text)
        self.assertEqual(clean_goal("开始执行：我想了解生成式 AI 是什么"), "我想了解生成式 AI 是什么")
        self.assertEqual(clean_goal("我希望先在本地试试。开始执行：我想了解生成式 AI 是什么"), "我想了解生成式 AI 是什么")
        self.assertEqual(clean_goal("/run 不要生成文件，只做分析"), "不要生成文件，只做分析")

    def test_task_can_inherit_conversation_user_level(self) -> None:
        history = [{"role": "user", "content": "我不算小白，用过 ChatGPT，每天 1 小时。"}]
        level = conversation_user_level(history, "开始执行：我想用 AI 优化简历")
        self.assertEqual(level, "做过简单调研")
        task = make_task("我想用 AI 优化简历，准备一周内投产品岗位", user_level=level)
        self.assertEqual(task["user_level"], "做过简单调研")

    def test_approvals_are_internal_state_not_task_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state = SessionState(Path(tmpdir), "session-ok")
            state.init({"domain": "AI", "goal": "Research", "approved_tools": ["github_search"]})
            self.assertNotIn("approved_tools", state.task())
            approved = state.approve_tool("github_search")
            self.assertIn("github_search", approved["approved_tools"])
            self.assertNotIn("approved_tools", approved["task"])

    def test_session_id_blocks_path_traversal(self) -> None:
        with self.assertRaises(ValueError):
            validate_session_id("../bad")
        self.assertEqual(validate_session_id("session-ok_1"), "session-ok_1")

    def test_openapi_contract_exposes_paths(self) -> None:
        spec = openapi_spec()
        self.assertEqual(spec["openapi"], "3.1.0")
        self.assertIn("/health", spec["paths"])
        self.assertIn("/jobs", spec["paths"])

    def test_mcp_tool_contract_contains_queue_tools(self) -> None:
        names = {tool["name"] for tool in tool_definitions()}
        self.assertIn("rapid_expert_run", names)
        self.assertIn("rapid_expert_queue_submit", names)
        self.assertIn("rapid_expert_health", names)

    def test_study_hacker_command_version(self) -> None:
        proc = subprocess.run(
            [str(ROOT / "bin" / "study.cmd"), "hacker", "--version"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("study hacker", proc.stdout)

    def test_queue_submit_cancel_retry(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            queue = JobQueue(root)
            job = queue.submit({"domain": "AI", "goal": "Research"}, to_step="plan")
            self.assertEqual(job["status"], "queued")
            approved = queue.approve_tool(job["job_id"], "github_search")
            self.assertIn("github_search", approved["approved_tools"])
            self.assertNotIn("approved_tools", approved["task"])
            cancelled = queue.cancel(job["job_id"])
            self.assertEqual(cancelled["status"], "cancelled")
            retried = queue.retry(job["job_id"])
            self.assertEqual(retried["status"], "queued")

    def test_mcp_export_output_stays_inside_dist(self) -> None:
        self.assertEqual(resolve_export_output("dist/test.zip").parent, (ROOT / "dist").resolve())
        with self.assertRaises(ValueError):
            resolve_export_output("../outside.zip")

    def test_public_http_bind_requires_api_token(self) -> None:
        env = dict(os.environ)
        env.pop("HARNESS_API_TOKEN", None)
        env.pop("HARNESS_ALLOW_UNAUTHENTICATED", None)
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "harness_server.py"), "--host", "0.0.0.0", "--port", "0"],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("missing_api_token", proc.stderr)

    def test_mcp_content_length_framing(self) -> None:
        request = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode("utf-8")
        framed = b"Content-Length: " + str(len(request)).encode("ascii") + b"\r\n\r\n" + request
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "harness_mcp.py")],
            input=framed,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertTrue(proc.stdout.startswith(b"Content-Length:"))
        _, _, body = proc.stdout.partition(b"\r\n\r\n")
        payload = json.loads(body.decode("utf-8"))
        self.assertTrue(payload["result"]["tools"])


if __name__ == "__main__":
    unittest.main()
