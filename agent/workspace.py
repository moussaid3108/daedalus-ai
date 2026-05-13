import os
import uuid
import subprocess
import shutil

WORKSPACES_DIR = "/tmp/daedalus_workspaces"


def create_workspace(repo_url: str = None) -> tuple:
    os.makedirs(WORKSPACES_DIR, exist_ok=True)
    ws_id = uuid.uuid4().hex[:10]
    workspace = os.path.join(WORKSPACES_DIR, ws_id)

    if repo_url:
        if not repo_url.startswith(("http://", "https://")):
            raise ValueError("Repository URL must start with http:// or https://")
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, workspace],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            raise ValueError(f"Clone failed: {result.stderr[:300]}")
    else:
        os.makedirs(workspace)
        try:
            subprocess.run(["git", "init"], cwd=workspace, capture_output=True)
        except FileNotFoundError:
            pass  # git absent du conteneur, le workspace reste utilisable

    return ws_id, workspace


def get_workspace(ws_id: str) -> str:
    workspace = os.path.join(WORKSPACES_DIR, ws_id)
    if not os.path.isdir(workspace):
        raise ValueError("Workspace not found or expired")
    return workspace


def delete_workspace(ws_id: str):
    shutil.rmtree(os.path.join(WORKSPACES_DIR, ws_id), ignore_errors=True)
