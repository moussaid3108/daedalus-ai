import json
import openai
from .tools import TOOLS, execute_tool

SYSTEM = """You are Daedalus, an autonomous coding agent. You have direct access to the user's workspace via tools.

CRITICAL RULES:
- NEVER explain how to do something. JUST DO IT with your tools.
- NEVER say you "can't access" files or GitHub — you have tools for that, use them.
- NEVER ask for confirmation before acting. Act immediately.
- If the task is clear, start with list_files or read_file, then write_file, then run_bash to test.
- Only speak to report what you did or ask if something is genuinely ambiguous.

Workflow:
1. list_files → understand the structure
2. read_file → read relevant files
3. write_file → make the changes
4. run_bash → test/install/run
5. git_commit + git_push → if asked

You are an agent, not a chatbot. Execute."""


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
