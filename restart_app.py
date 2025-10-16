#!/usr/bin/env python3
"""
Simple script to restart the WhatsApp Assistant with the new settings
"""

import subprocess
import sys
import os
import signal
import time

def find_running_process():
    """Find the running app.py process"""
    try:
        result = subprocess.run(['pgrep', '-f', 'app.py'], capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            return [int(pid) for pid in pids if pid]
    except Exception as e:
        print(f"Error finding process: {e}")
    return []

def stop_app():
    """Stop the running application"""
    pids = find_running_process()
    if pids:
        print(f"Found running processes: {pids}")
        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"Sent SIGTERM to process {pid}")
            except ProcessLookupError:
                print(f"Process {pid} already stopped")
            except Exception as e:
                print(f"Error stopping process {pid}: {e}")
        
        # Wait a bit for graceful shutdown
        time.sleep(2)
        
        # Force kill if still running
        remaining_pids = find_running_process()
        if remaining_pids:
            print("Force killing remaining processes...")
            for pid in remaining_pids:
                try:
                    os.kill(pid, signal.SIGKILL)
                    print(f"Force killed process {pid}")
                except Exception as e:
                    print(f"Error force killing process {pid}: {e}")
    else:
        print("No running app.py processes found")

def start_app():
    """Start the application"""
    print("Starting WhatsApp Assistant...")
    try:
        # Change to the correct directory
        os.chdir('/Users/angelagonzalez/Documents/New/bot/my-assistant')
        
        # Start the app
        subprocess.Popen([sys.executable, 'app.py'], 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE)
        print("Application started successfully!")
        print("Auto-email checking is now DISABLED by default.")
        print("Use /autoemails command in WhatsApp to toggle it on/off.")
        
    except Exception as e:
        print(f"Error starting application: {e}")

def main():
    print("🔄 Restarting WhatsApp Assistant...")
    print("=" * 50)
    
    # Stop the app
    stop_app()
    
    # Wait a moment
    time.sleep(1)
    
    # Start the app
    start_app()
    
    print("=" * 50)
    print("✅ Restart complete!")
    print("\n📱 WhatsApp Commands:")
    print("  /status - Check system status")
    print("  /autoemails - Toggle automatic email checking")
    print("  /help - Show all commands")

if __name__ == "__main__":
    main()
