package io.aicoach.middleware.service;

import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

/**
 * In-memory store for delivery metadata created at upload time.
 * <p>
 * TTL: entries are never explicitly evicted in this implementation; a
 * production deployment should add a scheduled task to purge entries older
 * than 1 hour or switch to Redis.
 * </p>
 */
@Service
public class DeliveryStore {

    public record DeliveryEntry(
            String deliveryId,
            String objectKey,
            String configurations,
            Instant createdAt) {
    }

    private final ConcurrentHashMap<String, DeliveryEntry> store = new ConcurrentHashMap<>();

    public void put(String deliveryId, String objectKey, String configurations) {
        store.put(deliveryId, new DeliveryEntry(deliveryId, objectKey, configurations, Instant.now()));
    }

    public Optional<DeliveryEntry> get(String deliveryId) {
        return Optional.ofNullable(store.get(deliveryId));
    }

    public boolean exists(String deliveryId) {
        return store.containsKey(deliveryId);
    }
}
