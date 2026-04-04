package io.aicoach.middleware.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public record DeliveryAnalysisResponse(
        @JsonProperty("delivery_id") String deliveryId,
        @JsonProperty("delivery_physics") DeliveryPhysics deliveryPhysics,
        @JsonProperty("biomechanics") Biomechanics biomechanics,
        @JsonProperty("system_evaluations") SystemEvaluations systemEvaluations) {

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record DeliveryPhysics(
            @JsonProperty("speed_kmh") double speedKmh,
            @JsonProperty("pitch_length") String pitchLength,
            @JsonProperty("deviation") Deviation deviation) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Deviation(
            @JsonProperty("swing_type") String swingType,
            @JsonProperty("swing_degrees") double swingDegrees) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Biomechanics(
            @JsonProperty("approach_velocity_mps") double approachVelocityMps,
            @JsonProperty("front_knee_angle_degrees") double frontKneeAngleDegrees,
            @JsonProperty("momentum_transfer_efficiency") double momentumTransferEfficiency) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record SystemEvaluations(
            @JsonProperty("identified_strengths") List<String> identifiedStrengths,
            @JsonProperty("identified_flaws") List<String> identifiedFlaws) {
    }
}