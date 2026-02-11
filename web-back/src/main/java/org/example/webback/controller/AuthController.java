package org.example.webback.controller;

import jakarta.servlet.http.HttpServletRequest;
import org.example.webback.common.Result;
import org.example.webback.service.AuthService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    @Autowired
    private AuthService authService;

    @PostMapping("/login")
    public Result login(@RequestBody Map<String, String> data, HttpServletRequest request) {
        String username = data.get("username");
        String password = data.get("password");
        String ip = getClientIp(request);

        try {
            // 所有复杂的校验、加密、生成Token逻辑都在 Service 里
            Map<String, Object> result = authService.login(username, password, ip);
            return Result.success(result);
        } catch (RuntimeException e) {
            return Result.error(401, e.getMessage());
        }
    }

    @PostMapping("/logout")
    public Result logout() {
        return Result.success("退出成功");
    }

    @GetMapping("/me")
    public Result me(@RequestAttribute("uid") Long uid) {
        // 简单查询可以直接调用 Service 获取用户信息
        return Result.success(authService.getCurrentUser(uid));
    }

    // 获取真实IP工具方法
    private String getClientIp(HttpServletRequest request) {
        String ip = request.getHeader("X-Forwarded-For");
        if (ip == null || ip.length() == 0 || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getHeader("X-Real-IP");
        }
        if (ip == null || ip.length() == 0 || "unknown".equalsIgnoreCase(ip)) {
            ip = request.getRemoteAddr();
        }
        return ip;
    }
}