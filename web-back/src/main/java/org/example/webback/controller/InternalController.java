package org.example.webback.controller;

import cn.hutool.core.bean.BeanUtil;
import org.example.webback.common.Result;
import org.example.webback.dto.AlarmReportDTO;
import org.example.webback.entity.Alarm;
import org.example.webback.entity.Device;
import org.example.webback.service.AlarmService;
import org.example.webback.service.DeviceService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;

@RestController
@RequestMapping("/api/internal")
public class InternalController {

    @Autowired
    private AlarmService alarmService;

    @Autowired
    private DeviceService deviceService;

    @Autowired
    private SimpMessagingTemplate messagingTemplate; // 📡 WebSocket 发送工具

    @PostMapping("/alarm/report")
    public Result report(@RequestBody AlarmReportDTO dto) {
        System.out.println("📥 收到 Python 报警: " + dto);

        // 1. 转换数据 (DTO -> Entity)
        Alarm alarm = new Alarm();
        // 使用 Hutool 快速拷贝属性 (也可以手动 set)
        BeanUtil.copyProperties(dto, alarm);

        // 补全默认字段
        alarm.setAuditStatus(0); // 待审核
        alarm.setCreatedAt(LocalDateTime.now());

        // 2. 存入数据库
        alarmService.save(alarm);

        // 3. 准备推送给前端的数据
        // 为了让弹窗显示设备名，我们需要查一下 Device 表
        Device device = deviceService.getById(dto.getCameraId());
        if (device != null) {
            alarm.setDeviceName(device.getName());
        } else {
            alarm.setDeviceName("未知设备 (" + dto.getCameraId() + ")");
        }

        // 设置状态文本，方便前端展示
        alarm.setStatusText("待审核");

        // 4. 📡 WebSocket 广播！
        // 前端订阅地址: /topic/alarm
        messagingTemplate.convertAndSend("/topic/alarm", alarm);

        return Result.success();
    }
}