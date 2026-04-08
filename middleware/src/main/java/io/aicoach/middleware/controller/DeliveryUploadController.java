package io.aicoach.middleware.controller;

import io.aicoach.middleware.model.DeliveryUploadRequest;
import io.aicoach.middleware.model.DeliveryUploadResponse;
import io.aicoach.middleware.service.DeliveryStore;
import io.aicoach.middleware.service.MinioPresignedUrlClient;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import tools.jackson.core.exc.StreamWriteException;
import tools.jackson.databind.DatabindException;
import tools.jackson.databind.ObjectMapper;

import java.util.UUID;

/**
 * Handles delivery upload initiation.
 *
 * <p>Step 1 in the async pipeline: Flutter calls this endpoint to obtain a
 * presigned MinIO PUT URL and a {@code delivery_id}.  Flutter then uploads
 * the video directly to MinIO (step 2), after which MinIO fires a webhook to
 * the speedtracking-api to begin processing (step 3).</p>
 */
@RestController
@RequestMapping("/api/v1/deliveries")
public class DeliveryUploadController {

    private final MinioPresignedUrlClient minioPresignedUrlClient;
    private final DeliveryStore deliveryStore;
    private final ObjectMapper objectMapper;

    public DeliveryUploadController(
            MinioPresignedUrlClient minioPresignedUrlClient,
            DeliveryStore deliveryStore,
            ObjectMapper objectMapper) {
        this.minioPresignedUrlClient = minioPresignedUrlClient;
        this.deliveryStore = deliveryStore;
        this.objectMapper = objectMapper;
    }

    /**
     * {@code POST /api/v1/deliveries/upload}
     *
     * <p>Validates the delivery configuration, generates a presigned MinIO PUT
     * URL, stores the delivery metadata in memory, and returns the
     * {@code delivery_id} and {@code upload_url} to the caller.</p>
     */
    @PostMapping("/upload")
    public ResponseEntity<DeliveryUploadResponse> requestUpload(
            @RequestBody DeliveryUploadRequest request) {

        validateRequest(request);

        String deliveryId = UUID.randomUUID().toString();
        String objectKey = "deliveries/" + deliveryId + "/video.mp4";

        String uploadUrl = minioPresignedUrlClient.generatePutUrl(objectKey);

        String configurationsJson = toJson(request);
        deliveryStore.put(deliveryId, objectKey, configurationsJson);

        return ResponseEntity.accepted()
                .body(new DeliveryUploadResponse(deliveryId, uploadUrl));
    }

    private void validateRequest(DeliveryUploadRequest request) {
        if (request.pitchLengthMeters() <= 0) {
            throw new IllegalArgumentException("pitch_length_meters must be positive");
        }
        if (request.ballColor() == null || request.ballColor().isBlank()) {
            throw new IllegalArgumentException("ball_color must not be blank");
        }
        if (request.ballWeightGrams() <= 0) {
            throw new IllegalArgumentException("ball_weight_grams must be positive");
        }
        if (request.bowlingStyle() == null || request.bowlingStyle().isBlank()) {
            throw new IllegalArgumentException("bowling_style must not be blank");
        }
        if (request.bowlerHeightCm() <= 0) {
            throw new IllegalArgumentException("bowler_height_cm must be positive");
        }
    }

    private String toJson(DeliveryUploadRequest request) {
        try {
            return objectMapper.writeValueAsString(request);
        } catch (StreamWriteException | DatabindException ex) {
            throw new IllegalStateException("Failed to serialise delivery configuration", ex);
        }
    }
}
