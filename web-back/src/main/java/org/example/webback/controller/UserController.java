package org.example.webback.controller;

import org.example.webback.common.Result;
import org.example.webback.entity.User;
import org.example.webback.service.UserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/user")
public class UserController {

    @Autowired
    private UserService userService;

    @GetMapping("/")
    public Result list(@RequestAttribute("uid") Long uid) {
        if (!userService.isAdmin(uid)) return Result.error(403, "权限不足");

        List<User> users = userService.listAllUsers();
        return Result.success(users);
    }

    @PostMapping("/")
    public Result add(@RequestBody User form, @RequestAttribute("uid") Long uid) {
        if (!userService.isAdmin(uid)) return Result.error(403, "权限不足");

        try {
            // 创建用户逻辑：查重、加密密码
            userService.createUser(form);
            return Result.success("用户创建成功");
        } catch (RuntimeException e) {
            return Result.error(400, e.getMessage());
        }
    }

    @PutMapping("/{id}")
    public Result update(@PathVariable Long id, @RequestBody User form, @RequestAttribute("uid") Long uid) {
        if (!userService.isAdmin(uid)) return Result.error(403, "权限不足");

        try {
            // 更新用户逻辑：处理密码加密、空值判断
            form.setId(id); // 确保 ID 正确
            userService.updateUser(form);
            return Result.success("更新成功");
        } catch (RuntimeException e) {
            return Result.error(500, e.getMessage());
        }
    }

    @DeleteMapping("/{id}")
    public Result delete(@PathVariable Long id, @RequestAttribute("uid") Long uid) {
        if (!userService.isAdmin(uid)) return Result.error(403, "权限不足");
        if (id.equals(uid)) return Result.error(400, "无法删除当前登录账号");

        userService.removeById(id);
        return Result.success("删除成功");
    }
}