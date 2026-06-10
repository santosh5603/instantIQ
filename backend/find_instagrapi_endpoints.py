import instagrapi
import os
import inspect

# Get path of instagrapi
instagrapi_path = os.path.dirname(inspect.getfile(instagrapi))
print(f"instagrapi path: {instagrapi_path}")

# Find all direct-related files in instagrapi
direct_files = []
for root, dirs, files in os.walk(instagrapi_path):
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                if "direct" in content or "thread" in content or "postback" in content:
                    direct_files.append((path, file))

print(f"Found {len(direct_files)} direct-related files in instagrapi:")
for path, file in direct_files:
    # Search for specific keywords like message_action, postback, button, etc.
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        
    for kw in ["postback", "message_action", "fb_token", "button", "generic_xma", "xma"]:
        if kw in content:
            print(f"  - File {file} contains keyword '{kw}'")
            # print surrounding lines
            lines = content.splitlines()
            for idx, line in enumerate(lines):
                if kw in line:
                    start = max(0, idx - 2)
                    end = min(len(lines), idx + 3)
                    print(f"    Lines {start+1}-{end}:")
                    for i in range(start, end):
                        print(f"      {i+1}: {lines[i]}")
                    print()
