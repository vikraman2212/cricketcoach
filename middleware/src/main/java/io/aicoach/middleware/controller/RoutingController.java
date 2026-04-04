package io.aicoach.middleware.controller;


import io.aicoach.middleware.exception.UserNotFoundException;
import io.aicoach.middleware.model.UserData;
import org.springframework.http.HttpStatus;
import org.springframework.http.RequestEntity;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class RoutingController {

    @GetMapping("/api/v1/getSpeed")
    public ResponseEntity<String> routeRequestToSpeedometer(RequestEntity<UserData> request) throws UserNotFoundException {
        // Implement routing logic based on the path
        // For example, you can use a switch statement or a map to route to different controllers
        if (request.getBody().userId().equals("")) {
            throw new UserNotFoundException();
        }
        return new ResponseEntity<>("Routing to SpeedometerController", HttpStatus.OK);
    }

}
