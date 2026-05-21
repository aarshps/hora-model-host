import os
import sys
import json
import subprocess
import shutil
import io

# Force UTF-8 output encoding for Windows consoles to support emojis in output
if sys.platform.startswith("win"):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except Exception:
        pass

def find_bw_executable():
    # 1. Search system PATH
    bw_path = shutil.which("bw")
    if bw_path:
        return bw_path

    # 2. Check standard Windows NPM global path
    user_profile = os.environ.get("USERPROFILE", "C:\\Users\\Aarsh")
    npm_bw = os.path.join(user_profile, "AppData", "Roaming", "npm", "bw.cmd")
    if os.path.exists(npm_bw):
        return npm_bw

    return None

def run_bw_command(args, session_key=None, input_data=None):
    bw_path = find_bw_executable()
    if not bw_path:
        raise FileNotFoundError("Bitwarden CLI ('bw') was not found on your system. Please install it or make sure it is on your PATH.")

    env = os.environ.copy()
    # Add Node.js and NPM to PATH for subprocess execution
    env["PATH"] = r"C:\Program Files\nodejs;" + env.get("PATH", "")

    if session_key:
        env["BW_SESSION"] = session_key

    cmd = [bw_path] + args
    
    # Use shell=True on Windows for .cmd files
    is_windows = os.name == "nt"
    
    stdin = subprocess.PIPE if input_data else None
    process = subprocess.Popen(
        cmd,
        stdin=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
        shell=is_windows
    )
    
    stdout, stderr = process.communicate(input=input_data)
    
    if process.returncode != 0:
        raise RuntimeError(f"Bitwarden CLI error: {stderr.strip() or stdout.strip()}")
        
    return stdout.strip()

