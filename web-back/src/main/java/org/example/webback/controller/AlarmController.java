package org.example.webback.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import org.example.webback.common.Result;
import org.example.webback.entity.Alarm;
import org.example.webback.service.AlarmService;
import org.example.webback.service.UserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/alerts") // 🚀 确保与前端一致的复数路径
public class AlarmController {

    @Autowired
    private AlarmService alarmService;

    @Autowired
    private UserService userService;

    /**
     * 获取待审核报警
     */
    @GetMapping("/pending")
    public Result getPendingAlerts(@RequestParam(defaultValue = "1") Integer page,
                                   @RequestParam(defaultValue = "20") Integer pageSize) {
        IPage<Alarm> result = alarmService.getPendingAlarms(page, pageSize);
        return Result.success(Map.of(
                "list", result.getRecords(),
                "total", result.getTotal(),
                "pages", result.getPages()
        ));
    }

    /**
     * 提交审核结果
     */
    @PostMapping("/{id}/audit")
    public Result auditAlarm(@PathVariable Long id,
                             @RequestBody Map<String, Object> body,
                             @RequestAttribute("uid") Object uid) {
        Integer status = (Integer) body.get("status");
        String remark = (String) body.get("remark");

        if (status == null) return Result.error(400, "必须选择审核状态");

        try {
            // 🚀 这里要小心转换拦截器传来的 UID 类型
            Integer userId = Integer.valueOf(uid.toString());
            alarmService.auditAlarm(id, status, remark, userId);
            return Result.success("审核操作已成功记录");
        } catch (Exception e) {
            return Result.error(500, "审核失败: " + e.getMessage());
        }
    }

    /**
     * 历史档案查询 (支持模糊搜索)
     */
    @GetMapping("/archive")
    public Result getArchive(@RequestParam(defaultValue = "1") Integer page,
                             @RequestParam(defaultValue = "10") Integer pageSize,
                             @RequestParam(required = false) Integer deviceId,
                             @RequestParam(required = false) Integer status,
                             @RequestParam(required = false) String startTime,
                             @RequestParam(required = false) String endTime) {

        IPage<Alarm> result = alarmService.getArchivedAlarms(page, pageSize, deviceId, status, startTime, endTime);
        return Result.success(Map.of(
                "list", result.getRecords(),
                "total", result.getTotal()
        ));
    }

    /**
     * 永久删除记录
     */
    @DeleteMapping("/{id}")
    public Result deleteAlarm(@PathVariable Long id, @RequestAttribute("uid") Object uid) {
        Long userId = Long.valueOf(uid.toString());
        if (!userService.isAdmin(userId)) {
            return Result.error(403, "权限不足：只有管理员可删除档案");
        }

        try {
            alarmService.removeAlarmWithFile(id);
            return Result.success("该报警记录及相关文件已物理删除");
        } catch (Exception e) {
            return Result.error(500, "删除操作异常");
        }
    }

    @PostMapping("/report")
    public Result reportAlarm(@RequestBody Map<String, Object> payload) {
        try {
            // 1. 解析 Python 发来的字段 (与 Python 的 payload 保持一致)
            Integer deviceId = (Integer) payload.get("deviceId");
            String type = (String) payload.get("type");
            Double confidence = (Double) payload.get("confidence");
            String snapshotUrl = (String) payload.get("snapshotUrl");
            String videoUrl = (String) payload.get("videoUrl");

            // 2. 调用 Service 保存到 DB
            alarmService.saveInternalAlarm(deviceId, type, confidence, snapshotUrl, videoUrl);

            return Result.success("报警数据已接收并存库");
        } catch (Exception e) {
            return Result.error(500, "数据解析或存库失败: " + e.getMessage());
        }
    }
}