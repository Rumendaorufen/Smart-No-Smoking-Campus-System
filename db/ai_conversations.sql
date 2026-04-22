-- 1. 会话主表：用于左侧列表显示
CREATE TABLE `ai_conversations` (
    `id` VARCHAR(64) PRIMARY KEY COMMENT '会话全局唯一ID',
    `user_id` INT NOT NULL COMMENT '所属用户',
    `title` VARCHAR(255) DEFAULT '新对话' COMMENT '会话标题（AI可随后根据内容更新）',
    `is_deleted` TINYINT DEFAULT 0 COMMENT '逻辑删除标识',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_user_list` (`user_id`, `is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. 消息明细表：修改原有的 ai_chat_history 逻辑
-- 现在的 session_id 存储的是 conversation_id