package io.aicoach.middleware.service;

import io.aicoach.middleware.exception.SpeedTrackingServiceException;
import io.aicoach.middleware.model.DeliveryAnalysisResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.InvalidMediaTypeException;
import org.springframework.http.MediaType;
import org.springframework.http.client.MultipartBodyBuilder;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.reactive.function.BodyInserters;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

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

    /**
     * Relays Server-Sent Events from the speedtracking-api to the given
     * {@link SseEmitter}.  Blocks until the upstream stream completes, times
     * out, or the calling thread is interrupted.
     *
     * @param deliveryId the delivery to stream events for
     * @param emitter    the Spring MVC SSE emitter to relay events through
     */
    public void relayEvents(String deliveryId, SseEmitter emitter) {
        try {
            webClient.get()
                    .uri("/api/v1/deliveries/{id}/events", deliveryId)
                    .accept(MediaType.TEXT_EVENT_STREAM)
                    .retrieve()
                    .onStatus(HttpStatusCode::isError, clientResponse -> clientResponse.bodyToMono(String.class)
                            .map(body -> new SpeedTrackingServiceException(
                                    "SpeedTracking API error on SSE stream: " + body)))
                    .bodyToFlux(new ParameterizedTypeReference<ServerSentEvent<String>>() {})
                    .doOnNext(sse -> {
                        try {
                            SseEmitter.SseEventBuilder event = SseEmitter.event()
                                    .data(sse.data() != null ? sse.data() : "");
                            if (sse.event() != null) {
                                event.name(sse.event());
                            }
                            emitter.send(event);
                        } catch (IOException ex) {
                            throw new SpeedTrackingServiceException("Failed to relay SSE event", ex);
                        }
                    })
                    .blockLast();

            emitter.complete();
        } catch (SpeedTrackingServiceException ex) {
            emitter.completeWithError(ex);
        } catch (Exception ex) {
            emitter.completeWithError(
                    new SpeedTrackingServiceException("SSE relay failed: " + ex.getMessage(), ex));
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