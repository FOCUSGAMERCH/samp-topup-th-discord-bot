#include <a_samp>
#include <a_mysql>
#include <YSI_Coding\y_hooks>


//-------------------------------
// Global query variable
//-------------------------------
new g_query[512];

// ตัวแปรชั่วคราวสำหรับเก็บข้อมูลการเติมเงินขณะรอการยืนยัน
new g_TempTopupAmount[MAX_PLAYERS];
new g_TempTransactionID[MAX_PLAYERS];

// Dialog Definition
#define TopupWeb 1001 // กำหนด ID ของ Dialog

//===============================
// โปรโตไทป์
//===============================
forward ProcessTopupTransactions();
forward OnProcessTopupTransactions();

//===============================
// Helper: อัปเดตข้อมูลผู้เล่นลง DB
// (คุณมีฟังก์ชันนี้อยู่แล้ว ใช้อันเดิมได้)
//===============================


//===============================
// Helper: แก้ยอดติดลบ (ขณะ "ออนไลน์")
//===============================
stock FixNegativeWalletOnline(playerid)
{
    if (playerData[playerid][pWallet] < 0)
    {
        new fixAbs = -playerData[playerid][pWallet];
        playerData[playerid][pWallet] = 0;
        UpdateplayerData(playerid);

        // (ทางเลือก) log ไป Discord
        #if defined DCC_SendChannelMessage
        new pname[MAX_PLAYER_NAME], s[256];
        GetPlayerName(playerid, pname, sizeof(pname));
        format(s, sizeof(s), "[WALLET-FIX] : ผู้เล่น %s มียอดติดลบ %d -> ปรับเป็น 0 (ขณะออนไลน์)", pname, fixAbs);
        DCC_SendChannelMessage(DCC_FindChannelById("1396529170267373668"), s);
        #endif
    }
    return 1;
}

//==============================================================================
// Timer สำหรับตรวจสอบการเติมเงินจากเว็บไซต์
//==============================================================================
public ProcessTopupTransactions()
{
    // เลือกรายการที่ยังไม่ processed (0) ทีละ 10 เรคคอร์ด
    mysql_format(g_SQL, g_query, sizeof(g_query),
        "SELECT id, playerName, amount, payment_method, ref_code \
         FROM topup_transactions WHERE processed = 0 LIMIT 10");
    mysql_tquery(g_SQL, g_query, "OnProcessTopupTransactions", "");
    return 1;
}

