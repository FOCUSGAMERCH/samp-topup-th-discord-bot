# SA-MP Top-up Discord Bot

บอท Discord สำหรับระบบเติม Cash ให้ผู้เล่นในเซิร์ฟเวอร์ SA-MP พัฒนาด้วย Python ใช้ปุ่มและหน้ากรอกข้อมูลใน Discord เพื่อเริ่มรายการ รองรับเติมให้ตัวเองหรือผู้เล่นคนอื่น และส่งสถานะรายการกลับใน Discord

> **ช่องทางชำระเงินรองรับประเทศไทยเท่านั้น:** PromptPay/โอนผ่านธนาคาร และ TrueMoney Wallet แบบลิงก์ซองอั่งเปา ไม่รองรับการชำระเงินหรือโอนเงินจากต่างประเทศ

> **สถานะ repository:** Repository สาธารณะนี้มี README สำหรับอธิบายโปรเจกต์เท่านั้น ยังไม่ได้เผยแพร่ source code ส่วนคำอธิบายการทำงานด้านล่างอ้างอิงจากโค้ดรุ่นที่ตรวจในเครื่องผู้พัฒนา

## ภาพรวมการทำงาน

1. ผู้เล่นกดปุ่มเติมเงินใน Discord
2. บอทตรวจว่าบัญชี Discord ผูกกับตัวละครในระบบ whitelist แล้วหรือไม่ โดยอ่านข้อมูลจาก MySQL ตาราง `players`
3. ผู้เล่นเลือกเติมให้ตัวเอง หรือเลือกเติมให้เพื่อนและกรอกชื่อตัวละครผู้รับ
4. บอทตรวจชื่อผู้รับกับฐานข้อมูล แล้วให้เลือกช่องทางชำระเงิน
5. บอทตรวจสอบการชำระเงินผ่าน API ของช่องทางนั้น
6. เมื่อ API ยืนยันสำเร็จ บอทบันทึกรายการลง MySQL ตาราง `topup_transactions` และแจ้งผลใน Discord
7. แถวรายการที่สร้างจากการชำระเงินถูกบันทึกเป็น `processed = 0` เพื่อส่งต่อให้ระบบที่ดูแลการเติม Cash ประมวลผล

**การเชื่อมต่อกับเกม:** ในไฟล์บอทที่ตรวจ ไม่พบการเชื่อมต่อโดยตรงกับ SA-MP ผ่าน socket หรือ game-server API ตัวบอทเขียนรายการลง MySQL เป็นจุดส่งต่องาน ดังนั้นการนำรายการไปเพิ่ม Cash ในเกมขึ้นอยู่กับส่วน server-side/ตัวประมวลผลฐานข้อมูลที่เชื่อมกับตารางนี้ ซึ่งอยู่นอก source ของบอทชุดนี้

## ช่องทางชำระเงิน

### PromptPay / ธนาคาร และ QR Code

- ผู้ใช้กรอกจำนวนเงิน โดยขั้นต่ำในโค้ดคือ 10 บาท
- บอทเรียก API เพื่อสร้างรายการชำระเงิน แล้วเรียก API อีกครั้งเพื่อขอรายละเอียด QR
- API ส่งรูป QR กลับมาเป็น Base64 จากนั้นบอทถอดรหัสและแนบรูปให้ผู้ใช้ในข้อความส่วนตัว (ephemeral) บน Discord
- ข้อความ QR แสดงยอดที่ต้องจ่าย ชื่อตัวละครผู้รับ และเวลาหมดอายุตามข้อมูลจาก API
- หลังโอนเงิน ผู้ใช้กดปุ่ม **ยืนยันการโอน** บอทจึงเรียก API เพื่อตรวจสถานะการชำระเงิน
- เมื่อ API ยืนยันสำเร็จ บอทบันทึกยอดและรหัสอ้างอิงลง `topup_transactions`
- โค้ดจำกัดการสร้าง QR ไว้ 3 ครั้งต่อผู้ใช้ในช่วงเวลา 5 นาที
- ช่องทางธนาคาร/PromptPay ปิดช่วง 23:00–02:00 น. ตามเวลาไทย

### TrueMoney Wallet แบบซองอั่งเปา

