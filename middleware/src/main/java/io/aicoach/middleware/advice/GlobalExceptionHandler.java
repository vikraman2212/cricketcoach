package io.aicoach.middleware.advice;

import io.aicoach.middleware.exception.SpeedTrackingServiceException;
import io.aicoach.middleware.exception.UserNotFoundException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice("io.aicoach.middleware.controller")
public class GlobalExceptionHandler {

    @ExceptionHandler(value = UserNotFoundException.class)
    public final ResponseEntity<String> handleUserNotFoundException(UserNotFoundException ex) {
        // Log the exception details
        System.err.println("Handling UserNotFoundException: " + ex.getMessage());
        // Return a custom error response with a 404 status
        return new ResponseEntity<>(ex.getMessage(), HttpStatus.NOT_FOUND);
    }

    @ExceptionHandler(value = IllegalArgumentException.class)
    public final ResponseEntity<String> handleIllegalArgumentException(IllegalArgumentException ex) {
        return new ResponseEntity<>(ex.getMessage(), HttpStatus.BAD_REQUEST);
    }

    @ExceptionHandler(value = SpeedTrackingServiceException.class)
    public final ResponseEntity<String> handleSpeedTrackingServiceException(SpeedTrackingServiceException ex) {
        return new ResponseEntity<>(ex.getMessage(), HttpStatus.BAD_GATEWAY);
    }

    @ExceptionHandler(value = Exception.class)
    public final ResponseEntity<String> handleGeneralException(Exception ex) {
        // Fallback for all other exceptions
        return new ResponseEntity<>("An internal error occurred", HttpStatus.INTERNAL_SERVER_ERROR);
    }

}
