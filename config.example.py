"""คัดลอกไฟล์นี้เป็น config.py แล้วกรอกค่าของตัวเองก่อนเปิดบอท"""

# ==== Discord: บอทและสิทธิ์ ====
# Token สำหรับล็อกอินบอท ห้ามแชร์หรืออัปโหลดขึ้น GitHub
token = ""
# Server ID ที่อนุญาตให้บอททำงาน
guild_id = []
# Discord User ID ของผู้ดูแลที่ใช้คำสั่งแอดมินได้
OWNERS = []
# Channel ID สำหรับรับ log รายการเติมเงิน
channeltopupnotify = 0

# ==== MySQL: ฐานข้อมูลเกม ====
configsql = {
    # ชื่อผู้ใช้ฐานข้อมูล
    "user": "root",
    # รหัสผ่านฐานข้อมูล
    "password": "",
    # เครื่องที่รัน MySQL
    "host": "127.0.0.1",
    # ชื่อฐานข้อมูล
    "database": "your_database",
}

# ==== PromptPay / โอนธนาคาร: API สร้าง QR ====
username = ""
password = ""
con_id = ""
# "01" สำหรับ PromptPay เบอร์โทร; ใช้ค่าตามการตั้งค่าผู้ให้บริการ
type = "01"
promptpay_id = ""
account_no = ""
acccode = ""
TMWEASY_ENDPOINT = "https://tmwallet.thaighost.net/apipp.php"
TMWEASY_TIMEOUT = 20

# ==== TrueMoney Wallet: ซองอั่งเปา ====
APIWALLET_ENDPOINT = "https://www.tmweasy.com/apiwallet.php"
APIWALLET_TIMEOUT = 20
tmemail = ""

# ==== หน้าตาเมนูใน Discord ====
# "01" = เมนูเลือกช่องทาง | "02" = ปุ่ม Wallet และธนาคาร
TOPUP_UI_TYPE = "02"
# รูปแบบ QR code ที่ใช้ในโพสต์
TOPUP_QRCODE_TYPE = "01"

# พอร์ตเว็บสรุป Top-up (เปิดเฉพาะเครื่องนี้)
DASHBOARD_PORT = 8765
