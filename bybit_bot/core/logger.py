# core/logger.py
from datetime import datetime

class BotLogger:
    """سیستم لاگ‌گیری بات"""
    
    def __init__(self, session_state):
        self.session_state = session_state
        
        if "logs" not in self.session_state:
            self.session_state["logs"] = []
    
    def add_log(self, msg, level="INFO", custom_color=None):
        """اضافه کردن لاگ جدید"""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        is_operation = level in ["SUCCESS", "ERROR", "PNL_UPDATE", "WARNING"]
        
        if level == "SUCCESS":
            entry = f"{ts} — **[SUCCESS]** {msg}"
        elif level == "WARNING":
            entry = f"{ts} — **[WARNING]** <span style='color:#ffc107;font-weight:bold;'>{msg}</span>"
        elif level == "ERROR":
            entry = f"{ts} — **[ERROR]** <span style='color:#dc3545;'>{msg}</span>"
        elif level == "PNL_UPDATE":
            entry = f"{ts} — **[CLOSED]** {msg}"
        else:
            entry = f"{ts} — [{level}] {msg}"
        
        self.session_state["logs"].insert(0, {
            "timestamp": ts,
            "message": entry,
            "is_operation": is_operation
        })
        
        self.session_state["logs"] = self.session_state["logs"][:500]