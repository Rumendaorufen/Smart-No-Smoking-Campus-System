package org.example.webback.config;

import org.example.webback.common.Result;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalExceptionHandler {

    // 捕获所有 RuntimeException
    @ExceptionHandler(RuntimeException.class)
    public Result<String> handleRuntimeException(RuntimeException e) {
        // 打印堆栈信息到控制台，方便调试
        e.printStackTrace();
        // 返回友好的 JSON 错误
        return Result.error(e.getMessage());
    }

    // 捕获所有其他 Exception
    @ExceptionHandler(Exception.class)
    public Result<String> handleException(Exception e) {
        e.printStackTrace();
        return Result.error("系统内部错误: " + e.getMessage());
    }
}