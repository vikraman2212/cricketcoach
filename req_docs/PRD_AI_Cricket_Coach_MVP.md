# Product Requirements Document: AI Cricket Coach — Speed Gun MVP

**Version:** 1.0  
**Date:** 3 April 2026  
**Author:** Product/BA Analysis  
**Status:** Draft for Review

---

## 1. Executive Summary

The AI Cricket Coach is a mobile app that gives amateur cricketers instant bowling speed readings from a phone camera — no radar gun required. The MVP ("Speed Gun") provides a free, shareable speed measurement to drive viral adoption among Australian grade cricket players. Future tiers add biomechanical coaching (Pro) and team management (Academy).

**MVP Goal:** A bowler records a single delivery on their phone. Within 10–15 seconds of stopping the recording, they see their bowling speed in km/h along with a pitch map showing where the ball landed, presented as a shareable card.

---

## 2. Target User

| Attribute           | Detail                                                                          |
| ------------------- | ------------------------------------------------------------------------------- |
| **Primary persona** | Amateur fast/medium bowler, 16–35 years old, playing grade cricket in Australia |
| **Context**         | Net session or casual practice — not match day                                  |
| **Device**          | iPhone or Android (modern, 2020+, capable of 60–120 fps video)                  |
| **Technical skill** | Non-technical. Must work with zero configuration beyond phone placement         |
| **Motivation**      | "How fast am I bowling?" — curiosity, bragging rights, tracking improvement     |

### User Story (MVP)

> As an amateur bowler practicing in the nets, I want to set my phone behind the stumps, bowl a delivery, and see my bowling speed within seconds — so I can track my pace and share it with mates.

---

## 3. Business Model

| Tier | Name                | Price      | Features                                                   | Status           |
| ---- | ------------------- | ---------- | ---------------------------------------------------------- | ---------------- |
| 1    | **Speed Gun** (MVP) | Free       | Speed reading, pitch map, shareable card                   | **Building now** |
| 2    | **Pro**             | ~$9.99/mo  | Skeletal overlay, run-up analysis, AI Coach chat           | Future           |
| 3    | **Academy**         | ~$29.99/mo | Coach web dashboard, squad management, aggregate analytics | Future           |

**Growth strategy (B2C2B/PLG):** Free Speed Gun creates viral adoption → players upgrade to Pro → coaches discover via their players → coaches buy Academy tier.

---

## 4. MVP Feature Scope

### 4.1 In Scope (Must Have)

| #   | Feature               | Description                                                                                 | Acceptance Criteria                                                                                                             |
| --- | --------------------- | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| F1  | **Video capture**     | Record a single delivery (3–5 sec) at maximum device frame rate                             | 60fps minimum, 120fps preferred (slow-mo). Behind-the-stumps guidance overlay.                                                  |
| F2  | **Ball detection**    | Detect the cricket ball in each frame of the video                                          | YOLOv11n + SAHI. Detect red Kookaburra ball on Australian pitches. mAP@50 ≥ 0.7 on test set.                                    |
| F3  | **Ball tracking**     | Track the ball across frames through the delivery                                           | ByteTrack + Kalman filter. Handle 1–3 frames of occlusion (behind batsman/stumps). Continuous trajectory from release to pitch. |
| F4  | **Speed calculation** | Calculate ball speed from tracked trajectory                                                | Physics engine: v = d/t using pixel-to-meter calibration. Target accuracy: **±5 km/h** for MVP (see §7).                        |
| F5  | **Pitch map**         | Show where the ball pitched (full/good/short length)                                        | Classify pitch length based on ball landing position relative to known pitch dimensions.                                        |
| F6  | **Trajectory replay** | Replay the recorded video with a glowing ball trajectory overlaid using Flutter CustomPaint | Ball path drawn over original video at playback speed. Trajectory coordinates returned from cloud, rendered client-side.        |
| F7  | **Result card**       | Display speed + pitch map as a shareable visual                                             | Card with speed (large number), pitch length classification, date, rendered within 15 sec of recording stop.                    |
| F8  | **Share**             | Share result card to social media / messaging                                               | Native OS share sheet. Export result card as image (PNG/JPG). Option to export replay as short video clip.                      |
| F9  | **Camera guidance**   | Guide user to position phone correctly                                                      | On-screen guide showing: place phone behind stumps, ensure full pitch is visible, keep phone steady.                            |

### 4.2 Out of Scope (Deferred to Pro/Academy)

