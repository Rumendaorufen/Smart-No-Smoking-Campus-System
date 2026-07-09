package org.example.webback.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.ClientHttpRequestInterceptor;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import java.util.Collections;

@Configuration
public class WebMvcConfig implements WebMvcConfigurer {

    @Value("${app.python-static-path}")
    private String pythonStaticPath;

    @Configuration
    public class RestConfig {
        @Bean
        public RestTemplate restTemplate() {
            RestTemplate rest = new RestTemplate();
            rest.setInterceptors(Collections.singletonList(
                (ClientHttpRequestInterceptor) (request, body, execution) -> {
                    String traceId = org.slf4j.MDC.get("trace_id");
                    if (traceId != null) {
                        request.getHeaders().add("X-Trace-Id", traceId);
                    }
                    return execution.execute(request, body);
                }
            ));
            return rest;
        }
    }

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/**")
                .allowedOriginPatterns("*")
                .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
                .allowedHeaders("*")
                .allowCredentials(true)
                .maxAge(3600);
    }

    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        registry.addResourceHandler("/static/**")
                .addResourceLocations("file:" + pythonStaticPath + "/");
    }

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(new JwtInterceptor())
                .addPathPatterns("/api/**")
                .excludePathPatterns(
                        "/api/auth/login",
                        "/api/internal/**",
                        "/api/monitor/stream/**",
                        "/api/internal/**",
                        "/api/monitor/devices/sync-status",
                        "/api/alerts/report",
                        "/api/logs/**"
                );
    }
}