- ผู้ใช้ส่งลิงก์ซอง TrueMoney ในหน้ากรอกข้อมูลของ Discord
- บอทตรวจรูปแบบลิงก์และเช็กรหัสซองใน `topup_transactions` เพื่อป้องกันใช้รหัสอ้างอิงซ้ำ
- บอทส่งลิงก์ให้ API ตรวจ/รับซอง หาก API ตอบว่าสำเร็จ จะใช้จำนวนเงินที่ API รายงาน
- บอทบันทึกชื่อผู้รับ จำนวนเงิน ช่องทาง และรหัสซองลง `topup_transactions`

ช่องทางทั้งสองเป็นบริการชำระเงินในประเทศไทย รายการจากต่างประเทศไม่รองรับ

## ปุ่มและเมนูใน Discord

โพสต์เติมเงินหลักมีองค์ประกอบดังนี้:

- **เติมเงิน** — ตรวจ whitelist แล้วเริ่มรายการสำหรับตัวละครของผู้ใช้
- **เติมให้เพื่อน** — เปิดหน้ากรอกชื่อตัวละคร ตรวจว่ามีชื่อนั้นในตารางผู้เล่น แล้วเริ่มรายการในชื่อผู้รับ
- **เช็ค Cash** — อ่านยอด `playerWallet` ของตัวละครที่ผูกกับ Discord แล้วแสดงให้ผู้ใช้เห็น
- **เลือกช่องทาง** — ตามค่า UI ใน config รุ่นที่ตรวจ จะแสดงปุ่ม TrueMoney Wallet และธนาคาร/PromptPay; อีกโหมดหนึ่งใช้เมนูเลือก
- **ยืนยันการโอน** — ตรวจผลการชำระ QR กับ API และบันทึกรายการเมื่อสำเร็จ
- **ลิงก์คลิปสอน** — มีปุ่มลิงก์ในโพสต์ แต่ URL ใน source รุ่นที่ตรวจเป็นหน้า YouTube ทั่วไป ควรเปลี่ยนเป็นคลิปคู่มือจริงก่อนใช้งาน

ข้อความตอบกลับรายการส่วนตัวจะมองเห็นเฉพาะผู้กดปุ่ม ส่วน log รายการที่สำเร็จจะถูกส่งไปยังช่องแจ้งเตือนที่ตั้งค่าไว้

## คำสั่งผู้ดูแล

คำสั่งทั้งหมดใช้ prefix `!` และตรวจสิทธิ์จากรายชื่อ owner ที่ตั้งค่าไว้:

- `!setuptopup` — สร้างโพสต์หลักสำหรับเติมเงิน
- `!topupoff` — ปิดการเติมเงินและปิดปุ่มบนโพสต์เป้าหมาย
- `!topupon` — เปิดการเติมเงินอีกครั้ง
- `!refpup` — รีเฟรชหรือแก้คำอธิบายโพสต์เติมเงิน
- `!give <ชื่อตัวละคร> <จำนวน Cash>` — คำสั่งสำรองสำหรับ owner เพื่อเพิ่ม Cash ให้ผู้เล่นโดยตรงในฐานข้อมูล และบันทึก log แบบ manual

คำสั่ง `!give` เป็นการแก้ยอดในฐานข้อมูลโดยตรง ไม่ใช่ขั้นตอนชำระเงินปกติ

## การเชื่อมต่อที่เห็นในโค้ด

โค้ดรุ่นที่ตรวจใช้ MySQL สำหรับอ่านบัญชี whitelist และยอด Cash รวมถึงบันทึกรายการเติมเงิน โดยส่วนชำระเงินเรียก API ของ PromptPay/ธนาคาร และ API สำหรับรับซอง TrueMoney ทั้งนี้รายละเอียดการส่งต่อจากตาราง MySQL ไปยังตัวเกมต้องดู source ฝั่ง server เพิ่มเติม ซึ่งไม่ได้อยู่ในชุดโค้ดบอทที่ตรวจ

## หมายเหตุ

คู่มือติดตั้ง รายการ dependency และ source code ยังไม่ได้เผยแพร่ใน repository นี้ ห้ามนำ credentials หรือ token จากไฟล์ตั้งค่าขึ้น GitHub แบบสาธารณะ