| Feature                        | Tier    | Rationale for deferral                                                                                                       |
| ------------------------------ | ------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Skeletal/biomechanical overlay | Pro     | Requires bowler-pose model training (separate YOLOv11s-Pose pipeline) + Flutter skeleton renderer. NOT needed for Speed Gun. |
| Run-up speed analysis          | Pro     | Needs pose tracking across long distance                                                                                     |
| AI Coach chat (LLM feedback)   | Pro     | Needs LLM integration + prompt engineering                                                                                   |
| Swing/seam analysis            | Pro     | Requires trajectory deviation calculation (complex physics)                                                                  |
| User accounts & login          | Pro     | Speed Gun can work anonymously for viral growth                                                                              |
| Delivery history / trends      | Pro     | Requires persistent storage + auth                                                                                           |
| Coach web dashboard            | Academy | Separate web app                                                                                                             |
| Squad management               | Academy | Database + authorization model                                                                                               |
| White ball / pink ball support | v1.1    | Focus on red Kookaburra for AU grade cricket first                                                                           |

### 4.3 Nice to Have (MVP stretch)

| Feature                                    | Notes                                      |
| ------------------------------------------ | ------------------------------------------ |
| Slow-motion replay with trajectory overlay | Enhances shareability significantly        |
| Multiple deliveries in one recording       | Auto-segment deliveries from a longer clip |

### 4.4 Platform Evolution Vision

The product evolves through three platform phases. Each phase unlocks a step-change in user experience:

| Phase             | Name             | Inference Location                | Key Unlock                                                                  | Trigger to Graduate                                                 |
| ----------------- | ---------------- | --------------------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| **Phase 1 (MVP)** | Cloud Speed Gun  | Cloud (GPU)                       | Ship fast, iterate on model accuracy, retain video for debugging/retraining | Ball detector achieves ≥0.7 mAP@50 on test set                      |
| **Phase 2**       | On-Device Speed  | Edge (phone)                      | Offline use, <5 sec latency, zero cloud cost per inference                  | Model achieves ≥0.7 mAP at 1080px single-pass YOLO (no SAHI needed) |
| **Phase 3**       | Biomechanics Pro | Hybrid (edge detect + cloud pose) | Skeletal overlay, run-up analysis, AI coaching                              | User base justifies Pro tier revenue                                |

**Why cloud first:** You don't yet know if the model works. Video upload during Phase 1 gives you the raw footage to debug detection failures, retrain the model, and measure accuracy against ground truth. Once the model is proven, removing the upload step is a straightforward swap (see ERD §2.1 — `DeliveryAnalyzer` abstraction).

**Why not stay on cloud forever:** For a 3-5 second clip producing ~32 bytes of useful physics data (two trajectory points + timing), uploading 15-25 MB of video is disproportionate. On-device inference eliminates network dependency, enables offline use at nets without WiFi, and reduces per-inference cost to zero.

---

## 5. User Flow (MVP)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. OPEN APP                                                 │
│    → See "Record Delivery" button + camera guidance tips     │
│                                                             │
│ 2. POSITION PHONE                                           │
│    → Place behind stumps (tripod/propped)                   │
│    → On-screen guide confirms pitch is framed correctly     │
│                                                             │
│ 3. TAP RECORD                                               │
│    → Camera starts at max fps (120fps if available)         │
│    → Bowler bowls a single delivery                         │
│                                                             │
│ 4. TAP STOP                                                 │
│    → Video (3-5 sec, ~15-25 MB) saved locally               │
│                                                             │
│ 5. UPLOAD + PROCESSING [Phase 1] (target: ≤15 sec total)    │
│    → App requests presigned upload URL from middleware       │
│    → Video uploads directly to MinIO (3-5 sec on WiFi)      │
│    → MinIO webhook triggers analysis in FastAPI              │
│    → App opens SSE stream for live progress updates:        │
│       "Detecting ball..." → "Tracking..." → "Calculating..."│
│                                                             │
│ 5b. ON-DEVICE PROCESSING [Phase 2 — future]                 │
│    → App runs YOLO inference locally on video frames        │
│    → Physics engine runs on-device                          │
│    → Result in <5 sec, no upload needed                     │
│                                                             │
│ 6. RESULT SCREEN                                            │
│    → Video replays with glowing ball trajectory overlay      │
│    → Large speed number: "127 km/h"                         │
│    → Pitch map: "Good Length"                               │
│    → "Share" button → native share sheet                    │
│                                                             │
│ 7. (OPTIONAL) BOWL AGAIN                                    │
│    → Return to recording screen                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Architecture Decision: Cloud Now → Edge Later (Phased)

