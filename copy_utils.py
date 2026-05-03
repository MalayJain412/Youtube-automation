import os

# Root directory to start searching from
ROOT_DIR = r"E:\Youtube automation"

# File extensions to include
INCLUDE_EXTENSIONS = {'.py', '.js', '.css', '.html', '.txt', '.json'}

# Output file where combined code will be saved
OUTPUT_FILE = os.path.join(ROOT_DIR, "all_code_snippets.txt")

# Directories to exclude
EXCLUDE_DIRS = {'venv', '__pycache__', '.git', 'node_modules', 'new-dev','leads','KMS','Admin-Panel','graphify-out'}

def should_include(file_name):
    return os.path.splitext(file_name)[1].lower() in INCLUDE_EXTENSIONS

def copy_code_snippets():
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
        for dirpath, dirnames, filenames in os.walk(ROOT_DIR):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

            for filename in filenames:
                if should_include(filename):
                    file_path = os.path.join(dirpath, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            outfile.write(f"\n\n----- File: {file_path} -----\n")
                            outfile.write(f.read())
                    except Exception as e:
                        print(f"Could not read {file_path}: {e}")

    print(f"\n✅ Code snippets copied to: {OUTPUT_FILE}")

if __name__ == "__main__":
    copy_code_snippets()
