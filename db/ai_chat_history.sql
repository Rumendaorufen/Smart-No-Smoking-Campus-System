CREATE TABLE `ai_chat_history` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `session_id` VARCHAR(128) NOT NULL COMMENT '对应 conversation_id',
    `message` JSON NOT NULL COMMENT '存储消息角色(role)和内容(content)的JSON',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_session` (`session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;