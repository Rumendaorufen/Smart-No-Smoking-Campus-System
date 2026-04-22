package org.example.webback.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.util.Date;

@Data
@TableName("ai_conversations")
public class AiConversation {

    // 使用前端传入或后端生成的 UUID 作为主键，类型为 INPUT
    @TableId(type = IdType.INPUT)
    private String id;

    // 当前登录用户的 ID (假设你系统里的 userId 是 Long 类型)
    private Long userId;

    // 对话标题，默认为“新对话”
    private String title;

    // 逻辑删除标识 (0: 未删除, 1: 已删除)
    // MyBatis-Plus 会在执行 deleteById 时自动将其转为 UPDATE is_deleted = 1
    @TableLogic
    private Integer isDeleted;

    // 创建时间 (建议在数据库层面设置默认值 CURRENT_TIMESTAMP，或者配置 MP 自动填充)
    private Date createdAt;

    // 更新时间
    private Date updatedAt;
}