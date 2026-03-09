import datetime

def log(message: str, category: str = "INFO"):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Simplification for consistent formatting: [YYYY-mm-dd HH:MM:SS] [CATEGORY] Message
    # If the message already has brackets (like in some existing Meta-MAS prints), we can handle it.
    print(f"[{timestamp}] [{category}] {message}")