Given the constraints (solo developer, unproven model, need for debugging data), **cloud processing is required for MVP** — but the long-term goal is fully on-device inference.

### Phase 1: Cloud (MVP)

| Factor                     | Cloud                                   | On-Device                                      | Verdict           |
| -------------------------- | --------------------------------------- | ---------------------------------------------- | ----------------- |
| Development effort         | 1 API endpoint                          | CoreML export + Android NNAPI + Flutter bridge | **Cloud wins**    |
| Accuracy                   | Full SAHI on GPU (320×320 slices)       | Constrained to single-pass 1080px              | **Cloud wins**    |
| Latency (3-5s video)       | ~10-15 sec (upload + GPU inference)     | ~5-8 sec (no upload)                           | On-device faster  |
| Cross-platform             | Works on any phone with camera          | Must optimize per chipset                      | **Cloud wins**    |
| Model updates              | Deploy server-side, instant             | Requires app update                            | **Cloud wins**    |
| Cost                       | ~$0.01-0.03 per inference (GPU)         | Free after download                            | On-device cheaper |
| **Debugging / retraining** | **Video retained for failure analysis** | **Video never leaves phone**                   | **Cloud wins**    |

Cloud is necessary for MVP because:

1. **The model doesn't exist yet** — you need video uploads to diagnose detection failures and retrain
2. **SAHI is likely required** for acceptable accuracy — too slow for real-time on-device
3. **Server-side model updates** let you iterate without app store releases

### Phase 2: On-Device (Post-Model-Validation)

Graduation criteria: ball detector achieves **≥0.7 mAP@50 at 1080px single-pass** (no SAHI). When this is met:

| What changes                  | How                                                           |
| ----------------------------- | ------------------------------------------------------------- |
| No video upload               | YOLO runs on-device via CoreML (iOS) / ONNX Runtime (Android) |
| No MinIO / webhook / SSE      | Physics engine runs locally in Dart or via Flutter FFI        |
| Latency drops to <5 sec       | No network round-trip                                         |
| Works offline                 | Bowler can use at nets without WiFi                           |
| Cloud cost per inference = $0 | Only app download cost                                        |

The Flutter app uses a **`DeliveryAnalyzer` abstraction** (see ERD §2.1) so that swapping from `CloudAnalyzer` to `OnDeviceAnalyzer` requires zero UI changes.

### Phase 3: Hybrid (Biomechanics Pro Tier)

Pose estimation (YOLOv11s-Pose) is too large for most phones. Pro tier uses edge ball detection + cloud pose analysis. Revenue from Pro subscriptions funds the GPU cost.

---

## 7. Speed Accuracy Analysis

### What's Physically Realistic?

With a single monocular phone camera behind the stumps:

| Variable     | Value                    | Impact                            |
| ------------ | ------------------------ | --------------------------------- |
| Camera FPS   | 120 fps (iPhone slow-mo) | Each frame = 8.33ms               |
| Ball speed   | 130 km/h (~36.1 m/s)     | Ball travels 0.30m per frame      |
| Pitch length | 20.12m                   | Ball airtime ≈ 557ms = ~67 frames |
| Timing error | ±1 frame = ±8.33ms       | Speed error ≈ ±1.5% ≈ **±2 km/h** |
| At 60 fps    | ±1 frame = ±16.67ms      | Speed error ≈ ±3% ≈ **±4 km/h**   |

**Key limitations:**

- Monocular depth estimation introduces additional ±2-3 km/h error
- Ball detection misses (e.g., occlusion) can skip frames, inflating error
- Phone placement angle/distance affects pixel-to-meter calibration

**Realistic MVP accuracy target: ±5 km/h** at 120fps, **±8 km/h** at 60fps.

This is useful for amateurs ("Am I bowling 120+ or 110?") but not match-grade. Communicating this to users: show speed as a range or with a confidence indicator.

---

## 8. Success Metrics (MVP)

| Metric               | Target                          | Measurement                          |
| -------------------- | ------------------------------- | ------------------------------------ |
| Processing time      | ≤ 15 sec from stop to result    | Median p50                           |
| Speed accuracy       | ±5 km/h at 120fps               | Validated against radar gun readings |
| Ball detection rate  | ≥ 80% of frames in delivery arc | Successful trajectory extraction     |
| User completion rate | ≥ 70% record → see result       | No drop-off during processing wait   |
| Share rate           | ≥ 30% of results shared         | Track share button taps              |

