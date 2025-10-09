package xiaozhi.common.exception;

import java.util.List;
import java.util.Objects;

import org.apache.shiro.authz.UnauthorizedException;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.validation.ObjectError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.servlet.resource.NoResourceFoundException;
import org.springframework.web.context.request.async.AsyncRequestNotUsableException;
import org.apache.catalina.connector.ClientAbortException;

import lombok.AllArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.utils.Result;

/**
 * 异常处理器
 * Copyright (c) 人人开源 All rights reserved.
 * Website: https://www.renren.io
 */
@Slf4j
@AllArgsConstructor
@RestControllerAdvice
public class RenExceptionHandler {

    /**
     * 处理自定义异常
     */
    @ExceptionHandler(RenException.class)
    public Result<Void> handleRenException(RenException ex) {
        Result<Void> result = new Result<>();
        result.error(ex.getCode(), ex.getMsg());

        return result;
    }

    @ExceptionHandler(DuplicateKeyException.class)
    public Result<Void> handleDuplicateKeyException(DuplicateKeyException ex) {
        Result<Void> result = new Result<>();
        result.error(ErrorCode.DB_RECORD_EXISTS);

        return result;
    }

    @ExceptionHandler(UnauthorizedException.class)
    public Result<Void> handleUnauthorizedException(UnauthorizedException ex) {
        Result<Void> result = new Result<>();
        result.error(ErrorCode.FORBIDDEN);

        return result;
    }

    @ExceptionHandler(Exception.class)
    public Result<Void> handleException(Exception ex) {
        log.error(ex.getMessage(), ex);

        return new Result<Void>().error();
    }

    @ExceptionHandler(NoResourceFoundException.class)
    public Result<Void> handleNoResourceFoundException(NoResourceFoundException ex) {
        log.warn("Resource not found: {}", ex.getMessage());
        return new Result<Void>().error(404, "资源不存在");
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public Result<Void> handleMethodArgumentNotValidException(MethodArgumentNotValidException ex) {
        List<ObjectError> allErrors = ex.getBindingResult().getAllErrors();
        String errorMsg = allErrors.stream()
                .filter(Objects::nonNull)
                .map(err -> {
                    String msg = err.getDefaultMessage();
                    return (msg != null && !msg.trim().isEmpty()) ? msg : null;
                })
                .filter(Objects::nonNull)
                .findFirst()
                .orElse("请求参数错误！");

        return new Result<Void>().error(ErrorCode.PARAM_VALUE_NULL, errorMsg);
    }

    /**
     * 处理客户端断开连接异常（断开的管道）
     * 针对文件下载等场景中客户端提前断开连接的情况
     */
    @ExceptionHandler({ClientAbortException.class, AsyncRequestNotUsableException.class})
    public void handleClientAbortException(Exception ex) {
        // 客户端断开连接，不需要返回响应，只记录警告日志
        log.warn("客户端断开连接: {}", ex.getMessage());
        // 不返回任何内容，避免再次尝试写入已断开的连接
    }

    /**
     * 处理IO异常（包括断开的管道）
     * 智能识别断开的管道异常，避免产生二次异常
     */
    @ExceptionHandler(java.io.IOException.class)
    public void handleIOException(java.io.IOException ex) {
        // 检查是否是断开的管道异常
        if (ex.getMessage() != null && ex.getMessage().contains("断开的管道")) {
            log.warn("客户端断开连接: {}", ex.getMessage());
            // 不返回任何内容，避免二次异常
        } else {
            log.error("IO异常: {}", ex.getMessage(), ex);
        }
    }

}