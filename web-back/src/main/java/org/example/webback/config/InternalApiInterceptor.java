package org.example.webback.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.example.webback.common.Result;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.util.StringUtils;
import org.springframework.web.servlet.HandlerInterceptor;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

public class InternalApiInterceptor implements HandlerInterceptor {

    public static final String TOKEN_HEADER = "X-Internal-Token";

    private final byte[] expectedToken;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public InternalApiInterceptor(@Value("${internal.api-token}") String token) {
        if (!StringUtils.hasText(token) || token.length() < 32) {
            throw new IllegalArgumentException("internal.api-token must contain at least 32 characters");
        }
        this.expectedToken = token.getBytes(StandardCharsets.UTF_8);
    }

    @Override
    public boolean preHandle(HttpServletRequest request,
                             HttpServletResponse response,
                             Object handler) throws Exception {
        if ("OPTIONS".equalsIgnoreCase(request.getMethod())) {
            return true;
        }

        String supplied = request.getHeader(TOKEN_HEADER);
        byte[] suppliedBytes = StringUtils.hasText(supplied)
                ? supplied.getBytes(StandardCharsets.UTF_8)
                : new byte[0];

        if (!MessageDigest.isEqual(expectedToken, suppliedBytes)) {
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            response.setContentType("application/json;charset=UTF-8");
            response.getWriter().write(objectMapper.writeValueAsString(
                    Result.error(401, "内部服务认证失败")));
            return false;
        }
        return true;
    }
}
