"""Copy the UI and demo data into docs/ for GitHub Pages (demo-only static hosting)."""
import os, shutil
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = os.path.join(root, "docs")
shutil.rmtree(out, ignore_errors=True)
shutil.copytree(os.path.join(root, "web"), out)
shutil.copytree(os.path.join(root, "demo"), os.path.join(out, "demo"))
open(os.path.join(out, ".nojekyll"), "w").close()
print("static demo written to", out)
