package org.example.webback.controller;

import org.example.webback.common.Result;
import org.example.webback.entity.Device;
import org.example.webback.service.DeviceService;
import org.example.webback.service.UserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/monitor")
public class DeviceController {

    @Autowired
    private DeviceService deviceService;
    @Autowired
    private UserService userService;

    // 1. 获取设备列表 (保持不变)
    @GetMapping("/devices")
    public Result list() {
        return Result.success(deviceService.listAllDevices());
    }

    // 2. 添加设备 (注意：拦截器必须放行此接口，或者在拦截器里对这个特定 URL 做排除)
    @PostMapping("/devices")
    public Result add(@RequestBody Device device, @RequestAttribute(value = "uid", required = false) Long uid) {
        if (uid == null || !userService.isAdmin(uid)) return Result.error(403, "无权操作");
        try {
            deviceService.addDevice(device);
            return Result.success(Map.of("id", device.getId()));
        } catch (RuntimeException e) {
            return Result.error(400, e.getMessage());
        }
    }




    // 更新设备
    @PutMapping("/devices/{id}")
    public Result update(@PathVariable Integer id, @RequestBody Device form, @RequestAttribute("uid") Long uid) {
        if (!userService.isAdmin(uid)) return Result.error(403, "无权操作");

        try {
            deviceService.updateDevice(id, form);
            return Result.success("更新成功");
        } catch (RuntimeException e) {
            return Result.error(500, e.getMessage());
        }
    }

    // 删除设备
    @DeleteMapping("/devices/{id}")
    public Result delete(@PathVariable Integer id, @RequestAttribute("uid") Long uid) {
        if (!userService.isAdmin(uid)) return Result.error(403, "无权操作");

        deviceService.removeById(id);
        return Result.success("删除成功");
    }

//    // 检测在线状态 (核心业务逻辑移至 Service)
//    @GetMapping("/stream/status/{id}")
//    public Result checkStatus(@PathVariable Integer id) {
//        try {
//            int status = deviceService.checkAndUpdateStatus(id);
//            return Result.success(Map.of("status", status));
//        } catch (RuntimeException e) {
//            return Result.error(404, e.getMessage());
//        }
//    }

    // 🚀 新增：供 Python AI 后端调用的同步接口
// Python 请求地址：http://localhost:8080/api/monitor/devices/sync-status
    @PostMapping("/devices/sync-status")
    public Result syncStatus(@RequestBody Map<String, Object> payload) {
        try {
            // 解析 Python 发来的 json: {"id": 41, "status": 1}
            Integer id = (Integer) payload.get("id");
            Integer status = (Integer) payload.get("status");

            if (id != null && status != null) {
                deviceService.syncDeviceStatus(id, status);
                return Result.success("状态同步成功");
            }
            return Result.error(400, "参数错误");
        } catch (Exception e) {
            return Result.error(500, "同步失败: " + e.getMessage());
        }
    }

    // 🚀 优化：修改原来的检测状态接口
// 将主动探测改为“被动返回”，这样前端轮询时速度极快，且不会因为 Socket 超时卡顿
    @GetMapping("/stream/status/{id}")
    public Result getStatus(@PathVariable Integer id) {
        Device device = deviceService.getById(id);
        if (device == null) return Result.error(404, "设备不存在");

        // 直接返回数据库里的状态（这个状态已被 Python 实时同步过）
        return Result.success(Map.of("status", device.getStatus()));
    }
}