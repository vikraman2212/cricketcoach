package io.aicoach.middleware.exception;

public class UserNotFoundException extends RuntimeException {

    private final String detail;

    public UserNotFoundException() {
        this.detail = "User not found";
    }

    public UserNotFoundException(String detail) {
        this.detail = detail;
    }

    @Override
    public String getMessage() {
        return detail;
    }
}
