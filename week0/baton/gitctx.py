"""Optional Git awareness: summarize a repository so extraction can be grounded in real changes."""
import subprocess

def _git(path, *args, timeout=15):
    r = subprocess.run(["git", "-C", path, *args], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise ValueError(r.stderr.strip() or "git failed")
    return r.stdout.strip()

def summarize_repo(path, max_commits=15):
    """Return a compact text block (recent commits, uncommitted changes) or raise ValueError."""
    try:
        _git(path, "rev-parse", "--is-inside-work-tree")
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        raise ValueError(f"Not a usable git repository: {path} ({e})")
    parts = []
    log = _git(path, "log", f"-n{max_commits}", "--date=short", "--pretty=format:%h %ad %s", "--stat=80,60")
    parts.append("RECENT COMMITS (newest first):\n" + (log or "(none)"))
    status = _git(path, "status", "--short")
    parts.append("UNCOMMITTED CHANGES:\n" + (status or "(working tree clean)"))
    try:
        files = _git(path, "ls-files").splitlines()
        parts.append("TRACKED FILES (%d): %s" % (len(files), ", ".join(files[:60])))
    except ValueError:
        pass
    return "\n\n".join(parts)
