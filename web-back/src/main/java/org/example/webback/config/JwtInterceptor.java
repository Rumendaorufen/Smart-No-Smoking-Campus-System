package org.example.webback.config;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.example.webback.common.Result;
import org.example.webback.service.JwtService;
import org.springframework.util.StringUtils;
import org.springframework.web.servlet.HandlerInterceptor;
import com.fasterxml.jackson.databind.ObjectMapper;

// 拦截器逻辑
public class JwtInterceptor implements HandlerInterceptor {

    private final JwtService jwtService;

    public JwtInterceptor(JwtService jwtService) {
        this.jwtService = jwtService;
    }

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
        if (!StringUtils.hasText(token)) {
            returnAuthError(response, "未登录或 Token 已过期");
            return false;
        }

        try {
            // 4. 统一验证签名并解析 uid
            Long uid = jwtService.verifyAndGetUserId(token);

            // ✅ 关键：把 uid 存入 request，Controller 里 @RequestAttribute("uid") 才能拿到
            request.setAttribute("uid", uid);

            // Populate MDC for log context (cleaned up by TraceIdFilter)
            org.slf4j.MDC.put("user_id", String.valueOf(uid));
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
