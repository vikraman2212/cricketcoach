package io.aicoach.middleware.controller;

import io.aicoach.middleware.exception.UserNotFoundException;
import io.aicoach.middleware.service.DeliveryStore;
import io.aicoach.middleware.service.SpeedTrackingClient;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

/**
 * Relays Server-Sent Events from the speedtracking-api to the Flutter client.
 *
 * <p>Step 4 in the async pipeline: Flutter opens this SSE stream after
 * uploading the video to MinIO.  This controller proxies the event stream
 * from {@code GET {speedtracking-api}/api/v1/deliveries/{id}/events} to
 * the Flutter client so the Flutter app only talks to the middleware.</p>
 */
@RestController
@RequestMapping("/api/v1/deliveries")
public class DeliveryStreamController {

    private final DeliveryStore deliveryStore;
    private final SpeedTrackingClient speedTrackingClient;
    private final long sseTimeoutMs;

    public DeliveryStreamController(
            DeliveryStore deliveryStore,
            SpeedTrackingClient speedTrackingClient,
            @Value("${delivery.stream.timeout-ms:120000}") long sseTimeoutMs) {
        this.deliveryStore = deliveryStore;
        this.speedTrackingClient = speedTrackingClient;
        this.sseTimeoutMs = sseTimeoutMs;
    }

    /**
     * {@code GET /api/v1/deliveries/{delivery_id}/stream}
     *
     * <p>Opens an SSE connection and relays progress events from the
     * speedtracking-api to the caller.  Returns 404 if the delivery is
     * not found in the in-memory store.</p>
     */
    @GetMapping(value = "/{deliveryId}/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter streamDelivery(@PathVariable String deliveryId) {
        if (!deliveryStore.exists(deliveryId)) {
            throw new UserNotFoundException("Delivery not found: " + deliveryId);
        }

        SseEmitter emitter = new SseEmitter(sseTimeoutMs);

        Thread relayThread = Thread.ofVirtual()
                .name("sse-relay-" + deliveryId)
                .start(() -> speedTrackingClient.relayEvents(deliveryId, emitter));

        emitter.onCompletion(relayThread::interrupt);
        emitter.onTimeout(relayThread::interrupt);
        emitter.onError(ex -> relayThread.interrupt());

        return emitter;
    }
}
