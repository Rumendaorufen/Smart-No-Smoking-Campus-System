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

    // 获取设备列表
    @GetMapping("/devices")
    public Result list() {
        // Service 封装了查询逻辑 (例如倒序排列)
        List<Device> devices = deviceService.listAllDevices();
        return Result.success(devices);
    }

    // 添加设备
    @PostMapping("/devices")
    public Result add(@RequestBody Device device, @RequestAttribute("uid") Long uid) {
        if (!userService.isAdmin(uid)) return Result.error(403, "无权操作");

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

    // 检测在线状态 (核心业务逻辑移至 Service)
    @GetMapping("/stream/status/{id}")
    public Result checkStatus(@PathVariable Integer id) {
        try {
            int status = deviceService.checkAndUpdateStatus(id);
            return Result.success(Map.of("status", status));
        } catch (RuntimeException e) {
            return Result.error(404, e.getMessage());
        }
    }
}