-- SA-MP Discord top-up transaction table
-- Select the same database used by the bot and SA-MP server before running this file.

CREATE TABLE IF NOT EXISTS `topup_transactions` (
    `id` INT(11) NOT NULL AUTO_INCREMENT,
    `playerName` VARCHAR(255) COLLATE tis620_thai_ci NOT NULL,
    `amount` DECIMAL(10,2) NOT NULL,
    `payment_method` ENUM('promptpay', 'truemoney') COLLATE tis620_thai_ci NOT NULL,
    `ref_code` VARCHAR(255) COLLATE tis620_thai_ci DEFAULT NULL,
    `processed` TINYINT(1) NOT NULL DEFAULT 1,
    `transaction_date` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=tis620 COLLATE=tis620_thai_ci;
