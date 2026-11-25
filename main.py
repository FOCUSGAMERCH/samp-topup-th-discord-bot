import asyncio
import base64
import io
import os
import re
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import mysql.connector
import nextcord
import requests
from nextcord.ext import commands
from nextcord.ui import TextInput

import config
import database
import dashboard

# ========= Discord Bot =========
intents = nextcord.Intents.all()
bot = commands.Bot(command_prefix="!", help_command=None, intents=intents)

# ========= Global Switch เปิด/ปิดปุ่มเติมเงิน =========
TOPUP_ENABLED = True  # เริ่มต้นเปิด

# ========= Cooldown / Rate Limit สำหรับสร้าง QR PromptPay =========
QR_MAX_ATTEMPTS = 3               # อนุญาตสูงสุด 3 ครั้ง
QR_WINDOW_SECONDS = 5 * 60        # ภายใน 5 นาที

qr_attempts = defaultdict(lambda: deque(maxlen=QR_MAX_ATTEMPTS + 2))

def check_qr_rate_limit(user_id: int) -> tuple[bool, int]:
    """
    ตรวจสอบว่าผู้ใช้ยังสร้าง QR ได้หรือไม่
    Returns: (is_limited: bool, remaining_minutes: int)
    """
    now = datetime.now(TH_TZ)
    attempts = qr_attempts[user_id]

    # ลบ record เก่าที่อยู่นอกหน้าต่างเวลา
    while attempts and (now - attempts[0]).total_seconds() > QR_WINDOW_SECONDS:
        attempts.popleft()

    # ยังไม่ถึงขีดจำกัด → อนุญาต + บันทึกเวลาครั้งนี้
    if len(attempts) < QR_MAX_ATTEMPTS:
        attempts.append(now)
        return False, 0

    # เกินขีดจำกัด → คำนวณเวลาที่เหลือ
    if attempts:
        oldest = attempts[0]
        time_passed = (now - oldest).total_seconds()
        remaining_sec = max(0, QR_WINDOW_SECONDS - time_passed)
        return True, int((remaining_sec + 59) // 60)  # ปัดขึ้นเป็นนาที

    return False, 0

# ========= Helpers: เวลา / DB / Embed =========
TH_TZ = timezone(timedelta(hours=7))  # Asia/Bangkok (+07:00)

def now_th_text():
    t = datetime.now(TH_TZ)
    return t.strftime("%d/%m/%Y %H:%M:%S") + " (GMT+7)"

def is_bank_maintenance() -> bool:
    """ตรวจสอบว่าอยู่ในช่วงปิดปรับปรุงธนาคารหรือไม่ (23:00 - 02:00)"""
    now = datetime.now(TH_TZ)
    hour = now.hour
    return hour >= 23 or hour < 2

# === ข้อความแจ้งเตือนธนาคารปิดปรับปรุง ===
BANK_MAINTENANCE_MESSAGE = (
    "เนื่องจากธนาคารจะปิดปรับปรุงระบบในช่วงเวลา **23.00 - 02.00 น. ของทุกวัน**\n"
    "รบกวนหลีกเลี่ยงการเติม Cash ในเวลานี้นะครับ\n"
    "หากเครดิตไม่เข้า/เข้าช้า **แจ้งแอดมินได้เลยครับ**"
)

def fetch_player_by_discord_id(did: int):
    try:
        return database.get_player_by_discord_id(did)
    except mysql.connector.Error:
        return None

def fetch_player_by_name(pname: str):
    try:
        return database.get_player_by_name(pname)
    except mysql.connector.Error:
        return None

def build_topup_embed(description_override: str = None) -> nextcord.Embed:
    default_desc = (
        "--------------------\n"
        "> `✨` ระบบเติมเงินอัตโนมัติ 24 ชั่วโมง\n"
        "> `⚠️` ขั้นต่ำเพียง 10 บาท\n"
        "--------------------\n"
        "**ระบบรองรับการเติม Cash ให้ตนเองหรือให้เพื่อน**\n"
        "ระบบจะดำเนินการทันทีหลังจากชำระเงินสำเร็จ\n\n"
        "**⚠️ หมายเหตุ:**\n"
        "• เติมผ่านธนาคาร **ไม่สามารถใช้ได้ช่วง 23:00 - 02:00 น.** (ปิดปรับปรุงระบบ)\n"
        "• ใช้ **TrueMoney Wallet (ซองอั่งเปา)** ได้ตลอด 24 ชม."
    )
    embed = nextcord.Embed(
        title='`💸` Training Park | เติม Cash อัตโนมัติ',
        description=description_override if description_override is not None else default_desc,
        color=nextcord.Color.from_rgb(255, 0, 0)
    )
    embed.add_field(
        name="`📌` หมายเหตุเพิ่มเติม",
        value="หากเครดิตไม่เข้า/เข้าช้าในช่วงปิดปรับปรุง → แจ้งแอดมินได้เลย",
        inline=False
    )
    embed.set_image(url="https://images-ext-1.discordapp.net/external/lt2pXQqpuwxgW6yY_8m8hlVLf2k3NrgXPGvGDfC5kmQ/https/share.creavite.co/p1Ym2vUqJzD3WEtv.gif")
    return embed

async def check_whitelist(interaction: nextcord.Interaction):
    try:
        row = database.get_whitelisted_player(interaction.user.id)
        if not row or not row.get("playerName"):
            try:
                await interaction.response.send_message(
                    "**คุณยังไม่เคยรับไวท์ลิสต์!**\nกรุณาไปที่ห้องรับไวท์ลิสต์และดำเนินการให้เรียบร้อยก่อน",
                    ephemeral=True
                )
            except nextcord.errors.InteractionResponded:
                await interaction.followup.send(
                    "**คุณยังไม่เคยรับไวท์ลิสต์!**\nกรุณาไปที่ห้องรับไวท์ลิสต์และดำเนินการให้เรียบร้อยก่อน",
                    ephemeral=True
                )
            return None
        return row
    except mysql.connector.Error as err:
        msg = ("เกิดข้อผิดพลาด: โครงสร้างฐานข้อมูลไม่ถูกต้อง โปรดติดต่อผู้ดูแล"
               if "Unknown column" in getattr(err, "msg", str(err))
               else "เกิดข้อผิดพลาดกับฐานข้อมูล")
        try:
            await interaction.response.send_message(msg, ephemeral=True)
        except nextcord.errors.InteractionResponded:
            await interaction.followup.send(msg, ephemeral=True)
        return None

# ========= View: ปุ่มยืนยันหลังสร้าง QR (PromptPay/ธนาคาร) =========
class PaymentView(nextcord.ui.View):
    def __init__(self, id_pay, timereal_min, amount_check, playername):
        super().__init__(timeout=None)
        self.id_play = id_pay
        self.timereal_min = timereal_min
        self.playername = playername
        self.amount_check = amount_check

    @nextcord.ui.button(
        label="ยืนยันการโอน",
        emoji="<a:botsever16:1184867493379055617>",
        custom_id="submit_confirm_payment",
        style=nextcord.ButtonStyle.gray,
        row=1
    )
    async def submit(self, button: nextcord.Button, interaction: nextcord.Interaction):
        if not TOPUP_ENABLED:
            return await interaction.response.send_message(
                "ขณะนี้ปิดการเติมเงินชั่วคราว กรุณาลองใหม่ภายหลัง", ephemeral=True
            )
        await interaction.response.send_message(
            embed=nextcord.Embed(description="> `🔍` กำลังตรวจสอบ โปรดรอสักครู่!!", color=nextcord.Color.greyple()),
            ephemeral=True
        )
        msg = await interaction.original_message()
        for dots in [".", "..", "..."]:
            await asyncio.sleep(0.5)
            await msg.edit(embed=nextcord.Embed(description=f"> `🔄` Loading {dots}", color=nextcord.Color.blue()))
        await asyncio.sleep(0.4)
        await msg.edit(embed=nextcord.Embed(description="> `✅` Loading สำเร็จแล้ว", color=nextcord.Color.green()))
        params = {
            "username": config.username,
            "password": config.password,
            "con_id": config.con_id,
            "id_pay": self.id_play,
            "accode": getattr(config, "acccode", None),
            "account_no": getattr(config, "account_no", None),
            "ip": interaction.user.id,
            "method": "confirm",
        }
        try:
            resp = requests.get(
                "https://tmwallet.thaighost.net/apipp.php",
                params=params,
                timeout=15,
            )
        except requests.RequestException as e:
            await msg.edit(content=f"API มีปัญหา โปรดติดต่อแอดมิน\nรายละเอียด: {e}")
            return
        if resp.status_code != 200:
            await msg.edit(content="API มีปัญหาโปรดติดต่อแอดมิน")
            return
        data = resp.json()
        if data.get("status") != 1:
            await msg.edit(embed=nextcord.Embed(
                title="`❌` คุณยังไม่ได้ดำเนินการโอนเงิน `❌`",
                description="> `⚠️` หากชำระแล้ว กรุณารอ 1-5 นาที แล้วกดยืนยันอีกครั้ง",
                color=nextcord.Color.red()
            ))
            return
        tnx_id = data.get("tnx_id")
        amount = float(self.amount_check)
        points_to_add = int(amount)
        try:
            database.add_topup_transaction(
                self.playername,
                points_to_add,
                "promptpay",
                tnx_id,
            )
        except mysql.connector.Error as err:
            await msg.edit(embed=nextcord.Embed(
                title="`❌` เกิดข้อผิดพลาดทางด้านฐานข้อมูล",
                description=f"โปรดติดต่อผู้ดูแลระบบ\nรายละเอียด: {err}",
                color=nextcord.Color.red()
            ), view=None)
            return
        finally:
            try:
                cursor.close(); conn.close()
            except Exception:
                pass
        channel = bot.get_channel(getattr(config, "channeltopupnotify", 0))
        if channel:
            payer = interaction.user
            payer_db = fetch_player_by_discord_id(payer.id)
            payer_game = payer_db["playerName"] if payer_db and payer_db.get("playerName") else None
            is_friend_topup = payer_game != self.playername
            if is_friend_topup:
                rec_db = fetch_player_by_name(self.playername)
                rec_discord_id = rec_db["DiscordIDWhitelist"] if rec_db and rec_db.get("DiscordIDWhitelist") else None
                payer_lines = [f"ผู้ชำระ: {payer.mention} (ID: `{payer.id}`)"]
                if payer_game:
                    payer_lines.append(f"ชื่อตัวละครผู้ชำระ: `{payer_game}`")
                recipient_lines = [f"ผู้รับ: `{self.playername}`"]
                if rec_discord_id:
                    recipient_lines.append(f"Discord ผู้รับ: <@{rec_discord_id}> (ID: `{rec_discord_id}`)")
                detail_text = (
                    "\n".join(payer_lines) + "\n\n" +
                    "\n".join(recipient_lines) + "\n\n" +
                    f"จำนวน: **{points_to_add}** Cash\n"
                    f"ช่องทาง: **PromptPay/ธนาคาร**\n"
                    f"อ้างอิง: `{tnx_id}`\n"
                    f"เวลา (TH): `{now_th_text()}`"
                )
                log_title = "`🎁` รายการเติมเงินให้เพื่อน/คนอื่น (PromptPay/ธนาคาร)"
            else:
                detail_text = (
                    f"ผู้เล่น: {payer.mention} (`{payer_game}`)\n"
                    f"จำนวน: **{points_to_add}** Cash\n"
                    f"ช่องทาง: **PromptPay/ธนาคาร**\n"
                    f"อ้างอิง: `{tnx_id}`\n"
                    f"เวลา (TH): `{now_th_text()}`"
                )
                log_title = "`🔔` รายการเติมเงินใหม่ (PromptPay/ธนาคาร)"
            embed_log = nextcord.Embed(
                title=log_title,
                description=detail_text,
                color=nextcord.Color.from_rgb(72, 228, 154),
                timestamp=datetime.now(timezone.utc)
            )
            try:
                embed_log.set_thumbnail(url=payer.display_avatar.url)
            except Exception:
                pass
            embed_log.set_footer(
                text=f"Requested by {interaction.user.name}",
                icon_url=(interaction.user.avatar.url if interaction.user.avatar else None)
            )
            await channel.send(embed=embed_log)
        await msg.edit(embed=nextcord.Embed(
            title="`✅` ยืนยันการชำระเงินสำเร็จ",
            description=(
                "ระบบได้รับข้อมูลการชำระเงินของคุณแล้ว\n"
                f"`👤` **ชื่อ:** `{self.playername}`\n"
                f"`💸` **จำนวน:** `{points_to_add}` Cash\n\n"
                "**กรุณารอรับไอเทมในเกมสักครู่ ขอบคุณครับ**"
            ),
            color=nextcord.Color.green()
        ), view=None)

# ========= Modal: TrueMoney Wallet (ซองอั่งเปา ผ่าน tmweasyapi) =========
class WalletModal(nextcord.ui.Modal):
    def __init__(self, whitelisted_name: str) -> None:
        super().__init__(title="เติมเงินผ่านวอเลท (ซองอั่งเปา)", timeout=None, custom_id="item-walletmodal-new")
        self.whitelisted_name = whitelisted_name
        self.link = TextInput(
            label="ลิงก์ซองอั่งเปา TrueMoney",
            placeholder="https://gift.truemoney.com/campaign/?v=xxxxxxxxxxxxxxx",
            style=nextcord.TextInputStyle.short,
            required=True
        )
        self.add_item(self.link)
        self.player = TextInput(
            label="ชื่อตัวละครผู้รับ (ไม่บังคับ)",
            default_value=self.whitelisted_name,
            style=nextcord.TextInputStyle.short,
            required=False
        )
        self.add_item(self.player)
        self._tm_pattern = re.compile(r"^https:\/\/gift\.truemoney\.com\/campaign\/(\?|)v=[a-zA-Z0-9]+$")

    def _is_valid_truemoney_link(self, link: str) -> bool:
        return self._tm_pattern.match(link) is not None

    @staticmethod
    def _extract_gift_key(link: str) -> str:
        try:
            return link.split("v=")[1]
        except Exception:
            return link

    async def callback(self, interaction: nextcord.Interaction):
        if not TOPUP_ENABLED:
            return await interaction.response.send_message(
                "ขณะนี้ปิดการเติมเงินชั่วคราว กรุณาลองใหม่ภายหลัง", ephemeral=True
            )
        gift_link = str(self.link.value).strip().replace(" ", "")
        if "/campaign?v=" in gift_link:
            gift_link = gift_link.replace("/campaign?v=", "/campaign/?v=")
        input_name = (self.player.value or "").strip()
        playername_to_check = input_name if input_name else self.whitelisted_name
        await interaction.response.send_message(
            embed=nextcord.Embed(description="> `🔍` กำลังตรวจสอบซองอั่งเปา...", color=nextcord.Color.greyple()),
            ephemeral=True
        )
        msg = await interaction.original_message()
        if not self._is_valid_truemoney_link(gift_link):
            return await msg.edit(embed=nextcord.Embed(
                description="> `❌` กรุณาใส่ลิงก์ซองอั่งเปา TrueMoney ให้ถูกต้อง",
                color=nextcord.Color.red()
            ))
        gift_key = self._extract_gift_key(gift_link)
        try:
            exists = database.transaction_reference_exists(gift_key)
        except mysql.connector.Error as err:
            return await msg.edit(embed=nextcord.Embed(
                title="`❌` ตรวจสอบซองล้มเหลว",
                description=f"โปรดติดต่อผู้ดูแลระบบ\nรายละเอียด: {err}",
                color=nextcord.Color.red()
            ))
        if exists:
            return await msg.edit(embed=nextcord.Embed(
                description="> `⚠️` ซองนี้ถูกใช้งานไปแล้วในระบบ (กันรับซ้ำ 1 คนต่อ 1 ซอง)",
                color=nextcord.Color.orange()
            ))
        params = {
            "username": config.username,
            "password": config.password,
            "tmemail": config.tmemail,
            "transactionid": gift_link,
            "clientip": str(interaction.user.id),
            "ref1": str(interaction.user.id),
            "action": "yes",
            "json": "1",
        }
        try:
            r = requests.get(
                "https://www.tmweasy.com/apiwallet.php",
                params=params,
                timeout=20,
            )
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as e:
            return await msg.edit(embed=nextcord.Embed(
                description=f"> `❌` เชื่อมต่อ tmweasy ล้มเหลว: {e}",
                color=nextcord.Color.red()
            ))
        except ValueError:
            return await msg.edit(embed=nextcord.Embed(
                description="> `❌` tmweasy ตอบกลับไม่ใช่ JSON",
                color=nextcord.Color.red()
            ))
        status = str(data.get("Status", "")).lower()
        msg_api = str(data.get("Msg", "") or "")
        amount = data.get("Amount", 0)
        if status != "check_success":
            reason = "ไม่สามารถรับซองได้"
            if "หมดอายุ" in msg_api: reason = "ซองหมดอายุ"
            elif "ใช้แล้ว" in msg_api: reason = "มีคนรับไปแล้ว"
            elif "เต็ม" in msg_api: reason = "ซองครบจำนวนผู้รับแล้ว"
            elif "ไม่ถูกต้อง" in msg_api: reason = "ลิงก์ซองไม่ถูกต้อง"
            return await msg.edit(embed=nextcord.Embed(
                description=f"> `❌` {reason}",
                color=nextcord.Color.red()
            ))
        try:
            amount_f = float(amount)
        except (TypeError, ValueError):
            amount_f = 0.0
        points_to_add = int(amount_f)
        try:
            database.add_topup_transaction(
                playername_to_check,
                points_to_add,
                "truemoney",
                gift_key,
            )
        except mysql.connector.Error as err:
            return await msg.edit(embed=nextcord.Embed(
                title="`❌` เกิดข้อผิดพลาดฐานข้อมูล",
                description=f"โปรดติดต่อผู้ดูแลระบบ\nรายละเอียด: {err}",
                color=nextcord.Color.red()
            ))
        channel = bot.get_channel(getattr(config, "channeltopupnotify", 0))
        if channel:
            payer = interaction.user
            payer_db = fetch_player_by_discord_id(payer.id)
            payer_game = payer_db["playerName"] if payer_db and payer_db.get("playerName") else None
            is_friend_topup = payer_game != playername_to_check
            if is_friend_topup:
                rec_db = fetch_player_by_name(playername_to_check)
                rec_discord_id = rec_db["DiscordIDWhitelist"] if rec_db and rec_db.get("DiscordIDWhitelist") else None
                payer_lines = [f"ผู้ชำระ: {payer.mention} (ID: `{payer.id}`)"]
                if payer_game:
                    payer_lines.append(f"ชื่อตัวละครผู้ชำระ: `{payer_game}`")
                recipient_lines = [f"ผู้รับ: `{playername_to_check}`"]
                if rec_discord_id:
                    recipient_lines.append(f"Discord ผู้รับ: <@{rec_discord_id}> (ID: `{rec_discord_id}`)")
                detail_text = (
                    "\n".join(payer_lines) + "\n\n" +
                    "\n".join(recipient_lines) + "\n\n" +
                    f"จำนวน: **{points_to_add}** Cash\n"
                    f"ช่องทาง: **TrueMoney (ซองอั่งเปา)**\n"
                    f"อ้างอิง: `{gift_key}`\n"
                    f"เวลา (TH): `{now_th_text()}`"
                )
                log_title = "`🎁` เติมให้เพื่อน/คนอื่น (ซองอั่งเปา)"
            else:
                detail_text = (
                    f"ผู้เล่น: {payer.mention} (`{payer_game}`)\n"
                    f"จำนวน: **{points_to_add}** Cash\n"
                    f"ช่องทาง: **TrueMoney (ซองอั่งเปา)**\n"
                    f"อ้างอิง: `{gift_key}`\n"
                    f"เวลา (TH): `{now_th_text()}`"
                )
                log_title = "`🔔` รายการเติมเงินใหม่ (ซองอั่งเปา)"
            embed_log = nextcord.Embed(
                title=log_title,
                description=detail_text,
                color=nextcord.Color.from_rgb(255, 90, 0),
                timestamp=datetime.now(timezone.utc)
            )
            try:
                embed_log.set_thumbnail(url=payer.display_avatar.url)
            except Exception:
                pass
            embed_log.set_footer(
                text=f"Requested by {interaction.user.name}",
                icon_url=(interaction.user.avatar.url if interaction.user.avatar else None)
            )
            await channel.send(embed=embed_log)
        await msg.edit(embed=nextcord.Embed(
            title="`✅` รับซองอั่งเปาสำเร็จ",
            description=(
                "ระบบรับซองของคุณเรียบร้อย\n"
                f"`👤` **ชื่อ:** `{playername_to_check}`\n"
                f"`💸` **จำนวน:** `{points_to_add}` Cash\n\n"
                "**กรุณารอรับไอเทมในเกมสักครู่ ขอบคุณครับ**"
            ),
            color=nextcord.Color.green()
        ))

# ========= Modal: ธนาคาร / PromptPay =========
class BankModal(nextcord.ui.Modal):
    def __init__(self, whitelisted_name: str) -> None:
        super().__init__(title="เติมเงินผ่านธนาคาร", timeout=None, custom_id="item-bankmodal-new")
        self.whitelisted_name = whitelisted_name
        self.label = TextInput(
            label="ชื่อตัวละครผู้รับ (ไม่บังคับ)",
            default_value=self.whitelisted_name,
            style=nextcord.TextInputStyle.short,
            required=False
        )
        self.add_item(self.label)
        self.amount = TextInput(
            label="จำนวนที่ต้องการเติม",
            placeholder="10",
            style=nextcord.TextInputStyle.short,
            required=True,
            min_length=2,
            max_length=6
        )
        self.add_item(self.amount)

    async def callback(self, interaction: nextcord.Interaction):
        if not TOPUP_ENABLED:
            return await interaction.response.send_message(
                "ขณะนี้ปิดการเติมเงินชั่วคราว กรุณาลองใหม่ภายหลัง", ephemeral=True
            )

        # === ตรวจสอบช่วงปิดปรับปรุงธนาคาร ===
        if is_bank_maintenance():
            return await interaction.response.send_message(
                embed=nextcord.Embed(
                    title="ธนาคารปิดปรับปรุงระบบ",
                    description=BANK_MAINTENANCE_MESSAGE,
                    color=nextcord.Color.red()
                ).set_footer(text="กรุณาใช้ TrueMoney Wallet (ซองอั่งเปา) แทนในช่วงนี้"),
                ephemeral=True
            )

        # =========== ตรวจสอบ Rate Limit การสร้าง QR (ป้องกันสแปม) ===========
        user_id = interaction.user.id
        is_limited, remaining_min = check_qr_rate_limit(user_id)

        if is_limited:
            return await interaction.response.send_message(
                embed=nextcord.Embed(
                    title="⏳ กรุณารอสักครู่",
                    description=(
                        f"คุณสร้าง QR ถี่เกินไป\n"
                        f"กรุณารออีกประมาณ **{remaining_min} นาที** ก่อนสร้าง QR ใหม่"
                    ),
                    color=nextcord.Color.orange()
                ),
                ephemeral=True
            )
        # ==================================================================

        input_name = (self.label.value or "").strip()
        playername_to_check = input_name if input_name else self.whitelisted_name

        await interaction.response.send_message(
            embed=nextcord.Embed(description="> `🔃` กำลังตรวจสอบข้อมูล", color=nextcord.Color.blue()),
            ephemeral=True
        )
        msg = await interaction.original_message()

        try:
            amount_val = int(str(self.amount.value).strip())
            if amount_val < 10:
                return await msg.edit(embed=nextcord.Embed(
                    description="> `❌` ขั้นต่ำ 10 บาท กรุณาระบุจำนวนเงินให้ถูกต้อง",
                    color=nextcord.Color.orange()
                ))
        except ValueError:
            return await msg.edit(embed=nextcord.Embed(
                description="> `❌` กรุณาระบุจำนวนเงินเป็นตัวเลขเท่านั้น",
                color=nextcord.Color.orange()
            ))

        params_create = {
            "username": config.username, "password": config.password, "con_id": config.con_id,
            "amount": amount_val, "ref1": interaction.user.id, "method": "create_pay",
        }
        try:
            resp = requests.get(
                "https://tmwallet.thaighost.net/apipp.php",
                params=params_create,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") != 1:
                return await msg.edit(embed=nextcord.Embed(
                    description=f"เกิดข้อผิดพลาด: {data.get('msg')}", color=nextcord.Color.red()
                ))
        except requests.RequestException as e:
            return await msg.edit(embed=nextcord.Embed(
                description=f"> `❌` ติดต่อ API ไม่ได้: {e}", color=nextcord.Color.red()
            ))

        id_pay = data["id_pay"]

        params_detail = {
            "username": config.username, "password": config.password, "con_id": config.con_id,
            "id_pay": id_pay, "promptpay_id": getattr(config, "promptpay_id", None),
            "type": getattr(config, "type", None), "method": "detail_pay",
        }
        try:
            resp_detail = requests.get(
                "https://tmwallet.thaighost.net/apipp.php",
                params=params_detail,
                timeout=15,
            )
            resp_detail.raise_for_status()
            detail = resp_detail.json()
            if detail.get("status") != 1:
                return await msg.edit(embed=nextcord.Embed(
                    description="> `❌` ระบบผิดพลาดโปรดแจ้งแอดมิน", color=nextcord.Color.red()
                ))
        except requests.RequestException as e:
            return await msg.edit(embed=nextcord.Embed(
                description=f"> `❌` ติดต่อ API ไม่ได้: {e}", color=nextcord.Color.red()
            ))

        try:
            image_b64 = detail["qr_image_base64"]
            image_data = base64.b64decode(image_b64)
            image_file = io.BytesIO(image_data)
            qr_filename = "QR_Payment.png"
            file_to_send = nextcord.File(fp=image_file, filename=qr_filename)
        except (KeyError, TypeError, base64.binascii.Error):
            return await msg.edit(embed=nextcord.Embed(
                description="> `❌` API ไม่ได้ส่งรูป QR Code หรือข้อมูลรูปภาพไม่ถูกต้อง",
                color=nextcord.Color.red()
            ))

        timeout_min = int(detail["time_out"]) // 60
        amount_check = int(detail["amount_check"]) / 100.0

        embed = nextcord.Embed(
            title="`📝` เติมเงินสแกนคิวอาร์โค้ด",
            description=(
                "`✅` สแกนจ่ายแล้วกด **`ยืนยันการโอน`**\n"
                f"`⚠️` กรุณาชำระภายใน {timeout_min} นาที\n"
                "`📱` รองรับทุกธนาคาร"
            ),
            color=nextcord.Color.green()
        )
        embed.set_image(url=f"attachment://{qr_filename}")
        embed.add_field(name="`📃` ยอดที่ต้องชำระ", value=f"```{amount_check:.2f}```", inline=True)
        embed.add_field(name="`🎁` ชำระเงินให้ ", value=f"```{playername_to_check}```", inline=True)
        embed.set_footer(
            text="สแกนคิวอาร์โค้ด • บันทึกรูปภาพไปสแกน",
            icon_url="https://media.discordapp.net/attachments/1020289567703695401/1020289567909224559/Untitled.png?format=webp&quality=lossless"
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True,
            file=file_to_send,
            view=PaymentView(id_pay, timeout_min, amount_check, playername_to_check)
        )

# ========= เลือกช่องทางตอนเติมให้เพื่อน =========
class FriendMethodSelect(nextcord.ui.StringSelect):
    def __init__(self, player_name: str):
        self.player_name = player_name
        options = [
            nextcord.SelectOption(label="TrueMoney Wallet (ซองอั่งเปา)", value="wallet", emoji="🧧"),
            nextcord.SelectOption(label="ธนาคาร / PromptPay", value="bank", emoji="🏦"),
        ]
        super().__init__(
            placeholder="เลือกช่องทาง (ให้เพื่อน)",
            min_values=1, max_values=1, options=options, custom_id="friend_topup_method_select"
        )

    async def callback(self, interaction: nextcord.Interaction):
        if not TOPUP_ENABLED:
            return await interaction.response.send_message("ขณะนี้ปิดการเติมเงินชั่วคราว กรุณาลองใหม่ภายหลัง", ephemeral=True)
        player_data = await check_whitelist(interaction)
        if not player_data:
            return
        if self.values[0] == "wallet":
            await interaction.response.send_modal(WalletModal(whitelisted_name=self.player_name))
        else:
            if is_bank_maintenance():
                return await interaction.response.send_message(
                    embed=nextcord.Embed(
                        title="ธนาคารปิดปรับปรุงระบบ",
                        description=BANK_MAINTENANCE_MESSAGE,
                        color=nextcord.Color.red()
                    ).set_footer(text="ใช้ TrueMoney Wallet แทนได้เลย!"),
                    ephemeral=True
                )
            await interaction.response.send_modal(BankModal(whitelisted_name=self.player_name))

class FriendSelectView(nextcord.ui.View):
    def __init__(self, player_name: str):
        super().__init__(timeout=120)
        self.add_item(FriendMethodSelect(player_name))

# ========= View ปุ่มสองอัน (โหมด 02) =========
class TopupButtonsView(nextcord.ui.View):
    def __init__(self, player_name: str):
        super().__init__(timeout=120)
        self.player_name = player_name

        wallet_btn = nextcord.ui.Button(
            label="เติมผ่านวอเลท 🧧", style=nextcord.ButtonStyle.green, custom_id="btn_topup_wallet", row=1
        )
        wallet_btn.callback = self.wallet_callback
        self.add_item(wallet_btn)

        bank_label = "ธนาคาร / PromptPay (ปิด 23:00-02:00)" if is_bank_maintenance() else "ธนาคาร / PromptPay"
        bank_style = nextcord.ButtonStyle.grey if is_bank_maintenance() else nextcord.ButtonStyle.blurple
        bank_disabled = is_bank_maintenance()

        bank_btn = nextcord.ui.Button(
            label=bank_label, style=bank_style, custom_id="btn_topup_bank", row=1, disabled=bank_disabled
        )
        bank_btn.callback = self.bank_callback
        self.add_item(bank_btn)

    async def wallet_callback(self, interaction: nextcord.Interaction):
        if not TOPUP_ENABLED:
            return await interaction.response.send_message("ขณะนี้ปิดการเติมเงินชั่วคราว กรุณาลองใหม่ภายหลัง", ephemeral=True)
        await interaction.response.send_modal(WalletModal(whitelisted_name=self.player_name))

    async def bank_callback(self, interaction: nextcord.Interaction):
        if not TOPUP_ENABLED:
            return await interaction.response.send_message("ขณะนี้ปิดการเติมเงินชั่วคราว กรุณาลองใหม่ภายหลัง", ephemeral=True)
        if is_bank_maintenance():
            return await interaction.response.send_message(
                embed=nextcord.Embed(
                    title="ธนาคารปิดปรับปรุงระบบ",
                    description=BANK_MAINTENANCE_MESSAGE,
                    color=nextcord.Color.red()
                ).set_footer(text="ใช้ TrueMoney Wallet แทนได้เลย!"),
                ephemeral=True
            )
        await interaction.response.send_modal(BankModal(whitelisted_name=self.player_name))

# ========= View หลัก =========
class TopupEntry(nextcord.ui.View):
    def __init__(self, enabled: bool = True):
        super().__init__(timeout=None)
        self.add_item(nextcord.ui.Button(
            style=nextcord.ButtonStyle.link,
            label="คลิปสอนเติมเงิน คลิ๊กเลย!!",
            emoji="<:botsever6:1184837744611049512>",
            url="https://www.youtube.com",
            row=3
        ))
        self.open_topup_button = nextcord.ui.Button(
            label='[💸] เติมเงิน',
            custom_id='topup_open',
            style=nextcord.ButtonStyle.blurple,
            row=1,
            disabled=(not enabled)
        )
        self.topup_for_friend_button = nextcord.ui.Button(
            label='[🎁] เติมให้เพื่อน',
            custom_id='topup_for_friend',
            style=nextcord.ButtonStyle.red,
            row=1,
            disabled=(not enabled)
        )
        self.balance_button = nextcord.ui.Button(
            label='[💰] เช็ค Cash',
            custom_id='balance_new',
            style=nextcord.ButtonStyle.green,
            row=1,
            disabled=(not enabled)
        )
        self.open_topup_button.callback = self.open_topup
        self.topup_for_friend_button.callback = self.topup_for_friend
        self.balance_button.callback = self.balance
        self.add_item(self.open_topup_button)
        self.add_item(self.topup_for_friend_button)
        self.add_item(self.balance_button)

    async def open_topup(self, interaction: nextcord.Interaction):
        if not TOPUP_ENABLED:
            return await interaction.response.send_message("ขณะนี้ปิดการเติมเงินชั่วคราว กรุณาลองใหม่ภายหลัง", ephemeral=True)
        player_data = await check_whitelist(interaction)
        if not player_data:
            return
        player_name = player_data["playerName"]
        mode = str(getattr(config, "TOPUP_UI_TYPE", "01")).strip()
        if mode == "02":
            await interaction.response.send_message(
                embed=nextcord.Embed(
                    title="เลือกรูปแบบการเติมเงิน",
                    description="กดปุ่มด้านล่างเพื่อเลือกวิธีเติม",
                    color=nextcord.Color.gold()
                ),
                ephemeral=True,
                view=TopupButtonsView(player_name=player_name)
            )
        else:
            class MethodSelect(nextcord.ui.StringSelect):
                def __init__(self):
                    options = [
                        nextcord.SelectOption(label="TrueMoney Wallet (ซองอั่งเปา)", value="wallet", emoji="🧧"),
                        nextcord.SelectOption(label="ธนาคาร / PromptPay", value="bank", emoji="🏦"),
                    ]
                    super().__init__(placeholder="เลือกช่องทางการเติมเงิน", min_values=1, max_values=1, options=options, custom_id="topup_method_select")
                async def callback(self_inner, interaction_inner: nextcord.Interaction):
                    if not TOPUP_ENABLED:
                        return await interaction_inner.response.send_message("ปิดการเติมเงินชั่วคราว", ephemeral=True)
                    pdata = await check_whitelist(interaction_inner)
                    if not pdata:
                        return
                    if self_inner.values[0] == "wallet":
                        await interaction_inner.response.send_modal(WalletModal(whitelisted_name=player_name))
                    else:
                        if is_bank_maintenance():
                            return await interaction_inner.response.send_message(
                                embed=nextcord.Embed(
                                    title="ธนาคารปิดปรับปรุงระบบ",
                                    description=BANK_MAINTENANCE_MESSAGE,
                                    color=nextcord.Color.red()
                                ).set_footer(text="ใช้ TrueMoney Wallet แทนได้เลย!"),
                                ephemeral=True
                            )
                        await interaction_inner.response.send_modal(BankModal(whitelisted_name=player_name))
            select_view = nextcord.ui.View(timeout=120)
            select_view.add_item(MethodSelect())
            await interaction.response.send_message(
                embed=nextcord.Embed(
                    title="เลือกช่องทางการเติมเงิน",
                    description="กรุณาเลือกด้านล่างว่าจะเติมผ่านอะไร",
                    color=nextcord.Color.gold()
                ),
                ephemeral=True,
                view=select_view
            )

    async def topup_for_friend(self, interaction: nextcord.Interaction):
        if not TOPUP_ENABLED:
            return await interaction.response.send_message("ขณะนี้ปิดการเติมเงินชั่วคราว กรุณาลองใหม่ภายหลัง", ephemeral=True)
        player_data = await check_whitelist(interaction)
        if not player_data:
            return
        class FriendRecipientModal(nextcord.ui.Modal):
            def __init__(self):
                super().__init__(title="เติมให้เพื่อน • ระบุชื่อ", timeout=None, custom_id="friend_recipient_modal")
                self.name = TextInput(
                    label="ชื่อตัวละครผู้รับ",
                    placeholder="เช่น Training_Park ",
                    style=nextcord.TextInputStyle.short,
                    required=True,
                    min_length=3, max_length=24
                )
                self.add_item(self.name)
            async def callback(self, itx: nextcord.Interaction):
                if not TOPUP_ENABLED:
                    return await itx.response.send_message("ปิดการเติมเงินชั่วคราว", ephemeral=True)
                friend_name = str(self.name.value).strip()
                try:
                    player_found = database.player_exists(friend_name)
                except mysql.connector.Error as err:
                    return await itx.response.send_message(
                        embed=nextcord.Embed(description=f"ตรวจสอบชื่อผู้เล่นล้มเหลว: {err}", color=nextcord.Color.red()),
                        ephemeral=True
                    )
                if not player_found:
                    return await itx.response.send_message(
                        embed=nextcord.Embed(
                            description=f"ไม่พบผู้เล่นชื่อ `{friend_name}` ในระบบ\nกรุณาตรวจสอบอีกครั้ง",
                            color=nextcord.Color.orange()
                        ),
                        ephemeral=True
                    )
                mode = str(getattr(config, "TOPUP_UI_TYPE", "01")).strip()
                if mode == "02":
                    await itx.response.send_message(
                        embed=nextcord.Embed(
                            title="เลือกรูปแบบการเติมเงิน (ให้เพื่อน)",
                            description=f"กำลังจะเติมให้ **{friend_name}**\nเลือกวิธีด้านล่าง",
                            color=nextcord.Color.gold()
                        ),
                        ephemeral=True,
                        view=TopupButtonsView(player_name=friend_name)
                    )
                else:
                    await itx.response.send_message(
                        embed=nextcord.Embed(
                            title="เลือกช่องทางการเติมเงิน (ให้เพื่อน)",
                            description=f"กำลังจะเติมให้ **{friend_name}**\nเลือกวิธีด้านล่าง",
                            color=nextcord.Color.gold()
                        ),
                        ephemeral=True,
                        view=FriendSelectView(player_name=friend_name)
                    )
        await interaction.response.send_modal(FriendRecipientModal())

    async def balance(self, interaction: nextcord.Interaction):
        if not TOPUP_ENABLED:
            return await interaction.response.send_message("ขณะนี้ปิดการเติมเงินชั่วคราว กรุณาลองใหม่ภายหลัง", ephemeral=True)
        player_data = await check_whitelist(interaction)
        if not player_data:
            return
        player_name = player_data["playerName"]
        wallet_balance = int(player_data.get("playerWallet", 0))
        desc = f"`👤` ชื่อตัวละคร: `{player_name}`\n`💰` Cash คงเหลือ: **`{wallet_balance:,}`**"
        embed = nextcord.Embed(title="`🔍` ยอดเงินคงเหลือ", description=desc, color=nextcord.Color.green())
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ========= Utilities: อัปเดต View ของโพสต์ =========
async def update_topup_message_view(ctx: commands.Context, enabled: bool, target_msg=None, message_id: str = None):
    if target_msg is None and message_id is not None:
        try:
            target_msg = await ctx.channel.fetch_message(int(message_id))
        except Exception:
            target_msg = None
    if target_msg is None and ctx.message.reference and ctx.message.reference.message_id:
        try:
            target_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        except Exception:
            target_msg = None
    if target_msg is None:
        return False
    try:
        await target_msg.edit(view=TopupEntry(enabled=enabled))
        return True
    except Exception:
        return False

# ========= Events / Commands =========
@bot.event
async def on_ready():
    os.system('cls' if os.name == 'nt' else 'clear')
    print('\033[31m|=============================================================|\033[37m')
    print('\033[32m| \033[33mBOT TOPUP SAMP Start...')
    print(f'\033[32m| \033[33mLogged in as \033[37m{bot.user}')
    print('\033[32m| \033[33mAPIs')
    print('\033[32m| \033[37mhttps://www.tmweasy.com/apiwallet.php ← ซองอั่งเปา')
    print('\033[32m| \033[37mhttps://tmwallet.thaighost.net/apipp.php ← QR Code')
    print('\033[31m|=============================================================|\033[37m')
    bot.add_view(TopupEntry(enabled=TOPUP_ENABLED))

@bot.event
async def on_command_error(ctx: commands.Context, error):
    if isinstance(error, commands.CommandNotFound):
        return
    raise error

@bot.command(name="setuptopup")
async def setuptopup(ctx: commands.Context):
    if hasattr(config, "OWNERS") and ctx.author.id in config.OWNERS:
        embed = build_topup_embed()
        await ctx.send(embed=embed, view=TopupEntry(enabled=TOPUP_ENABLED))
        try:
            await ctx.message.add_reaction("✅")
        except Exception:
            pass
    else:
        await ctx.send(embed=nextcord.Embed(
            title="🐃 มึงไม่มีสิทธิ์ใช้ไอโง่ 🐃",
            color=nextcord.Color.orange()
        ))

@bot.command(name="refpup", usage="!refpup <message_id|-> [description ใหม่]")
async def refpup(ctx: commands.Context, message_id: str = None, *, new_desc: str = None):
    if not (hasattr(config, "OWNERS") and ctx.author.id in config.OWNERS):
        return await ctx.send(embed=nextcord.Embed(
            title="🐃 มึงไม่มีสิทธิ์ใช้ไอโง่ 🐃",
            color=nextcord.Color.orange()
        ))
    target_msg = None
    if message_id == "-":
        if ctx.message.reference and ctx.message.reference.message_id:
            try:
                target_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            except nextcord.NotFound:
                return await ctx.send("หา message จากการ reply ไม่เจอ", delete_after=6)
        else:
            return await ctx.send("โปรด reply ไปที่ข้อความบอทก่อน แล้วพิมพ์ `!refpup -`", delete_after=8)
    elif message_id is None:
        return await ctx.send(
            "วิธีใช้:\n"
            "• `!refpup <message_id>` (รีเฟรชเป็นเทมเพลต)\n"
            "• `!refpup <message_id> <description ใหม่>`\n"
            "• หรือ reply ไปที่ข้อความบอทแล้วพิมพ์ `!refpup - [description ใหม่]`",
            delete_after=12
        )
    if target_msg is None:
        try:
            target_msg = await ctx.channel.fetch_message(int(message_id))
        except ValueError:
            return await ctx.send("`message_id` ต้องเป็นตัวเลข หรือใช้ `-` ถ้า reply", delete_after=8)
        except nextcord.NotFound:
            return await ctx.send("ไม่พบข้อความตาม ID นี้ในห้องนี้", delete_after=6)
        except nextcord.Forbidden:
            return await ctx.send("บอทไม่มีสิทธิ์ดึงข้อความนี้", delete_after=6)
        except Exception as e:
            return await ctx.send(f"ดึงข้อความล้มเหลว: {e}", delete_after=8)
    if target_msg.author.id != bot.user.id:
        return await ctx.send("ข้อความนี้ไม่ใช่ของบอท แก้ไขไม่ได้", delete_after=6)
    try:
        new_embed = build_topup_embed(description_override=new_desc)
        await target_msg.edit(content=None, embed=new_embed, view=TopupEntry(enabled=TOPUP_ENABLED))
        await ctx.message.add_reaction("✅")
        await ctx.send(f"รีเฟรชโพสต์สำเร็จ (ID: `{target_msg.id}`)", delete_after=6)
    except nextcord.Forbidden:
        await ctx.send("บอทไม่มีสิทธิ์แก้ไขข้อความนี้", delete_after=6)
    except Exception as e:
        await ctx.send(f"แก้ไขไม่สำเร็จ: {e}", delete_after=8)

@bot.command(name="topupoff", usage="!topupoff [message_id|reply ไปที่โพสต์]")
async def topupoff(ctx: commands.Context, message_id: str = None):
    global TOPUP_ENABLED
    if not (hasattr(config, "OWNERS") and ctx.author.id in config.OWNERS):
        return await ctx.send(embed=nextcord.Embed(
            title="🐃 มึงไม่มีสิทธิ์ใช้ไอโง่ 🐃",
            color=nextcord.Color.orange()
        ))
    TOPUP_ENABLED = False
    updated = await update_topup_message_view(ctx, enabled=False, message_id=message_id)
    if updated:
        await ctx.send("ปิดการเติมเงินแล้ว และอัปเดตปุ่มบนโพสต์ให้กดไม่ได้ ✅", delete_after=8)
    else:
        await ctx.send("ปิดการเติมเงินแล้ว (ถ้าต้องการให้ปุ่มบนโพสต์กลายเป็นเทา ให้ reply โพสต์นั้นหรือใส่ message_id แล้วสั่งอีกครั้ง) ✅", delete_after=12)

@bot.command(name="topupon", usage="!topupon [message_id|reply ไปที่โพสต์]")
async def topupon(ctx: commands.Context, message_id: str = None):
    global TOPUP_ENABLED
    if not (hasattr(config, "OWNERS") and ctx.author.id in config.OWNERS):
        return await ctx.send(embed=nextcord.Embed(
            title="🐃 มึงไม่มีสิทธิ์ใช้ไอโง่ 🐃",
            color=nextcord.Color.orange()
        ))
    TOPUP_ENABLED = True
    updated = await update_topup_message_view(ctx, enabled=True, message_id=message_id)
    if updated:
        await ctx.send("เปิดการเติมเงินแล้ว และอัปเดตปุ่มบนโพสต์ให้กดได้ ✅", delete_after=8)
    else:
        await ctx.send("เปิดการเติมเงินแล้ว (ถ้าต้องการให้ปุ่มบนโพสต์กลับมากดได้ ให้ reply โพสต์นั้นหรือใส่ message_id แล้วสั่งอีกครั้ง) ✅", delete_after=12)

if __name__ == "__main__":
    try:
        dashboard_url = dashboard.start_dashboard(
            getattr(config, "DASHBOARD_PORT", 8765)
        )
        print(f"Local top-up dashboard: {dashboard_url}")
    except OSError as error:
        print(f"Local dashboard could not start: {error}")

    bot.run(config.token)
