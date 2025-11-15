# check_files.py
import os

base = r'C:\PYTON\استراتژی های ترید با پایتون\HH_ROBOT\app_modular\Claude\bybit_bot'

files_to_check = {
    'core/api_client.py': 'BybitAPIClient',
    'core/position_manager.py': 'PositionManager',
    'core/risk_manager.py': 'RiskManager',
    'core/logger.py': 'BotLogger',
    'core/utils.py': 'safe_float',
    'config/settings.py': 'ConfigManager',
    'strategies/base_strategy.py': 'BaseStrategy',
    'strategies/heikin_ashi_strategy.py': 'HeikinAshiSMAStrategy',
}

print("=" * 70)
print("🔍 بررسی فایل‌های پروژه")
print("=" * 70)

all_ok = True

for file_path, class_name in files_to_check.items():
    full_path = os.path.join(base, file_path)
    
    if os.path.exists(full_path):
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = len(content.splitlines())
            has_class = class_name in content
            
            if has_class and lines > 10:
                status = "✅"
            else:
                status = "❌"
                all_ok = False
            
            print(f"{status} {file_path}: {lines} خط | کلاس '{class_name}': {has_class}")
    else:
        print(f"❌ {file_path}: فایل وجود ندارد!")
        all_ok = False

print("=" * 70)

if all_ok:
    print("✅ همه فایل‌ها کامل هستند!")
    print("\nحالا __init__.py ها را خالی می‌کنیم...")
    
    # خالی کردن __init__.py ها
    init_files = [
        'config/__init__.py',
        'core/__init__.py',
        'strategies/__init__.py',
        'ui/__init__.py'
    ]
    
    for init_file in init_files:
        full_path = os.path.join(base, init_file)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write('# Empty init file\n')
        print(f"✅ {init_file} خالی شد")
    
    print("\n" + "=" * 70)
    print("🎉 آماده اجرا! حالا این دستور را اجرا کنید:")
    print("streamlit run main.py")
    print("=" * 70)
else:
    print("\n⚠️ برخی فایل‌ها ناقص هستند!")
    print("لطفاً فایل‌های مشکل‌دار را بررسی کنید.")