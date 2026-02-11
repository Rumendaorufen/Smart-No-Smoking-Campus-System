package org.example.webback.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class WebMvcConfig implements WebMvcConfigurer {

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        // 允许所有路径跨域
        registry.addMapping("/**")
                .allowedOriginPatterns("*") // 允许所有来源
                .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
                .allowedHeaders("*")
                .allowCredentials(true)
                .maxAge(3600);
    }

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(new JwtInterceptor())
                .addPathPatterns("/api/**") // 拦截所有 /api 开头的请求
                .excludePathPatterns(
                        "/api/auth/login",    // 放行登录
                        "/api/monitor/stream/**", // 放行视频流相关(如果有)
                        "/api/internal/**"    // 放行 Python 内部调用的接口(建议加 IP 白名单，这里暂且放行)
                );
    }
}