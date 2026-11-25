# ==================== Discord: บอทและสิทธิ์ ====================
# Token สำหรับล็อกอินบอท ห้ามแชร์หรือเผยแพร่
token = "00000000"
# ใส่ Server ID ในรูปแบบ list
guild_id = [00000000] # ไอดีเชิฟเวอร์
# Discord User ID ที่อนุญาตให้ใช้คำสั่งผู้ดูแล
OWNERS = [00000000] # ไอดีเจ้าของดิส
# Channel ID สำหรับรับ log รายการเติมเงิน
channeltopupnotify = 00000000 # ชาแนลแจ้งเตือนเติมเงิน

# ==================== MySQL: ฐานข้อมูลเกม ====================
# ตั้งค่าการเชื่อมต่อ MySQL
configsql = {
    # ชื่อผู้ใช้ MySQL
    'user': 'root',
    # รหัสผ่าน MySQL
    'password': '',
    # เครื่องหรือ IP ที่รัน MySQL
    'host': 'localhost',
    # ชื่อฐานข้อมูลเกม
    'database': 'test'
}

# ==================== PromptPay / โอนธนาคาร ====================
# ข้อมูลเชื่อมต่อ API สำหรับสร้าง QR และตรวจสอบยอดโอน
# ชื่อบัญชี API ของผู้ให้บริการ PromptPay
username = "" # ชื่อผู้ใช้บนเว็บ
# รหัสผ่าน API (เก็บไว้ในเครื่องเท่านั้น)
password = "" # รหัสผ่านบนเว็บ 
# รหัสการเชื่อมต่อที่ออกโดยผู้ให้บริการ
con_id       = ""        # CON_ID จากหน้า setting (หมวด API พร้อมเพย์)
type         = "01"      # "01"=PromptPay เบอร์โทร, "03"=E-Wallet(เลขอ้างอิง)
# เบอร์หรือ ID PromptPay ที่รับชำระ
promptpay_id = ""        # หมายเลขพร้อมเพย์ (ถ้าใช้ 01)
# เลขบัญชีที่ผูกกับ API หากผู้ให้บริการกำหนด
account_no   = ""        # เลขบัญชีธนาคาร (ถ้าจำเป็น)
# รหัสยืนยัน/รหัสบัญชีที่ API ต้องใช้
acccode      = ""        # รหัสจาก encode KBIZ (ตามคู่มือ tmweasyapi)

TMWEASY_ENDPOINT = "https://tmwallet.thaighost.net/apipp.php"
TMWEASY_TIMEOUT  = 20

# ==================== TrueMoney Wallet: ซองอั่งเปา ====================
# เลือก endpoint จริงหรือ endpoint ทดสอบตามบัญชีที่ใช้
APIWALLET_ENDPOINT = "https://www.tmweasy.com/apiwallet.php"   # หรือ "http://tmwallet.thaighost.net/apiwallet.php"
# APIWALLET_ENDPOINT = "https://www.tmweasy.com/apiwallet_test.php"  # ใช้สำหรับทดสอบเท่านั้น
APIWALLET_TIMEOUT  = 20
# เบอร์ TrueMoney Wallet สำหรับรับซอง
tmemail = ""            # เบอร์ TrueMoney Wallet ของร้าน (10 หลัก) ใช้รับซอง

# ==================== หน้าตาเมนูใน Discord ====================
# "01" = เมนูเลือกช่องทาง | "02" = แสดงปุ่ม Wallet และธนาคาร
# เลือกรูปแบบเมนู: 01 หรือ 02 ตามคำอธิบายด้านล่าง
TOPUP_UI_TYPE = "02"

# ตัวเลือกรูปแบบ QR และการตกแต่ง Embed
TOPUP_QRCODE_TYPE = "01"

# พอร์ตเว็บสรุป Top-up (เปิดเฉพาะเครื่องนี้)
DASHBOARD_PORT = 8765
