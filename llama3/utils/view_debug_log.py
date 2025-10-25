"""
Debug Log Viewer

Simple utility to view and filter debug logs from vLLM deployment.

Usage:
    # View last 50 lines
    python view_debug_log.py
    
    # View last 100 lines
    python view_debug_log.py --lines 100
    
    # Follow log in real-time (like tail -f)
    python view_debug_log.py --follow
    
    # Filter by session ID
    python view_debug_log.py --session user-12345678
    
    # Search for keyword
    python view_debug_log.py --search "error"
"""

import time
import sys
from pathlib import Path

import fire


def view(
    lines: int = 50,
    follow: bool = False,
    session: str = None,
    search: str = None,
    file: str = "debug_info.log"
):
    """
    View debug log with various filters.
    
    Args:
        lines: Number of lines to show (default: 50)
        follow: Follow log in real-time like 'tail -f' (default: False)
        session: Filter by session ID
        search: Search for keyword (case-insensitive)
        file: Log file path (default: debug_info.log)
    """
    log_path = Path(file)
    
    if not log_path.exists():
        print(f"❌ Log file not found: {file}")
        print("   Make sure the vLLM deployment is running and has processed some messages.")
        return
    
    print(f"📖 Viewing: {file}")
    print("=" * 80)
    
    if follow:
        # Real-time following
        print("Following log (Ctrl+C to stop)...\n")
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                # Go to end of file
                f.seek(0, 2)
                
                while True:
                    line = f.readline()
                    if line:
                        # Apply filters
                        if session and session not in line:
                            continue
                        if search and search.lower() not in line.lower():
                            continue
                        
                        print(line, end='')
                        sys.stdout.flush()
                    else:
                        time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n\n✋ Stopped following log")
    else:
        # Show last N lines
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
            
            # Apply filters
            filtered_lines = []
            for line in all_lines:
                if session and session not in line:
                    continue
                if search and search.lower() not in line.lower():
                    continue
                filtered_lines.append(line)
            
            # Show last N lines
            display_lines = filtered_lines[-lines:] if len(filtered_lines) > lines else filtered_lines
            
            for line in display_lines:
                print(line, end='')
            
            print("\n" + "=" * 80)
            print(f"Showing last {len(display_lines)} lines")
            if session:
                print(f"Filtered by session: {session}")
            if search:
                print(f"Filtered by search: {search}")
            
            if len(filtered_lines) > lines:
                print(f"\n💡 Tip: Use --lines {len(filtered_lines)} to see all {len(filtered_lines)} matching lines")
            
        except Exception as e:
            print(f"❌ Error reading log: {e}")


def clear_log(file: str = "debug_info.log"):
    """
    Clear the debug log file.
    
    Args:
        file: Log file path (default: debug_info.log)
    """
    log_path = Path(file)
    
    if not log_path.exists():
        print(f"ℹ️  Log file doesn't exist: {file}")
        return
    
    try:
        log_path.unlink()
        print(f"✅ Cleared log file: {file}")
    except Exception as e:
        print(f"❌ Error clearing log: {e}")


def stats(file: str = "debug_info.log"):
    """
    Show statistics about the debug log.
    
    Args:
        file: Log file path (default: debug_info.log)
    """
    log_path = Path(file)
    
    if not log_path.exists():
        print(f"❌ Log file not found: {file}")
        return
    
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Count different types of entries
        total_lines = len(lines)
        user_messages = sum(1 for line in lines if 'USER MESSAGE:' in line)
        llm_prompts = sum(1 for line in lines if 'FULL PROMPT TO LLM:' in line)
        llm_outputs = sum(1 for line in lines if 'LLM RAW OUTPUT:' in line)
        errors = sum(1 for line in lines if 'ERROR' in line)
        
        # Extract unique sessions
        sessions = set()
        for line in lines:
            if 'Session:' in line:
                try:
                    session_part = line.split('Session:')[1].split()[0].strip(',')
                    sessions.add(session_part)
                except:
                    pass
        
        # File size
        file_size = log_path.stat().st_size
        size_mb = file_size / (1024 * 1024)
        
        print("📊 Debug Log Statistics")
        print("=" * 80)
        print(f"File: {file}")
        print(f"Size: {size_mb:.2f} MB ({file_size:,} bytes)")
        print(f"Total Lines: {total_lines:,}")
        print("-" * 80)
        print(f"User Messages: {user_messages}")
        print(f"LLM Prompts: {llm_prompts}")
        print(f"LLM Outputs: {llm_outputs}")
        print(f"Errors: {errors}")
        print(f"Unique Sessions: {len(sessions)}")
        print("=" * 80)
        
        if sessions:
            print("\nActive Sessions:")
            for session in sorted(sessions)[:10]:  # Show first 10
                print(f"  • {session}")
            if len(sessions) > 10:
                print(f"  ... and {len(sessions) - 10} more")
        
    except Exception as e:
        print(f"❌ Error reading log: {e}")


if __name__ == "__main__":
    fire.Fire({
        'view': view,
        'clear': clear_log,
        'stats': stats
    })