---

# SA-MP Top-up Discord Bot

A Python Discord bot for adding Cash to players in an SA-MP server. Players start a request through Discord buttons and forms. The bot supports topping up the linked account or another player, then reports the transaction status in Discord.

> **Thailand-only payment support:** The reviewed implementation supports Thai PromptPay/bank QR payments and TrueMoney Wallet gift-envelope links. Cross-border transfers and payments from outside Thailand are not supported.

> **Repository status:** This public repository contains a project README only; the source code has not been published. The operational details below are based on the developer's local source files.

## How it works

1. A player presses a top-up button in Discord.
2. The bot checks that the Discord account is linked to a whitelisted game character by querying the MySQL `players` table.
3. The player chooses self top-up or enters another character name as the recipient.
4. For a friend top-up, the bot checks that the recipient exists in the player database.
5. The bot processes payment through the selected payment API.
6. After the API confirms payment, the bot writes a transaction row to MySQL `topup_transactions` and reports the result in Discord.
7. Payment-created rows are stored with `processed = 0` for the connected server-side top-up processor.

**Game-server handoff:** The reviewed bot source does not show a direct SA-MP socket or game-server API connection. It writes a pending row to MySQL as the handoff point. Crediting Cash in-game depends on a separate server-side process that consumes this table; that component is outside this bot source.

## Payment methods

### PromptPay / Bank transfer and QR code

- The user enters an amount; the reviewed code enforces a minimum of 10 THB.
- The bot asks the payment API to create a payment, then requests the QR details.
- The API returns the QR image as Base64. The bot decodes it and attaches the image to an ephemeral Discord response.
- The QR message shows the amount, recipient character, and expiry time returned by the API.
- After paying, the user presses **Confirm Transfer**. The bot calls the API to check the payment status.
- Once confirmed, the bot records the amount and transaction reference in `topup_transactions`.
- QR creation is limited to three attempts per user within a five-minute window.
- The bank/PromptPay option is unavailable from 23:00 to 02:00 Thailand time.

### TrueMoney Wallet gift envelopes

- The user submits a TrueMoney gift-envelope link through a Discord form.
- The bot validates the link format and checks `topup_transactions` for an existing reference to prevent reusing the same gift code.
- The bot sends the link to the wallet API. If the API reports success, the bot uses the amount returned by that API.
- The bot records the recipient, amount, payment method, and gift reference in `topup_transactions`.

Both payment methods are intended for Thailand. Payments originating outside Thailand are not supported.

## Discord buttons and menus

The main top-up post includes:

- **Top up** — checks the whitelist and starts a request for the user's linked character.
- **Top up a friend** — opens a form for a character name, checks that the player exists, and starts a request for that recipient.
- **Check Cash** — reads the linked character's `playerWallet` balance and displays it privately.
- **Payment method** — the reviewed configuration displays TrueMoney Wallet and Bank/PromptPay buttons; an alternate UI mode uses a select menu.
- **Confirm Transfer** — checks the QR payment with the API and records the transaction after success.
- **Tutorial link** — a link button exists, but the URL in the reviewed source points to the general YouTube homepage. Replace it with the actual tutorial before use.

Private interaction responses are visible only to the user. Successful transaction logs are sent to the configured notification channel.

## Owner commands

Commands use the `!` prefix and are restricted to IDs in the configured owner list:

- `!setuptopup` — posts the main top-up panel.
- `!topupoff` — disables top-ups and the buttons on the target post.
- `!topupon` — re-enables top-ups.
- `!refpup` — refreshes the top-up post or changes its description.
- `!give <character> <amount>` — owner-only backup command that directly adds Cash in the database and writes a manual log.

The `!give` command changes the database balance directly; it is not part of the normal payment flow.

## Integrations shown in the source

The reviewed bot uses MySQL to look up whitelisted accounts and Cash balances and to record top-up transactions. Payment processing calls APIs for PromptPay/bank QR payments and TrueMoney gift-envelope redemption. The server-side process that reads the MySQL transaction rows must be reviewed separately to confirm how those rows become in-game Cash.

## Notes

Installation instructions, dependencies, and source code have not been published in this repository. Do not commit credentials or tokens from the configuration file to a public repository.
