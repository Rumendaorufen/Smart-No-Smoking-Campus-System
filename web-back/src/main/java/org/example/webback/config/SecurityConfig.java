package org.example.webback.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    // 1. 注入加密工具 Bean，供 Service 使用
    @Bean
    public BCryptPasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    // 2. 配置过滤链
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
                // 关闭 CSRF (因为我们使用 JWT，不需要 CSRF)
                .csrf(csrf -> csrf.disable())
                // 关闭 Session (JWT 是无状态的)
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                // 允许跨域 (配合 WebMvcConfig)
                .cors(cors -> cors.configure(http))
                // 拦截规则
                .authorizeHttpRequests(auth -> auth
                        // ✅ 放行登录接口、静态资源、WebSocket、视频流等
                        .requestMatchers(
                                "/api/auth/login",
                                "/static/**",
                                "/ws/**",
                                "/error"
                        ).permitAll()
                        // 🚀 其他接口也不要让 SpringSecurity 拦截，
                        // 我们使用自定义的 JwtInterceptor 来拦截 (更灵活)
                        .anyRequest().permitAll()
                );

        return http.build();
    }
}