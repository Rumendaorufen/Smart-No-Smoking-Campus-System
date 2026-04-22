package org.example.webback.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.Collections;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public BCryptPasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
                .csrf(csrf -> csrf.disable())
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                // 🚀 显式配置跨域，防止 OPTIONS 请求被拦截
                .cors(cors -> cors.configurationSource(corsConfigurationSource()))
                .authorizeHttpRequests(auth -> auth
                        // ✅ 1. 放行登录
                        .requestMatchers("/api/auth/login").permitAll()
                        // 🚀 核心：将 AI 相关的所有接口全部放行！
//                        .requestMatchers("/api/ai/**").permitAll()
                        // ✅ 2. 放行系统监控相关 (解决 Monitor.vue 的 401)
                        .requestMatchers("/api/system/status", "/api/system/**").permitAll()
                        // ✅ 3. 放行设备管理接口 (解决 Python 拉取列表的 401 和 Vue 404)
                        .requestMatchers("/api/monitor/devices", "/api/monitor/**").permitAll()
                        // ✅ 4. 放行内部上报、WS、静态资源
                        .requestMatchers("/api/internal/**", "/ws/**", "/static/**", "/error").permitAll()
                        // 🚀 5. 其余请求也放行，交给 JwtInterceptor 处理业务权限
                        .anyRequest().permitAll()
                );

        return http.build();
    }

    // 🚀 辅助：Cors 配置源
    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration config = new CorsConfiguration();
        config.setAllowedOriginPatterns(Collections.singletonList("*"));
        config.setAllowedMethods(Collections.singletonList("*"));
        config.setAllowedHeaders(Collections.singletonList("*"));
        config.setAllowCredentials(true);
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", config);
        return source;
    }
}