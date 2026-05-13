import os
import subprocess

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file in the workspace (max 8000 chars).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path from workspace root"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path from workspace root"},
                    "content": {"type": "string", "description": "Full file content to write"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_bash",
            "description": "Execute a bash command in the workspace directory. Timeout: 30s.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The bash command to run"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in the workspace up to 3 levels deep.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to list (default: '.')"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_commit",
            "description": "Stage all changes and create a git commit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Commit message"}
                },
                "required": ["message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_push",
            "description": "Push commits to the remote repository.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

BLOCKED_COMMANDS = ("rm -rf /", "mkfs", "dd if=", ":(){ :|:& };:", "> /dev/sd")


def _safe_path(workspace: str, path: str) -> str:
    full = os.path.realpath(os.path.join(workspace, path))
    if not full.startswith(os.path.realpath(workspace)):
        raise ValueError("Path outside workspace")
    return full


def execute_tool(name: str, args: dict, workspace: str) -> str:
    try:
        if name == "read_file":
            path = _safe_path(workspace, args["path"])
            if not os.path.exists(path):
                return f"File not found: {args['path']}"
            with open(path, "r", errors="replace") as f:
                return f.read(8000)

        elif name == "write_file":
            path = _safe_path(workspace, args["path"])
            dir_name = os.path.dirname(path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            with open(path, "w") as f:
                f.write(args["content"])
            return f"Written: {args['path']}"

        elif name == "run_bash":
            cmd = args["command"]
            if any(b in cmd for b in BLOCKED_COMMANDS):
                return "Command blocked for safety."
            result = subprocess.run(
                cmd, shell=True, cwd=workspace,
                capture_output=True, text=True, timeout=30
            )
            output = (result.stdout + result.stderr).strip()
            return output[:4000] if output else "(no output)"

        elif name == "list_files":
            path = _safe_path(workspace, args.get("path", "."))
            result = subprocess.run(
                ["find", ".", "-not", "-path", "./.git/*", "-maxdepth", "3"],
                cwd=path, capture_output=True, text=True, timeout=10
            )
            return result.stdout[:3000]

        elif name == "git_commit":
            subprocess.run(["git", "add", "-A"], cwd=workspace, capture_output=True)
            result = subprocess.run(
                ["git", "commit", "-m", args["message"]],
                cwd=workspace, capture_output=True, text=True
            )
            return (result.stdout + result.stderr).strip()

        elif name == "git_push":
            result = subprocess.run(
                ["git", "push"], cwd=workspace,
                capture_output=True, text=True, timeout=30
            )
            return (result.stdout + result.stderr).strip()

        return f"Unknown tool: {name}"

    except subprocess.TimeoutExpired:
        return "Command timed out (30s limit)"
    except Exception as e:
        return f"Error: {str(e)}"
