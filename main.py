import subprocess
import time

def run_services():
    print("🚀 جاري تشغيل البوت ولوحة التحكم...")
    # تشغيل ملف البوت (المستخدمين)
    bot_proc = subprocess.Popen(['python', 'bot.py'])
    # تشغيل ملف الإدارة (المطور)
    admin_proc = subprocess.Popen(['python', 'admin.py'])

    try:
        bot_proc.wait()
        admin_proc.wait()
    except KeyboardInterrupt:
        bot_proc.terminate()
        admin_proc.terminate()

if __name__ == "__main__":
    run_services()
