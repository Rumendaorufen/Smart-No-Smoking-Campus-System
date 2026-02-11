package org.example.webback.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("alarms") // 对应数据库表名 alarms
public class Alarm {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Integer cameraId; // 对应 camera_id

    private String type; // 默认 'SMOKING'

    private Double confidence; // 对应 Float

    private String videoUrl;

    private String roiUrl;

    private Integer auditStatus; // 0:待审核, 1:已确认, 2:误报, 9:忽略

    private Integer auditorId; // 审核人ID (外键)

    private LocalDateTime auditTime;

    private String auditRemark;

    private LocalDateTime createdAt;

    // ==========================================
    // 👇以此下是数据库表中不存在的字段 (关联查询用)
    // ==========================================

    @TableField(exist = false) // 告诉 MP 这不是数据库字段
    private String deviceName;

    @TableField(exist = false)
    private String auditorName;

    @TableField(exist = false)
    private String statusText; // 用于前端展示 "待审核" 等
}