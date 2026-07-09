package org.example.webback.controller;

import org.example.webback.common.Result;
import org.example.webback.dto.AlarmReportDTO;
import org.example.webback.entity.Alarm;
import org.example.webback.entity.Device;
import org.example.webback.service.AlarmService;
import org.example.webback.service.DeviceService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.web.bind.annotation.*;

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

        // 1. 通过 saveInternalAlarm 保存并触发飞书通知
        Alarm alarm = alarmService.saveInternalAlarm(
                dto.getCameraId(),
                dto.getType(),
                dto.getConfidence() != null ? dto.getConfidence().doubleValue() : 0.0,
                dto.getSnapshotUrl(),
                dto.getVideoUrl()
        );

        // 2. 准备推送给前端的数据
        Device device = deviceService.getById(dto.getCameraId());
        if (device != null) {
            alarm.setDeviceName(device.getName());
        } else {
            alarm.setDeviceName("未知设备 (" + dto.getCameraId() + ")");
        }
        alarm.setStatusText("待审核");

        // 3. 📡 WebSocket 广播！
        messagingTemplate.convertAndSend("/topic/alarm", alarm);

        return Result.success();
    }
}