# core/connection_manager.py
import time
from functools import wraps
from datetime import datetime
import streamlit as st

class ConnectionManager:
    """مدیریت پایداری اتصال و Retry خودکار"""
    
    def __init__(self, max_retries=3, retry_delay=5, timeout=10):
        """
        Args:
            max_retries: حداکثر تعداد تلاش مجدد
            retry_delay: تأخیر بین تلاش‌ها (ثانیه)
            timeout: زمان timeout برای هر درخواست (ثانیه)
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.connection_status = True
        self.last_successful_request = datetime.now()
        self.failed_requests_count = 0
        self.total_retries = 0
        self.connection_history = []  # تاریخچه وضعیت اتصال
    
    def is_network_error(self, exception):
        """بررسی اینکه آیا خطا مربوط به شبکه است"""
        error_keywords = [
            'timeout', 'connection', 'network', 'unreachable',
            'refused', 'reset', 'broken pipe', 'no route'
        ]
        error_str = str(exception).lower()
        return any(keyword in error_str for keyword in error_keywords)
    
    def log_connection_event(self, event_type, details=""):
        """ثبت رویداد اتصال"""
        event = {
            'timestamp': datetime.now(),
            'type': event_type,
            'details': details
        }
        self.connection_history.append(event)
        
        # نگه‌داری فقط 100 رویداد آخر
        if len(self.connection_history) > 100:
            self.connection_history = self.connection_history[-100:]
    
    def with_retry(self, logger=None):
        """
        Decorator برای اضافه کردن قابلیت retry به توابع
        
        استفاده:
            @connection_manager.with_retry(logger)
            def my_function():
                ...
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(self.max_retries):
                    try:
                        # تلاش برای اجرای تابع
                        result = func(*args, **kwargs)
                        
                        # موفقیت
                        self.last_successful_request = datetime.now()
                        
                        # اگر قبلاً مشکل داشتیم و الان حل شد
                        if not self.connection_status:
                            self.connection_status = True
                            self.failed_requests_count = 0
                            
                            if logger:
                                logger.add_log(
                                    "✅ **Connection restored!** Network is stable again.",
                                    "SUCCESS"
                                )
                            
                            self.log_connection_event("RESTORED", "Connection re-established")
                        
                        return result
                    
                    except Exception as e:
                        last_exception = e
                        self.total_retries += 1
                        
                        # بررسی نوع خطا
                        is_network_issue = self.is_network_error(e)
                        
                        # اگر تلاش آخر نبود
                        if attempt < self.max_retries - 1:
                            retry_msg = f"⚠️ Attempt {attempt + 1}/{self.max_retries} failed"
                            
                            if is_network_issue:
                                retry_msg += f" (Network issue). Retrying in {self.retry_delay}s..."
                            else:
                                retry_msg += f": {str(e)[:100]}. Retrying..."
                            
                            if logger:
                                logger.add_log(retry_msg, "WARNING")
                            
                            self.log_connection_event("RETRY", f"Attempt {attempt + 1}: {str(e)[:50]}")
                            
                            # منتظر بمانیم قبل از تلاش مجدد
                            time.sleep(self.retry_delay)
                        else:
                            # همه تلاش‌ها ناموفق بود
                            self.connection_status = False
                            self.failed_requests_count += 1
                            
                            error_msg = f"❌ **All {self.max_retries} attempts failed!**\n"
                            error_msg += f"Last error: {str(last_exception)[:200]}"
                            
                            if logger:
                                logger.add_log(error_msg, "ERROR")
                            
                            self.log_connection_event("FAILED", f"All retries exhausted: {str(e)[:50]}")
                            
                            # پرتاب خطا برای مدیریت در سطح بالاتر
                            raise last_exception
                
            return wrapper
        return decorator
    
    def get_status_summary(self):
        """خلاصه وضعیت اتصال"""
        now = datetime.now()
        time_since_last_success = (now - self.last_successful_request).total_seconds()
        
        return {
            'is_connected': self.connection_status,
            'last_success': self.last_successful_request,
            'seconds_since_success': time_since_last_success,
            'failed_requests': self.failed_requests_count,
            'total_retries': self.total_retries,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay
        }
    
    def reset_statistics(self):
        """ریست آمار"""
        self.failed_requests_count = 0
        self.total_retries = 0
        self.connection_history = []