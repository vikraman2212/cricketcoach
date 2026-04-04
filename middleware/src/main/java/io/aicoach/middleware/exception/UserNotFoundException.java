package io.aicoach.middleware.exception;

public class UserNotFoundException extends RuntimeException {
    public String getMessage() {
        return "User not found";
    }
}