//==============================================================================
// ประมวลผลการเติมเงิน
//==============================================================================
public OnProcessTopupTransactions()
{
    new rows = cache_num_rows();
    if (!rows) return 1;

    new playerName[MAX_PLAYER_NAME], amount, transaction_id;
    new payment_method[32], ref_code[256];
    new string[256]; // สำหรับ Discord log

    for (new i = 0; i < rows; i++)
    {
        cache_get_value_name_int(i, "id", transaction_id);
        cache_get_value_name_int(i, "amount", amount);
        cache_get_value_name(i, "playerName", playerName, sizeof(playerName));
        cache_get_value_name(i, "payment_method", payment_method, sizeof(payment_method));
        cache_get_value_name(i, "ref_code", ref_code, sizeof(ref_code));

        if (amount <= 0)
        {
            // ข้ามรายการไม่ปกติ
            mysql_format(g_SQL, g_query, sizeof(g_query), "UPDATE topup_transactions SET processed = 1 WHERE id = %d", transaction_id);
            mysql_tquery(g_SQL, g_query, "", "");
            continue;
        }

        new playerid = FindPlayerByName(playerName);

        if (playerid != INVALID_PLAYER_ID) // --- ผู้เล่นออนไลน์ ---
        {
            // mark กำลังประมวลผล
            mysql_format(g_SQL, g_query, sizeof(g_query), "UPDATE topup_transactions SET processed = 2 WHERE id = %d", transaction_id);
            mysql_tquery(g_SQL, g_query, "", "");

            g_TempTopupAmount[playerid] = amount;
            g_TempTransactionID[playerid] = transaction_id;

            // แก้ยอดติดลบให้เป็น 0 ก่อน แล้วค่อยบวกจำนวนที่เติม
            FixNegativeWalletOnline(playerid);

            playerData[playerid][pWallet] += amount;
            UpdateplayerData(playerid);

            // ปิดรายการ
            mysql_format(g_SQL, g_query, sizeof(g_query), "UPDATE topup_transactions SET processed = 1 WHERE id = %d", transaction_id);
            mysql_tquery(g_SQL, g_query, "", "");

            // แจ้งข้อความในเกม
            new message[128];
            format(message, sizeof(message), "{FFD700}[Topup]: {FFFFFF}คุณได้รับ %d Cash เรียบร้อยแล้ว ขอบคุณที่สนับสนุนครับ", amount);
            SendClientMessage(playerid, -1, message);

            // ช่องทางภาษาไทย
            new methodText[32];
            if (!strcmp(payment_method, "promptpay", true)) {
                format(methodText, sizeof(methodText), "พร้อมเพย์");
            } else {
                format(methodText, sizeof(methodText), "อั่งเปาวอลเล็ท");
            }

            // แจ้งเตือนไปยัง Discord สำหรับผู้เล่นออนไลน์
            #if defined DCC_SendChannelMessage
            format(string, sizeof(string),
                "[TOPUP-LOG] : ผู้เล่น %s เติมเงิน %d Cash ผ่าน %s (เลขอ้างอิง: %s)\nตอนเวลา: %s",
                playerName, amount, methodText, ref_code, ReturnDateTime(0));
            DCC_SendChannelMessage(DCC_FindChannelById("1396529170267373668"), string);
            #endif

            // กล่องแจ้งยืนยัน
            new dialogMsg[300];
            format(dialogMsg, sizeof(dialogMsg),
                "{33AAFF}ระบบเติมเงิน\n\n" \
                "{FFFFFF}คุณได้ทำรายการเติมเงินสำเร็จ:\n" \
                "จำนวน: {00FF00}%d Cash\n" \
                "ช่องทาง: {FFFF00}%s\n" \
                "เลขอ้างอิง: {CCCCCC}%s\n\n" \
                "{FFFFFF}กรุณากด \"ยืนยัน\" เพื่อปิด",
                amount, methodText, ref_code);

            Dialog_Show(playerid, TopupWeb, DIALOG_STYLE_MSGBOX, "Server Training Park", dialogMsg, "ยืนยัน", "");
        }
        else // --- ผู้เล่นออฟไลน์ ---
        {
            // สำคัญ: เคลียร์ติดลบใน DB ก่อน แล้วจึงบวกเงินที่เติม
            // GREATEST(playerWallet, 0) ทำให้ค่ายอดต่ำสุดเป็น 0
            mysql_format(g_SQL, g_query, sizeof(g_query),
                "UPDATE players \
                 SET playerWallet = GREATEST(playerWallet, 0) + %d \
                 WHERE playerName = '%e'",
                amount, playerName);
            mysql_tquery(g_SQL, g_query, "", "");

            // ปิดรายการ
            mysql_format(g_SQL, g_query, sizeof(g_query), "UPDATE topup_transactions SET processed = 1 WHERE id = %d", transaction_id);
            mysql_tquery(g_SQL, g_query, "", "");

            // แจ้งเตือนไปยัง Discord สำหรับผู้เล่นออฟไลน์
            #if defined DCC_SendChannelMessage
            format(string, sizeof(string),
                "[TOPUP-LOG] : ผู้เล่น %s (ออฟไลน์) เติมเงิน %d Cash ผ่าน %s (เลขอ้างอิง: %s)\nตอนเวลา: %s",
                playerName, amount, payment_method, ref_code, ReturnDateTime(0));
            DCC_SendChannelMessage(DCC_FindChannelById("1396529170267373668"), string);
            #endif
        }

        printf("[TopUp] Processed transaction ID %d for player %s, amount %d.", transaction_id, playerName, amount);
    }
    return 1;
}

//==============================================================================
// Dialog Handler สำหรับยืนยันการเติมเงิน (แสดงผลเฉยๆ)
//==============================================================================
Dialog:TopupWeb(playerid, response, listitem, inputtext[])
{
    if (response)
    {
        new amount = g_TempTopupAmount[playerid];
        new transaction_id = g_TempTransactionID[playerid];

        if (amount > 0 && transaction_id > 0)
        {
            // เคยทำไปแล้วใน OnProcessTopupTransactions (ออนไลน์)
            PlayerPlaySound(playerid, 1057, 0.0, 0.0, 0.0);
        }
        g_TempTopupAmount[playerid] = 0;
        g_TempTransactionID[playerid] = 0;
    }
    return 1;
}

//==============================================================================
// ฟังก์ชันเสริม
//==============================================================================
stock FindPlayerByName(const name[])
{
    foreach (new i : Player)
    {
        if (IsPlayerConnected(i))
        {
            new pName[MAX_PLAYER_NAME];
            GetPlayerName(i, pName, sizeof(pName));
            if (!strcmp(pName, name, false))
            {
                return i;
            }
        }
    }
    return INVALID_PLAYER_ID;
}

//==============================================================================
// Hooks
//==============================================================================
hook OnGameModeInit()
{
    SetTimer("ProcessTopupTransactions", 5000, true);
    return 1;
}

hook OnPlayerConnect(playerid)
{
    g_TempTopupAmount[playerid] = 0;
    g_TempTransactionID[playerid] = 0;

    // ปลอดภัยไว้ก่อน: ถ้าโหลดค่า pWallet มาแล้วติดลบ ให้เคลียร์เป็น 0
    if (playerData[playerid][pWallet] < 0)
    {
        playerData[playerid][pWallet] = 0;
        UpdateplayerData(playerid);
    }
    return 1;
}
