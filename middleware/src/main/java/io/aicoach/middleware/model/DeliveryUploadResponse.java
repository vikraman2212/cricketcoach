package io.aicoach.middleware.model;

import com.fasterxml.jackson.annotation.JsonProperty;

public record DeliveryUploadResponse(
        @JsonProperty("delivery_id") String deliveryId,
        @JsonProperty("upload_url") String uploadUrl) {
}
