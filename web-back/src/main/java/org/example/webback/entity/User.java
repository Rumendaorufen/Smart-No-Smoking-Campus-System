package org.example.webback.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("users") // 对应数据库表名 users
public class User {

    @TableId(type = IdType.AUTO) // 主键自增
    private Long id;

    private String username;

    // Python里叫 password_hash，但数据库列名是 password
    // 在这里直接用 password 即可映射
    @TableField("password")
    private String password;

    private String role;

    private Integer status; // 1:正常, 0:禁用

    private String lastLoginIp;

    private LocalDateTime lastLoginTime;

    // 对应 created_at
    private LocalDateTime createdAt;
}