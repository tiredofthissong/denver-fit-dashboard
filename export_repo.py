import os

OUTPUT_FILE = "repo_snapshot.txt"

EXCLUDED_DIRS = {".git", "__pycache__", ".venv", "node_modules"}
EXCLUDED_FILES = {OUTPUT_FILE}

def should_skip(path):
    for part in path.split(os.sep):
        if part in EXCLUDED_DIRS:
            return True
    return False

def export_repo():
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

            for file in files:
                if file in EXCLUDED_FILES:
                    continue

                filepath = os.path.join(root, file)

                if should_skip(filepath):
                    continue

                out.write("\n\n# ==============================\n")
                out.write(f"# FILE: {filepath}\n")
                out.write("# ==============================\n\n")

                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        out.write(f.read())
                except Exception as e:
                    out.write(f"[Could not read file: {e}]")

if __name__ == "__main__":
    export_repo()
    print("Repo snapshot created successfully.")
