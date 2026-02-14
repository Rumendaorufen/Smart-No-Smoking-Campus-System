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
@RequestMapping("/api/monitor")
public class DeviceController {

    @Autowired
    private DeviceService deviceService;
    @Autowired
    private UserService userService;

    /**
     * 1. 获取全量设备列表
     * 🚀 建议：前端只在页面初始化（mounted）时调用一次，不要轮询这个接口！
     */
    @GetMapping("/devices")
    public Result list() {
        return Result.success(deviceService.listAllDevices());
    }

    /**
     * 🚀 新增：轻量级状态轮询接口 (只返回 ID, Status, Enabled)
     * 目标：解决前端卡死，将原本查询全表的操作降级为查询索引字段
     */
    @GetMapping("/devices/status-only")
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
     * 2. 添加设备
     */
    @PostMapping("/devices")
    public Result add(@RequestBody Device device,
                      @RequestAttribute(value = "uid", required = false) Object uidObj) {
        // 1. 手动判断属性是否存在，避免 ServletRequestBindingException
        if (uidObj == null) {
            return Result.error(401, "登录凭证缺失，请重新登录");
        }

        // 2. 安全转换为 Long (Hutool 解析出的可能是 Integer)
        Long uid = Long.valueOf(uidObj.toString());

        // 3. 权限校验
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
     * 3. 更新设备 (包含启停控制)
     */
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

    /**
     * 4. 删除设备
     */
    @DeleteMapping("/devices/{id}")
    public Result delete(@PathVariable Integer id, @RequestAttribute("uid") Long uid) {
        if (!userService.isAdmin(uid)) return Result.error(403, "无权操作");
        deviceService.removeById(id);
        return Result.success("删除成功");
    }

    /**
     * 5. 供 Python AI 后端调用的同步接口
     */
    @PostMapping("/devices/sync-status")
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
     * 6. 获取单个设备状态
     * 🚀 优化：不再使用 getById(id) 全量查询，建议前端直接从上面的 status-only 列表里取
     */
    @GetMapping("/stream/status/{id}")
    public Result getStatus(@PathVariable Integer id) {
        // 直接从数据库核心字段读
        int status = deviceService.getDeviceStatus(id);
        return Result.success(Map.of("status", status));
    }
}