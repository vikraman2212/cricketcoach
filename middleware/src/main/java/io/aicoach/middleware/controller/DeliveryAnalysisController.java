package io.aicoach.middleware.controller;

import io.aicoach.middleware.model.DeliveryAnalysisResponse;
import io.aicoach.middleware.service.SpeedTrackingClient;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/v1/deliveries")
public class DeliveryAnalysisController {

    private final SpeedTrackingClient speedTrackingClient;

    public DeliveryAnalysisController(SpeedTrackingClient speedTrackingClient) {
        this.speedTrackingClient = speedTrackingClient;
    }

    @PostMapping(value = "/analyze", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<DeliveryAnalysisResponse> analyze(
            @RequestPart("video") MultipartFile video,
            @RequestPart("configurations") String configurations) {
        if (video.isEmpty()) {
            throw new IllegalArgumentException("video must not be empty");
        }
        if (configurations == null || configurations.isBlank()) {
            throw new IllegalArgumentException("configurations must not be blank");
        }

        DeliveryAnalysisResponse response = speedTrackingClient.analyze(video, configurations);
        return ResponseEntity.ok(response);
    }
}