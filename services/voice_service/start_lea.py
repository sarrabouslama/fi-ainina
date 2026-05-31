"""
start_lea.py — starts Léa's hands-free voice interaction
Run this script to activate Léa without any button press.
"""
import threading
import uvicorn
from app.wake_word import start_wake_word_detector

def start_server():
    uvicorn.run("app.main:app", host="127.0.0.1", port=8002)

if __name__ == "__main__":
    print(" Starting Léa voice assistant...")
    print(" Starting API server on port 8002...")
    
    # Start server in background
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Wait for server to load
    import time
    time.sleep(15)
    
    print(" Léa is now active — no button needed!")
    print(" Say 'Bonjour Léa' to start talking\n")
    
    # Start wake word detector (blocks here, always listening)
    start_wake_word_detector()