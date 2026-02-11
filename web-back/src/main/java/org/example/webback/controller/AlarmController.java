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
@RequestMapping("/api/alert")
public class AlarmController {

    @Autowired
    private AlarmService alarmService;
    @Autowired
    private UserService userService;

    // 获取待审核列表
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

    // 提交审核结果
    @PostMapping("/{id}/audit")
    public Result auditAlarm(@PathVariable Long id,
                             @RequestBody Map<String, Object> body,
                             @RequestAttribute("uid") Long uid) {
        Integer status = (Integer) body.get("status");
        String remark = (String) body.get("remark");

        if (status == null) return Result.error(400, "状态码不能为空");

        try {
            // 核心业务：更新状态 + 记录审核人 + 记录时间
            alarmService.auditAlarm(id, status, remark, Math.toIntExact(uid));
            return Result.success("审核完成");
        } catch (RuntimeException e) {
            return Result.error(500, e.getMessage());
        }
    }

    // 历史档案查询 (多条件搜索)
    @GetMapping("/archive")
    public Result getArchive(@RequestParam(defaultValue = "1") Integer page,
                             @RequestParam(defaultValue = "10") Integer pageSize,
                             @RequestParam(required = false) Integer deviceId,
                             @RequestParam(required = false) Integer status,
                             @RequestParam(required = false) String startTime,
                             @RequestParam(required = false) String endTime) {

        IPage<Alarm> result = alarmService.getArchivedAlarms(page, pageSize, deviceId, status, startTime, endTime);
        return Result.success(Map.of("list", result.getRecords(), "total", result.getTotal()));
    }

    // 删除记录 (物理删除 + 数据库删除)
    @DeleteMapping("/{id}")
    public Result deleteAlarm(@PathVariable Long id, @RequestAttribute("uid") Long uid) {
        if (!userService.isAdmin(uid)) return Result.error(403, "无权操作");

        try {
            // 这是一个事务操作：同时删文件和删库
            alarmService.removeAlarmWithFile(id);
            return Result.success("删除成功");
        } catch (RuntimeException e) {
            return Result.error(500, e.getMessage());
        }
    }
}