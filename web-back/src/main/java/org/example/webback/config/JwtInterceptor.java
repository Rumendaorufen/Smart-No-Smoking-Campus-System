package org.example.webback.config;

import cn.hutool.jwt.JWT;
import cn.hutool.jwt.JWTUtil;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.example.webback.common.Result;
import org.springframework.util.StringUtils;
import org.springframework.web.servlet.HandlerInterceptor;
import com.fasterxml.jackson.databind.ObjectMapper;

// 拦截器逻辑
public class JwtInterceptor implements HandlerInterceptor {

    // 密钥 (和 AuthService 里保持一致，建议放 yml)
    private static final byte[] JWT_KEY = "your_secret_key".getBytes();

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        // 1. 如果是 OPTIONS 请求 (跨域预检)，直接放行
        if ("OPTIONS".equals(request.getMethod())) {
            return true;
        }

        // 2. 获取 Token
        String token = request.getHeader("Authorization");
        if (!StringUtils.hasText(token)) {
            // 尝试从 Query 参数获取 (WebSocket 连接时可能会用到)
            token = request.getParameter("token");
        }

        // 去掉 "Bearer " 前缀
        if (StringUtils.hasText(token) && token.startsWith("Bearer ")) {
            token = token.substring(7);
        }

        // 3. 校验 Token
        if (!StringUtils.hasText(token) || !JWTUtil.verify(token, JWT_KEY)) {
            returnAuthError(response, "未登录或 Token 已过期");
            return false; // 拦截
        }

        try {
            // 4. 解析 Token 获取 uid
            JWT jwt = JWTUtil.parseToken(token);
            Long uid = Long.valueOf(jwt.getPayload("uid").toString());

            // ✅ 关键：把 uid 存入 request，Controller 里 @RequestAttribute("uid") 才能拿到
            request.setAttribute("uid", uid);
            return true; // 放行
        } catch (Exception e) {
            returnAuthError(response, "Token 无效");
            return false;
        }
    }

    // 辅助：返回 JSON 错误
    private void returnAuthError(HttpServletResponse response, String msg) throws Exception {
        response.setContentType("application/json;charset=UTF-8");
        response.setStatus(401);
        Result<Object> result = Result.error(401, msg);
        response.getWriter().write(new ObjectMapper().writeValueAsString(result));
    }
}