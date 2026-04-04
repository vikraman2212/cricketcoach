package io.aicoach.middleware.exception;

public class SpeedTrackingServiceException extends RuntimeException {

    public SpeedTrackingServiceException(String message) {
        super(message);
    }

    public SpeedTrackingServiceException(String message, Throwable cause) {
        super(message, cause);
    }
}