---

## 9. Risks & Mitigations

| Risk                                             | Likelihood | Impact                    | Mitigation                                                                                          |
| ------------------------------------------------ | ---------- | ------------------------- | --------------------------------------------------------------------------------------------------- |
| Ball too small to detect in some frames          | High       | Speed calc fails          | SAHI mandatory; Kalman prediction fills gaps of 1-3 frames                                          |
| User places phone at wrong angle                 | High       | Calibration breaks        | Camera guidance overlay; reject videos with bad framing                                             |
| 60fps phones have poor accuracy                  | Medium     | ±8 km/h too loose         | Detect fps and warn user; prefer slow-mo mode                                                       |
| Cloud latency exceeds 15 sec on poor connection  | Medium     | Bad UX                    | Compress video before upload; show progress bar. Phase 2 eliminates upload entirely.                |
| Red ball hard to distinguish from red objects    | Medium     | False detections          | Training data includes red distractors (shoes, boundary ropes)                                      |
| Privacy concerns with video upload               | Low        | Trust issues              | Phase 1: process and delete video within 1hr; never persist. Phase 2: video never leaves the phone. |
| On-device model accuracy insufficient            | Medium     | Can't graduate to Phase 2 | Stay on cloud. Improve model with more training data from Phase 1 uploads.                          |
| Phase 2 CoreML/ONNX export breaks model accuracy | Low        | Regression                | Validate exported model against PyTorch baseline before shipping                                    |

---

## 10. Privacy & Data Handling

| Concern         | Policy                                                                                             |
| --------------- | -------------------------------------------------------------------------------------------------- |
| Video storage   | Process immediately, delete within 24 hours. Never persist raw video.                              |
| Result data     | Store anonymized speed/pitch data for product analytics. No PII.                                   |
| GDPR compliance | No user accounts in MVP = no PII collected. Add consent flows when auth is introduced in Pro tier. |
| Data retention  | Processed analytics retained 12 months max. User can request deletion.                             |

---

## 11. Dependencies & Assumptions

| #   | Dependency                                                | Status          | Risk                                       |
| --- | --------------------------------------------------------- | --------------- | ------------------------------------------ |
| D1  | YOLOv11n ball detector trained to ≥0.7 mAP@50             | Not started     | **High** — blocks everything               |
| D2  | Annotated training dataset (≥500 frames with ball bboxes) | Not started     | **High** — blocks D1                       |
| D3  | GPU for cloud inference (Phase 1)                         | Not provisioned | Medium — commodity resource                |
| D4  | Flutter video capture at 120fps                           | Unvalidated     | Medium — may need native plugin            |
| D5  | Network upload of 15-25MB video in <5 sec (Phase 1 only)  | Assumption      | Medium — eliminated in Phase 2             |
| D6  | Model achieves ≥0.7 mAP at 1080px **without** SAHI        | Unknown         | Medium — gates Phase 2 graduation          |
| D7  | CoreML / ONNX Runtime export of YOLOv11n                  | Not validated   | Medium — gates Phase 2 on-device inference |

---

## 12. Open Questions

| #   | Question                                                                                           | Owner   | Impact                                         |
| --- | -------------------------------------------------------------------------------------------------- | ------- | ---------------------------------------------- |
| Q1  | Can we get ≥0.7 mAP with <500 annotated frames + auto-labeling?                                    | ML      | Determines annotation effort                   |
| Q2  | Does Flutter `camera` plugin support 120fps across iOS + Android?                                  | Mobile  | May need native module                         |
| Q3  | Should we support landscape + portrait, or mandate one orientation?                                | UX      | Affects calibration model                      |
| Q4  | Can we use phone accelerometer to detect recording angle automatically?                            | Mobile  | Improves framing validation                    |
| Q5  | Is a "calibration step" (e.g., mark stump positions) acceptable UX?                                | Product | Improves accuracy substantially                |
| Q6  | What is the minimum mAP@50 at 1080px single-pass YOLO (no SAHI) achievable with the training data? | ML      | Determines if/when Phase 2 on-device is viable |
| Q7  | CoreML vs ONNX Runtime — which performs better on mid-range phones for real-time YOLO?             | Mobile  | Determines Phase 2 export format               |
