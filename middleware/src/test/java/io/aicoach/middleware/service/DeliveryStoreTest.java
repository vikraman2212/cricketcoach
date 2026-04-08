package io.aicoach.middleware.service;

import org.junit.jupiter.api.Test;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;

class DeliveryStoreTest {

    private final DeliveryStore store = new DeliveryStore();

    @Test
    void put_and_get_returnsStoredEntry() {
        store.put("delivery-1", "deliveries/delivery-1/video.mp4", "{\"bowling_style\":\"fast\"}");

        Optional<DeliveryStore.DeliveryEntry> result = store.get("delivery-1");

        assertThat(result).isPresent();
        assertThat(result.get().deliveryId()).isEqualTo("delivery-1");
        assertThat(result.get().objectKey()).isEqualTo("deliveries/delivery-1/video.mp4");
        assertThat(result.get().configurations()).contains("fast");
        assertThat(result.get().createdAt()).isNotNull();
    }

    @Test
    void get_returnsEmptyForUnknownDelivery() {
        Optional<DeliveryStore.DeliveryEntry> result = store.get("no-such-id");
        assertThat(result).isEmpty();
    }

    @Test
    void exists_returnsTrueAfterPut() {
        store.put("delivery-2", "deliveries/delivery-2/video.mp4", "{}");
        assertThat(store.exists("delivery-2")).isTrue();
    }

    @Test
    void exists_returnsFalseForUnknownDelivery() {
        assertThat(store.exists("unknown")).isFalse();
    }
}
