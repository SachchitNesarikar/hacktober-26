"""Keep the extension's copy of the handoff renderer in sync, then zip it for 'Load unpacked' / store upload."""
import os, shutil
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
shutil.copy(os.path.join(root, "web", "handoff.js"), os.path.join(root, "extension", "handoff.js"))
shutil.make_archive(os.path.join(root, "baton-extension"), "zip", os.path.join(root, "extension"))
print("extension synced and zipped: baton-extension.zip")
