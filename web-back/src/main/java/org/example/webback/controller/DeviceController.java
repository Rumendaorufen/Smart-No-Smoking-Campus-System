package org.example.webback.controller;

import org.example.webback.common.Result;
import org.example.webback.entity.Device;
import org.example.webback.service.DeviceService;
import org.example.webback.service.UserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@RestController
public class DeviceController {

    @Autowired
    private DeviceService deviceService;
    @Autowired
    private UserService userService;

    // ==================== 1. 供 Python AI 引擎调用的【内部】接口 (无Token放行) ====================

    /**
     * 🚀 新增：供 Python 端同步设备列表
     * 对应 WebMvcConfig 中已放行的 /api/internal/** 路径
     * Python 请求地址改为：http://localhost:8080/api/internal/devices
     */
    @GetMapping("/api/internal/devices")
    public Result listAllDevicesInternal() {
        return Result.success(deviceService.listAllDevices());
    }

    // ==================== 2. 供前端调用的【监控】接口 (需要Token拦截) ====================

    @GetMapping("/api/monitor/devices")
    public Result list() {
        return Result.success(deviceService.listAllDevices());
    }

    /**
     * 轻量级状态轮询接口 (只返回 ID, Status, Enabled)
     */
    @GetMapping("/api/monitor/devices/status-only")
    public Result listStatus() {
        List<Device> list = deviceService.listAllDevices();
        List<Map<String, Object>> statusMap = list.stream().map(d -> {
            Map<String, Object> m = new java.util.HashMap<>();
            m.put("id", d.getId());
            m.put("status", d.getStatus());
            m.put("enabled", d.getEnabled());
            return m;
        }).collect(Collectors.toList());
        return Result.success(statusMap);
    }

    /**
     * 添加设备 (受 JwtInterceptor 保护)
     */
    @PostMapping("/api/monitor/devices")
    public Result add(@RequestBody Device device,
                      @RequestAttribute(value = "uid", required = false) Object uidObj) {
        if (uidObj == null) {
            return Result.error(401, "登录凭证缺失，请重新登录");
        }
        Long uid = Long.valueOf(uidObj.toString());
        if (!userService.isAdmin(uid)) {
            return Result.error(403, "权限不足：只有管理员可添加设备");
        }
        try {
            deviceService.addDevice(device);
            return Result.success(Map.of("id", device.getId()));
        } catch (RuntimeException e) {
            return Result.error(400, e.getMessage());
        }
    }

    /**
     * 更新设备
     */
    @PutMapping("/api/monitor/devices/{id}")
    public Result update(@PathVariable Integer id, @RequestBody Device form, @RequestAttribute("uid") Long uid) {
        if (!userService.isAdmin(uid)) return Result.error(403, "无权操作");
        try {
            deviceService.updateDevice(id, form);
            return Result.success("更新成功");
        } catch (RuntimeException e) {
            return Result.error(500, e.getMessage());
        }
    }

    /**
     * 删除设备
     */
    @DeleteMapping("/api/monitor/devices/{id}")
    public Result delete(@PathVariable Integer id, @RequestAttribute("uid") Long uid) {
        if (!userService.isAdmin(uid)) return Result.error(403, "无权操作");
        deviceService.removeById(id);
        return Result.success("删除成功");
    }

    /**
     * 供 Python AI 后端回传识别状态的接口
     */
    @PostMapping("/api/monitor/devices/sync-status")
    public Result syncStatus(@RequestBody Map<String, Object> payload) {
        try {
            Integer id = (Integer) payload.get("id");
            Integer status = (Integer) payload.get("status");
            if (id != null && status != null) {
                deviceService.syncDeviceStatus(id, status);
                return Result.success("状态同步完成");
            }
            return Result.error(400, "参数错误");
        } catch (Exception e) {
            return Result.error(500, "同步失败: " + e.getMessage());
        }
    }

    /**
     * 获取单个设备状态
     */
    @GetMapping("/api/monitor/stream/status/{id}")
    public Result getStatus(@PathVariable Integer id) {
        int status = deviceService.getDeviceStatus(id);
        return Result.success(Map.of("status", status));
    }
}