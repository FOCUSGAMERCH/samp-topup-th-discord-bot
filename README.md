# SA-MP Top-up Discord Bot

บอท Discord สำหรับระบบเติมเงินผู้เล่น SA-MP พัฒนาด้วย Python เชื่อมต่อกับ **Focus v3 API** เพื่อส่งคำขอเติมเงิน และรองรับการสั่งเติมให้เพื่อนผ่านคำสั่งใน Discord

> **ข้อจำกัดการชำระเงิน:** ระบบรองรับเฉพาะการโอนเงินภายในประเทศไทยเท่านั้น ไม่รองรับการโอนเงินจากต่างประเทศหรือการชำระเงินข้ามประเทศ

> **สถานะ Source Code:** Repository นี้จัดทำไว้สำหรับแนะนำโปรเจกต์ ขณะนี้ยังไม่มีการเผยแพร่ source code

## เกี่ยวกับโปรเจกต์

โปรเจกต์นี้ช่วยให้ผู้เล่นส่งคำขอเติมเงินสำหรับเซิร์ฟเวอร์ SA-MP ผ่าน Discord ได้ โดยบอทรับคำสั่งจากผู้ใช้และเชื่อมต่อกับ Focus v3 API เพื่อดำเนินการตามระบบที่ตั้งค่าไว้ นอกจากการเติมเงินให้บัญชีของตนเองแล้ว ยังรองรับการระบุผู้เล่นอื่นเพื่อเติมเงินให้เพื่อนได้ด้วย

ตัวบอทใช้คำสั่งที่ขึ้นต้นด้วย `!` รูปแบบคำสั่งและข้อมูลที่ต้องระบุขึ้นอยู่กับการตั้งค่าของบอทและระบบ API ที่เชื่อมต่อ

## ขอบเขตการเติมเงินและการชำระเงิน

- ใช้สำหรับส่งคำขอเติมเงินให้ผู้เล่นในระบบ SA-MP
- รองรับการเติมเงินให้เพื่อน โดยระบุผู้รับตามรูปแบบที่ระบบกำหนด
- การโอนเงินเพื่อชำระรายการรองรับเฉพาะการโอนภายในประเทศไทย
- ไม่รองรับการโอนเงินระหว่างประเทศหรือการชำระเงินจากต่างประเทศ
- การทำรายการและการแจ้งผลขึ้นอยู่กับการตอบกลับจาก Focus v3 API และการตั้งค่าของระบบ

## ลำดับการทำงานโดยสรุป

1. ผู้ใช้ส่งคำสั่งเติมเงินใน Discord ด้วยคำนำหน้า `!`
2. บอทรับข้อมูลคำขอ เช่น ผู้รับและรายละเอียดที่จำเป็นตามรูปแบบที่ตั้งไว้
3. บอทส่งคำขอไปยัง Focus v3 API
4. ระบบดำเนินการตามผลตอบกลับจาก API และบอทแจ้งสถานะให้ผู้ใช้ทราบใน Discord

## การปรับปรุง

โปรเจกต์รุ่นนี้ปรับการเชื่อมต่อให้รองรับ Focus v3 API เวอร์ชันใหม่ และแก้ไขปัญหาการทำงานที่พบในรุ่นก่อนหน้า

## หมายเหตุ

รายละเอียดรูปแบบคำสั่ง วิธีติดตั้ง และการตั้งค่าการเชื่อมต่อยังไม่ได้ระบุไว้ใน repository นี้ เนื่องจากยังไม่มีการเผยแพร่ source code และคู่มือการติดตั้ง

---

# SA-MP Top-up Discord Bot

A Python-based Discord bot for SA-MP server top-ups. It connects to the **Focus v3 API** to submit top-up requests and supports sending a top-up to a friend through Discord commands.

> **Payment limitation:** Payments are supported only through domestic transfers within Thailand. International transfers and cross-border payments are not supported.

> **Source code status:** This repository currently provides a project description. The source code has not been published.

## About

This project lets players submit top-up requests for an SA-MP server through Discord. The bot receives a user's command and connects to the Focus v3 API to process the request according to the configured system. In addition to topping up their own account, users can also specify another player as the recipient.

Bot commands use the `!` prefix. The exact command syntax and required information depend on the bot's configuration and the connected API system.

## Top-up and payment scope

- Submits top-up requests for players in an SA-MP system.
- Supports topping up a friend by specifying a recipient in the configured format.
- Payment transfers are limited to domestic transfers within Thailand.
- International transfers and payments from outside Thailand are not supported.
- Transaction processing and status notifications depend on the Focus v3 API response and system configuration.

## High-level workflow

1. A user submits a top-up command in Discord with the `!` prefix.
2. The bot receives the request details, such as the recipient and other required information.
3. The bot sends the request to the Focus v3 API.
4. The system handles the API response, and the bot reports the status in Discord.

## Updates

This version updates the integration for the newer Focus v3 API and fixes issues found in an earlier version.

## Notes

Command syntax, installation instructions, and connection setup are not documented in this repository because the source code and setup guide have not been published.
