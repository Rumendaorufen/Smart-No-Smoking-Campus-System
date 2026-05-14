package org.example.webback.config;

import jakarta.servlet.*;
import jakarta.servlet.http.HttpServletRequest;
import org.slf4j.MDC;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.util.UUID;

@Component
@Order(1)
public class TraceIdFilter implements Filter {

    private static final String TRACE_ID_HEADER = "X-Trace-Id";

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
            throws IOException, ServletException {

        HttpServletRequest httpRequest = (HttpServletRequest) request;
        String traceId = httpRequest.getHeader(TRACE_ID_HEADER);

        if (traceId == null || traceId.isBlank()) {
            traceId = UUID.randomUUID().toString().replace("-", "");
        }

        MDC.put("trace_id", traceId);
        MDC.put("endpoint", httpRequest.getRequestURI());

        try {
            chain.doFilter(request, response);
        } finally {
            MDC.remove("trace_id");
            MDC.remove("endpoint");
            MDC.remove("user_id");
        }
    }
}
