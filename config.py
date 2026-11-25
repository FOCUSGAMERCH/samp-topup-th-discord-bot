# ==== Discord: บอทและสิทธิ์ ====
# Token สำหรับให้บอทล็อกอิน Discord ค่านี้สร้างจาก Discord Developer Portal
token = ""
# รายการ Server ID (Guild ID) ที่อนุญาตให้บอททำงาน เช่น [123456789012345678]
guild_id = []
# รายการ Discord User ID ของผู้ดูแลที่ใช้คำสั่งแอดมินได้ เช่น [123456789012345678]
OWNERS = []
# Channel ID ที่ใช้ส่ง log รายการเติมเงิน
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

# ==== PromptPay / โอนธนาคาร: API สร้าง QR และตรวจรายการ ====
# ชื่อผู้ใช้บัญชี API จากผู้ให้บริการ QR/PromptPay
username = ""
# รหัสผ่านบัญชี API จากผู้ให้บริการ
password = ""
# Connection ID ที่ผู้ให้บริการออกให้
con_id = ""
# ประเภทปลายทางที่ API ใช้: "01" คือ PromptPay เบอร์โทร (เลือกตามบัญชีผู้ให้บริการ)
type = "01"
# เบอร์หรือ PromptPay ID ที่รับเงิน
promptpay_id = ""
# เลขบัญชีธนาคารที่ผูกกับ API (กรอกเมื่อผู้ให้บริการกำหนด)
account_no = ""
# รหัสบัญชีหรือรหัสยืนยันที่ API ต้องใช้ (กรอกตามข้อมูลจากผู้ให้บริการ)
acccode = ""
# URL API สำหรับสร้าง QR/ตรวจสอบรายการโอน ตามบริการที่ใช้งาน
TMWEASY_ENDPOINT = "https://tmwallet.thaighost.net/apipp.php"
# เวลาสูงสุดที่รอการตอบกลับ API หน่วยเป็นวินาที
TMWEASY_TIMEOUT = 20

# ==== TrueMoney Wallet: ตรวจสอบซองอั่งเปา ====
# URL API สำหรับตรวจสอบซอง เปลี่ยนเป็น endpoint ที่ได้รับจากผู้ให้บริการ
APIWALLET_ENDPOINT = "https://www.tmweasy.com/apiwallet.php"
# เวลาสูงสุดที่รอการตอบกลับ API หน่วยเป็นวินาที
APIWALLET_TIMEOUT = 20
# เบอร์ TrueMoney Wallet ที่ใช้รับซอง
tmemail = ""

# ==== รูปแบบเมนูชำระเงินใน Discord ====
# "01" = เมนูให้เลือกช่องทาง | "02" = แสดงปุ่ม Wallet และธนาคาร
TOPUP_UI_TYPE = "02"
# รูปแบบ QR code ที่ใช้ในโพสต์ เลือกค่าตามรูปแบบที่ระบบรองรับ
TOPUP_QRCODE_TYPE = "01"

# พอร์ตหน้าเว็บสรุป Top-up ซึ่งเปิดให้เข้าจากเครื่องนี้เท่านั้น
DASHBOARD_PORT = 8765
