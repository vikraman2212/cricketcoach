package io.aicoach.middleware.service;

import io.aicoach.middleware.exception.SpeedTrackingServiceException;
import io.aicoach.middleware.model.DeliveryAnalysisResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.InvalidMediaTypeException;
import org.springframework.http.MediaType;
import org.springframework.http.client.MultipartBodyBuilder;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.reactive.function.BodyInserters;
import org.springframework.web.reactive.function.client.WebClient;

import java.io.IOException;
import java.util.Objects;

@Service
public class SpeedTrackingClient {

    private final WebClient webClient;

    public SpeedTrackingClient(
            WebClient.Builder webClientBuilder,
            @Value("${speedtracking.service.base-url:http://localhost:8000}") String baseUrl) {
        this.webClient = webClientBuilder.baseUrl(baseUrl).build();
    }

    public DeliveryAnalysisResponse analyze(MultipartFile video, String configurations) {
        try {
            MultipartInputStreamFileResource resource = new MultipartInputStreamFileResource(
                    video.getInputStream(),
                    Objects.requireNonNullElse(video.getOriginalFilename(), "delivery.mp4"),
                    video.getSize());
            MultipartBodyBuilder bodyBuilder = new MultipartBodyBuilder();
            bodyBuilder.part("video", resource)
                    .header(HttpHeaders.CONTENT_TYPE, resolveMediaType(video).toString());
            bodyBuilder.part("configurations", configurations);

            DeliveryAnalysisResponse response = webClient.post()
                    .uri("/api/v1/deliveries/analyze")
                    .contentType(MediaType.MULTIPART_FORM_DATA)
                    .body(BodyInserters.fromMultipartData(bodyBuilder.build()))
                    .retrieve()
                    .onStatus(HttpStatusCode::isError, clientResponse -> clientResponse.bodyToMono(String.class)
                            .map(body -> new SpeedTrackingServiceException("SpeedTracking API error: " + body)))
                    .bodyToMono(DeliveryAnalysisResponse.class)
                    .block();

            if (response == null) {
                throw new SpeedTrackingServiceException("SpeedTracking API returned an empty response");
            }
            return response;
        } catch (IOException ex) {
            throw new SpeedTrackingServiceException("Failed to stream uploaded video to SpeedTracking API", ex);
        }
    }

    private MediaType resolveMediaType(MultipartFile video) {
        if (video.getContentType() == null || video.getContentType().isBlank()) {
            return MediaType.APPLICATION_OCTET_STREAM;
        }
        try {
            return MediaType.parseMediaType(video.getContentType());
        } catch (InvalidMediaTypeException ex) {
            return MediaType.APPLICATION_OCTET_STREAM;
        }
    }
}