package org.example.webback.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("devices") // 对应数据库表名 devices
public class Device {

    @TableId(type = IdType.AUTO)
    private Integer id; // Python里定义的是 Integer

    private String name;

    private String rtspUrl;

    private String areaConfig; // 对应 Text 类型

    private Integer status; // 1:在线, 0:离线

    private Boolean enabled; // 对应 Python 的 Boolean (MySQL中通常是 tinyint)

    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;
}