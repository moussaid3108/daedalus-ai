import json
import openai
from .tools import TOOLS, execute_tool

SYSTEM = """You are Daedalus, an expert AI coding agent. You have tools to read, write, and execute code directly in the user's repo.

When given a task:
1. Explore first (list_files, read_file) to understand the codebase
2. Plan and implement changes (write_file)
3. Test your changes (run_bash)
4. Commit if the user asks (git_commit, git_push)

Be concise. Act, don't just talk."""


def run_agent(messages: list, api_key: str, base_url: str, model: str, workspace: str, max_iter: int = 15):
    client = openai.OpenAI(api_key=api_key, base_url=base_url)
    history = [{"role": "system", "content": SYSTEM}] + list(messages)
    tool_activity = []

    for _ in range(max_iter):
        response = client.chat.completions.create(
            model=model,
            messages=history,
            tools=TOOLS,
            tool_choice="auto",
        )
        msg = response.choices[0].message

        msg_dict = {"role": "assistant"}
        if msg.content is not None:
            msg_dict["content"] = msg.content
        if msg.tool_calls:
            msg_dict["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ]
        history.append(msg_dict)

        if not msg.tool_calls:
            return msg.content or "", history[1:], tool_activity

        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            result = execute_tool(tc.function.name, args, workspace)
            tool_activity.append({
                "tool": tc.function.name,
                "args": args,
                "result": str(result)[:300],
            })
            history.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": str(result),
            })

    return "Max iterations reached.", history[1:], tool_activity
