package io.aicoach.middleware.model;

import com.fasterxml.jackson.annotation.JsonProperty;

public record DeliveryUploadRequest(
        @JsonProperty("pitch_length_meters") double pitchLengthMeters,
        @JsonProperty("ball_color") String ballColor,
        @JsonProperty("ball_weight_grams") int ballWeightGrams,
        @JsonProperty("bowling_style") String bowlingStyle,
        @JsonProperty("bowler_height_cm") int bowlerHeightCm) {
}
