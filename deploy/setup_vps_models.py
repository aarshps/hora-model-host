import paramiko
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure console supports UTF-8 characters for clean status logging
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def main():
    # 1. Load local environment variables for credentials
    base_dir = Path(__file__).resolve().parent.parent
    load_dotenv(base_dir / ".env")
    
    host = "185.194.218.92"
    username = "root"
    password = os.getenv("BW_PASSWORD")
    
    if not password:
        print("ERROR: BW_PASSWORD not set in local .env file.", file=sys.stderr)
        sys.exit(1)
        
    print(f"🚀 Establishing SSH connection to Contabo VPS ({host})...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(host, username=username, password=password, timeout=20)
        print("✅ SSH Connection established successfully!")
    except Exception as e:
        print(f"❌ Failed to connect to VPS: {e}", file=sys.stderr)
        sys.exit(1)
        
    try:
        # 2. Configure Systemd Ollama Overrides for Parallel loaded models
        print("\n⚙️ Configuring Systemd Ollama Parallel Service Overrides...")
        
        setup_override_cmd = """
        mkdir -p /etc/systemd/system/ollama.service.d
        cat << 'EOF' > /etc/systemd/system/ollama.service.d/override.conf
[Service]
Environment="OLLAMA_MAX_LOADED_MODELS=3"
Environment="OLLAMA_NUM_PARALLEL=2"
Environment="OLLAMA_KEEP_ALIVE=-1"
EOF
        systemctl daemon-reload
        systemctl restart ollama
        """
        
        stdin, stdout, stderr = ssh.exec_command(setup_override_cmd)
        
        # Read exit code
        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
            print(f"❌ Failed to setup systemd override. Exit code: {exit_status}", file=sys.stderr)
            print(stderr.read().decode('utf-8'), file=sys.stderr)
            sys.exit(1)
        else:
            print("✅ Systemd overrides written and Ollama service restarted successfully!")
            
        # 3. Pull Qwen 3.6 35B-A3B
        print("\n📥 Pulling Qwen 3.6 35B-A3B model (~20 GB). This will take several minutes...")
        pull_qwen_cmd = "ollama pull qwen3.6:35b"
        stdin, stdout, stderr = ssh.exec_command(pull_qwen_cmd)
        
        while True:
            line = stdout.readline()
            if not line:
                break
            print(f"[Ollama-Qwen] {line.strip()}")
            
        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
            print(f"❌ Failed to pull qwen3.6:35b. Exit code: {exit_status}", file=sys.stderr)
            print(stderr.read().decode('utf-8'), file=sys.stderr)
            sys.exit(1)
        else:
            print("✅ Qwen 3.6 35B-A3B pulled successfully!")
            
        # 4. Pull Gemma 4 31B
        print("\n📥 Pulling Gemma 4 31B model (~20 GB). This will take several minutes...")
        pull_gemma_cmd = "ollama pull gemma4:31b"
        stdin, stdout, stderr = ssh.exec_command(pull_gemma_cmd)
        
        while True:
            line = stdout.readline()
            if not line:
                break
            print(f"[Ollama-Gemma] {line.strip()}")
            
        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
            print(f"❌ Failed to pull gemma4:31b. Exit code: {exit_status}", file=sys.stderr)
            print(stderr.read().decode('utf-8'), file=sys.stderr)
            sys.exit(1)
        else:
            print("✅ Gemma 4 31B pulled successfully!")
            
        print("\n🎉 All remote model configurations complete!")
        
    finally:
        ssh.close()
        print("🔌 SSH Connection closed.")

if __name__ == "__main__":
    main()
