package io.aicoach.middleware.controller;

import io.aicoach.middleware.service.DeliveryStore;
import io.aicoach.middleware.service.MinioPresignedUrlClient;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(DeliveryUploadController.class)
class DeliveryUploadControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private MinioPresignedUrlClient minioPresignedUrlClient;

    @MockitoBean
    private DeliveryStore deliveryStore;

    @Test
    void uploadRequest_returnsAcceptedWithDeliveryIdAndUploadUrl() throws Exception {
        when(minioPresignedUrlClient.generatePutUrl(anyString()))
                .thenReturn("http://minio:9000/deliveries/fake-id/video.mp4?X-Amz-Signature=abc");

        String requestBody = """
                {
                  "pitch_length_meters": 22.0,
                  "ball_color": "red",
                  "ball_weight_grams": 156,
                  "bowling_style": "fast",
                  "bowler_height_cm": 180
                }
                """;

        mockMvc.perform(post("/api/v1/deliveries/upload")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(requestBody))
                .andExpect(status().isAccepted())
                .andExpect(jsonPath("$.delivery_id").isNotEmpty())
                .andExpect(jsonPath("$.upload_url").value(
                        "http://minio:9000/deliveries/fake-id/video.mp4?X-Amz-Signature=abc"));

        verify(deliveryStore).put(anyString(), anyString(), anyString());
    }

    @Test
    void uploadRequest_returnsBadRequestWhenPitchLengthIsZero() throws Exception {
        String requestBody = """
                {
                  "pitch_length_meters": 0,
                  "ball_color": "red",
                  "ball_weight_grams": 156,
                  "bowling_style": "fast",
                  "bowler_height_cm": 180
                }
                """;

        mockMvc.perform(post("/api/v1/deliveries/upload")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(requestBody))
                .andExpect(status().isBadRequest());
    }

    @Test
    void uploadRequest_returnsBadRequestWhenBallColorIsBlank() throws Exception {
        String requestBody = """
                {
                  "pitch_length_meters": 22.0,
                  "ball_color": "",
                  "ball_weight_grams": 156,
                  "bowling_style": "fast",
                  "bowler_height_cm": 180
                }
                """;

        mockMvc.perform(post("/api/v1/deliveries/upload")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(requestBody))
                .andExpect(status().isBadRequest());
    }

    @Test
    void uploadRequest_returnsBadRequestWhenBowlingStyleIsBlank() throws Exception {
        String requestBody = """
                {
                  "pitch_length_meters": 22.0,
                  "ball_color": "red",
                  "ball_weight_grams": 156,
                  "bowling_style": "   ",
                  "bowler_height_cm": 180
                }
                """;

        mockMvc.perform(post("/api/v1/deliveries/upload")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(requestBody))
                .andExpect(status().isBadRequest());
    }
}
