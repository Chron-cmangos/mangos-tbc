CREATE TABLE IF NOT EXISTS `mantech_character_grants` (
  `guid` int unsigned NOT NULL,
  `grant_key` varchar(64) CHARACTER SET ascii COLLATE ascii_general_ci NOT NULL,
  `mail_id` int unsigned NOT NULL,
  `granted_at` bigint unsigned NOT NULL,
  PRIMARY KEY (`guid`,`grant_key`),
  KEY `idx_mail_id` (`mail_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 ROW_FORMAT=DYNAMIC COMMENT='One-time ManTech character grants';
