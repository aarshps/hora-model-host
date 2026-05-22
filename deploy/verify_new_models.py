import httpx
import json
import sys

# Force console to output clean UTF-8
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

API_KEY = "hora_live_8e94a7cb2c114f0c9780a1d3fbc9581f"
BASE_URL = "http://185.194.218.92:8000/v1/chat/completions"

def test_model_streaming(model_name):
    print(f"\n==================================================")
    print(f"🎬 Testing Streaming Completion: {model_name}")
    print(f"==================================================")
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "You are a highly concise assistant. Answer in under 15 words."},
            {"role": "user", "content": "Explain what gravity is."}
        ],
        "stream": True
    }
    
    try:
        with httpx.stream("POST", BASE_URL, json=payload, headers=headers, timeout=600.0) as r:
            if r.status_code != 200:
                print(f"❌ Error Response ({r.status_code}): {r.read().decode('utf-8')}")
                return False
                
            print("🟢 Streaming response chunks:")
            for line in r.iter_lines():
                if line:
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            print("\n[STREAM COMPLETE]")
                            break
                        try:
                            data_json = json.loads(data_str)
                            delta = data_json.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            print(content, end="", flush=True)
                        except json.JSONDecodeError:
                            pass
            return True
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        return False

def main():
    print("🚀 Starting Automated Parallel Model Verification...")
    qwen_success = test_model_streaming("qwen3.6:35b")
    gemma_success = test_model_streaming("gemma4:31b")
    
    print("\n==================================================")
    print("📊 Final Verification Results:")
    print(f"  - Qwen 3.6 35B-A3B: {'✅ PASSED' if qwen_success else '❌ FAILED'}")
    print(f"  - Gemma 4 31B:      {'✅ PASSED' if gemma_success else '❌ FAILED'}")
    print("==================================================")
    
    if qwen_success and gemma_success:
        print("🎉 All tests passed successfully!")
        sys.exit(0)
    else:
        print("⚠️ Some tests failed. Please check VPS/Ollama status.")
        sys.exit(1)

if __name__ == "__main__":
    main()