def get_session():
    # First check environment variable
    session_key = os.environ.get("BW_SESSION")
    if session_key:
        print("🔑 Using existing BW_SESSION environment variable.")
        return session_key

    # Otherwise, check status
    try:
        status_json = run_bw_command(["status"])
        status = json.loads(status_json)
        if status.get("status") == "unlocked":
            print("🔑 Vault is already unlocked.")
            return None # Command doesn't need BW_SESSION if already unlocked in global config
    except Exception:
        pass

    print("🔒 Bitwarden vault is locked.")
    master_password = input("🔑 Enter your Bitwarden Master Password: ").strip()
    if not master_password:
        print("❌ No password provided. Aborting sync.")
        sys.exit(1)

    print("\n🔓 Unlocking vault...")
    bw_path = find_bw_executable()
    if not bw_path:
        raise FileNotFoundError("Bitwarden CLI ('bw') was not found on your system.")

    env = os.environ.copy()
    env["PATH"] = r"C:\Program Files\nodejs;" + env.get("PATH", "")
    is_windows = os.name == "nt"

    process = subprocess.Popen(
        [bw_path, "unlock"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
        shell=is_windows
    )
    
    stdout, stderr = process.communicate(input=master_password + "\n")

    if process.returncode != 0:
        print(f"❌ Failed to unlock: {stderr.strip() or stdout.strip()}")
        sys.exit(1)

    # Parse session key from stdout
    import re
    match = re.search(r'BW_SESSION="([^"]+)"', stdout)
    if match:
        session_key = match.group(1)
        print("✅ Vault unlocked successfully!")
        return session_key
    else:
        # Fallback parsing in case output format differs
        for line in stdout.splitlines():
            line = line.strip()
            if not line.startswith("?") and "vault" not in line.lower() and "session" not in line.lower() and len(line) > 50:
                print("✅ Vault unlocked successfully!")
                return line
        print(f"❌ Could not parse session key from output: {stdout}")
        sys.exit(1)


def main():
    print("=" * 60)
    print("     Hora Model Host - Bitwarden Secrets Vault Sync")
    print("=" * 60)

    # 1. Verify files exist
    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_file = os.path.join(repo_dir, ".env")
    key_file = os.path.join(repo_dir, "test_key")

    if not os.path.exists(env_file):
        print(f"❌ Local .env file not found at: {env_file}")
        sys.exit(1)
    if not os.path.exists(key_file):
        print(f"❌ Local SSH key file 'test_key' not found at: {key_file}")
        sys.exit(1)

    # 2. Get Bitwarden session key
    try:
        session_key = get_session()
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)

    # 3. Fetch folders to find "Hora"
    print("\n🔍 Fetching Bitwarden folders...")
    try:
        folders_json = run_bw_command(["list", "folders"], session_key)
        folders = json.loads(folders_json)
    except Exception as e:
        print(f"❌ Failed to retrieve folders: {e}")
        sys.exit(1)

    hora_folder = None
    for folder in folders:
        if folder.get("name", "").lower() == "hora":
            hora_folder = folder
            break

    if not hora_folder:
        print("⚠️ Folder 'Hora' not found in Bitwarden.")
        create_opt = input("Do you want to create a new folder named 'Hora'? (y/n): ").strip().lower()
        if create_opt == 'y':
            print("📁 Creating folder 'Hora'...")
            try:
                folder_template = json.loads(run_bw_command(["get", "template", "folder"], session_key))
                folder_template["name"] = "Hora"
                new_folder_json = run_bw_command(["create", "folder"], session_key, input_data=json.dumps(folder_template))
                hora_folder = json.loads(new_folder_json)
                print(f"✅ Folder 'Hora' created successfully with ID: {hora_folder['id']}")
            except Exception as e:
                print(f"❌ Failed to create folder: {e}")
                sys.exit(1)
        else:
            print("❌ Sync cancelled because the 'Hora' folder does not exist.")
            sys.exit(1)
    else:
        print(f"✅ Found folder 'Hora' (ID: {hora_folder['id']})")

    folder_id = hora_folder["id"]

    # Read local secrets
    with open(env_file, "r", encoding="utf-8") as f:
        env_content = f.read()

    with open(key_file, "r", encoding="utf-8") as f:
        key_content = f.read()

    # Define the items to sync
    sync_items = [
        {
            "name": "Hora Model Host - Environment Secrets (.env)",
            "content": env_content,
            "filename": ".env"
        },
        {
            "name": "Hora Model Host - SSH Private Key (test_key)",
            "content": key_content,
            "filename": "test_key"
        }
    ]

    # Fetch existing items in the folder to see if we should update or create
    print("\n🔍 Checking for existing secrets in the 'Hora' folder...")
    try:
        items_json = run_bw_command(["list", "items", "--folderid", folder_id], session_key)
        existing_items = json.loads(items_json)
    except Exception as e:
        print(f"❌ Failed to list items: {e}")
        sys.exit(1)

    for sync_item in sync_items:
        existing_item = None
        for item in existing_items:
            if item.get("name") == sync_item["name"]:
                existing_item = item
                break

        if existing_item:
            print(f"🔄 Updating existing item: '{sync_item['name']}'...")
            try:
                # Update notes field
                existing_item["notes"] = sync_item["content"]
                # Save updated item
                run_bw_command(["edit", "item", existing_item["id"]], session_key, input_data=json.dumps(existing_item))
                print(f"✅ Successfully updated '{sync_item['name']}'!")
            except Exception as e:
                print(f"❌ Failed to update item '{sync_item['name']}': {e}")
        else:
            print(f"➕ Creating new secure note: '{sync_item['name']}'...")
            try:
                item_template = json.loads(run_bw_command(["get", "template", "item"], session_key))
                item_template["name"] = sync_item["name"]
                item_template["folderId"] = folder_id
                item_template["type"] = 2 # Secure Note
                item_template["secureNote"] = {"type": 1}
                item_template["notes"] = sync_item["content"]
                
                run_bw_command(["create", "item"], session_key, input_data=json.dumps(item_template))
                print(f"✅ Successfully created '{sync_item['name']}'!")
            except Exception as e:
                print(f"❌ Failed to create item '{sync_item['name']}': {e}")

    print("\n🎉 Bitwarden secrets sync completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    main()
