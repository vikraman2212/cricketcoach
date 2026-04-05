package io.aicoach.middleware.controller;

import io.aicoach.middleware.service.DeliveryStore;
import io.aicoach.middleware.service.SpeedTrackingClient;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(DeliveryStreamController.class)
class DeliveryStreamControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private DeliveryStore deliveryStore;

    @MockitoBean
    private SpeedTrackingClient speedTrackingClient;

    @Test
    void streamDelivery_returns404WhenDeliveryNotFound() throws Exception {
        when(deliveryStore.exists("unknown-id")).thenReturn(false);

        mockMvc.perform(get("/api/v1/deliveries/unknown-id/stream"))
                .andExpect(status().isNotFound());
    }

    @Test
    void streamDelivery_returnsOkAndSseContentTypeWhenDeliveryExists() throws Exception {
        when(deliveryStore.exists("known-id")).thenReturn(true);

        mockMvc.perform(get("/api/v1/deliveries/known-id/stream")
                        .header("Accept", "text/event-stream"))
                .andExpect(status().isOk());
    }
}
