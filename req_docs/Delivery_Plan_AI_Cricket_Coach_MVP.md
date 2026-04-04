# Delivery Plan: AI Cricket Coach — Speed Gun MVP

**Version:** 1.0  
**Date:** 3 April 2026  
**Status:** Draft  
**Companion Docs:** [PRD](PRD_AI_Cricket_Coach_MVP.md) | [ERD](ERD_AI_Cricket_Coach_MVP.md)

---

## 1. Delivery Strategy

Solo developer, no hard deadline. The plan is structured as **incremental milestones** — each produces a shippable, testable artifact. No milestone depends on more than one preceding milestone (where possible), enabling context-switching without losing progress.

**Critical path:** Dataset → Model → Inference Pipeline → Flutter → Integration → Ship

---

## 2. Milestone Overview

```
M0 ─────▶ M1 ─────▶ M2 ─────▶ M3 ─────▶ M4 ─────▶ M5 ─────▶ M6
Infra     Dataset    Model      Backend    Flutter    Integrate  Ship
Setup     & Annot.   Training   Pipeline   App        E2E        MVP
```

| Milestone | Name                 | Goal                  | Exit Criteria                                                            |
| --------- | -------------------- | --------------------- | ------------------------------------------------------------------------ |
| **M0**    | Infrastructure Setup | Dev environment ready | Docker Compose (MinIO + FastAPI + Middleware) runs locally, CVAT running |
| **M1**    | Dataset & Annotation | Training data ready   | ≥500 annotated frames validated, train/val split, augmentation applied   |
| **M2**    | Model Training       | Ball detector works   | YOLOv11n ≥0.7 mAP@50, SAHI evaluation passing, model exported            |
| **M3**    | Backend Pipeline     | End-to-end inference  | Upload video → get speed + trajectory JSON (via API, no Flutter)         |
| **M4**    | Flutter App          | Mobile app functional | Record → upload → see result with trajectory overlay on device           |
| **M5**    | Integration & Polish | Full system working   | Phone → cloud → result in ≤15 sec, share working                         |
| **M6**    | Ship MVP             | Live for users        | Deployed to cloud, app on TestFlight/internal testing                    |

---

## 3. Detailed Task Breakdown

### M0: Infrastructure Setup

| #   | Task                             | Detail                                                                                    | Depends On | Effort  |
| --- | -------------------------------- | ----------------------------------------------------------------------------------------- | ---------- | ------- |
| 0.1 | Docker Compose for dev stack     | MinIO + speedtracking-api + middleware (see ERD §3)                                       | —          | 0.5 day |
| 0.2 | Configure MinIO bucket + webhook | Create `deliveries` bucket, set up webhook to FastAPI, lifecycle policy (1hr auto-delete) | 0.1        | 0.5 day |
| 0.3 | Set up CVAT via Docker           | Run CVAT locally, create project for cricket ball annotation                              | —          | 0.5 day |
| 0.4 | Verify existing scripts run      | `download_videos.py`, `extract_frames.py`, `validate_annotations.py`                      | —          | 0.5 day |

**Deliverable:** `docker compose up` brings up full dev stack. CVAT accessible at localhost:8080.

---

### M1: Dataset & Annotation

| #   | Task                                  | Detail                                                                                           | Depends On | Effort      |
| --- | ------------------------------------- | ------------------------------------------------------------------------------------------------ | ---------- | ----------- |
| 1.1 | Extract frames from downloaded videos | Run `extract_frames.py` on videos in `raw_videos/`                                               | 0.4        | 0.5 day     |
| 1.2 | Review & filter frames                | Remove frames without ball, duplicates, poor quality                                             | 1.1        | 1 day       |
| 1.3 | Annotate ball bounding boxes in CVAT  | Bbox around cricket ball. Use CVAT interpolation (annotate every 5th frame). Target: 500+ frames | 0.3, 1.2   | 15-25 hours |
| 1.4 | Export annotations (YOLO format)      | CVAT → YOLO `.txt` label files                                                                   | 1.3        | 0.5 hour    |
| 1.5 | Run `validate_annotations.py`         | Check label format, missing labels, bbox sanity                                                  | 1.4        | 0.5 hour    |
| 1.6 | Run `prepare_dataset.py`              | 80/20 train/val split                                                                            | 1.5        | 0.5 hour    |
| 1.7 | Run `augment_motion_blur.py`          | Add motion-blurred variants (~30% of dataset)                                                    | 1.6        | 0.5 hour    |
| 1.8 | Add negative frames                   | ~10% frames with empty label files (no ball visible)                                             | 1.6        | 1 hour      |

**Deliverable:** `datasets/cricket-ball/` has ≥500 annotated frames (train + val), augmented, validated.

**⚠️ This is the most time-consuming milestone.** Annotation is ~20-30 hours of manual work. CVAT's interpolation feature is critical — annotate every 5th frame, let CVAT fill the rest, then correct errors.

---

### M2: Model Training

| #    | Task                                     | Detail                                                                                        | Depends On | Effort                    |
| ---- | ---------------------------------------- | --------------------------------------------------------------------------------------------- | ---------- | ------------------------- |
| 2.1  | Initial training run (50 epochs, M1 MPS) | Quick iteration to validate pipeline and check for issues                                     | M1         | 0.5 day (+ 4-8hr train)   |
| 2.2  | Evaluate with `evaluate.py`              | Check mAP@50 on val set                                                                       | 2.1        | 0.5 hour                  |
| 2.3  | Evaluate with SAHI (`sahi_inference.py`) | Compare SAHI vs non-SAHI accuracy                                                             | 2.1        | 0.5 hour                  |
| 2.4  | Diagnose failures                        | Visualize detections with `visualize.py`. Identify: missed balls, false positives, hard cases | 2.2, 2.3   | 1 day                     |
| 2.5  | Auto-label unlabeled frames              | Run `sahi_inference.py --auto-label`, manually review results in CVAT                         | 2.4        | 2-4 hours                 |
| 2.6  | Retrain with expanded dataset            | Add auto-labeled + corrected frames, retrain 200 epochs                                       | 2.5        | 0.5 day (+ training time) |
| 2.7  | Full training run (cloud GPU)            | 200 epochs on Colab Pro / Lambda / Modal. Use if M1 too slow.                                 | 2.6        | 0.5 day (+ 1-2hr train)   |
| 2.8  | Final evaluation                         | Confirm ≥0.7 mAP@50. If not met → return to 2.4 (more data / augmentation).                   | 2.7        | 0.5 day                   |
| 2.9  | Export model                             | Run `export_model.py` → `cricket_ball_best.pt` (~6 MB)                                        | 2.8        | 0.5 hour                  |
| 2.10 | Also test 1080px single-pass (no SAHI)   | Record the mAP without SAHI — this determines Phase 2 viability                               | 2.8        | 0.5 hour                  |

**Deliverable:** `cricket_ball_best.pt` with ≥0.7 mAP@50. Baseline mAP@50 without SAHI recorded (gates future Phase 2).

**Decision gate after 2.8:** If mAP@50 < 0.5 after two training cycles, reassess: need more data? Different model size? Different augmentation?

---

### M3: Backend Pipeline (FastAPI)

| #    | Task                                          | Detail                                                                       | Depends On | Effort   |
| ---- | --------------------------------------------- | ---------------------------------------------------------------------------- | ---------- | -------- |
| 3.1  | MinIO webhook handler                         | `POST /webhooks/minio` — parse bucket notification, trigger async processing | 0.2        | 0.5 day  |
| 3.2  | Video download from MinIO                     | Pull video from MinIO bucket using boto3 S3 client                           | 3.1        | 0.5 day  |
| 3.3  | Video frame decoder                           | ffmpeg/OpenCV: decode video → frames + extract fps                           | 3.2        | 0.5 day  |
| 3.4  | YOLO + SAHI detection integration             | Integrate `ultralytics` + `sahi` for ball detection per frame                | M2, 3.3    | 1 day    |
| 3.5  | ByteTrack + Kalman tracking                   | Integrate tracking pipeline (reference: `track_demo.py`)                     | 3.4        | 1 day    |
| 3.6  | Physics engine                                | `calculate_speed()` + `classify_pitch_length()` (see ERD §2.5)               | 3.5        | 1.5 days |
| 3.7  | SSE event publishing                          | `sse-starlette` integration: publish progress events during pipeline         | 3.4        | 0.5 day  |
| 3.8  | SSE endpoint                                  | `GET /api/v1/deliveries/{id}/events` — stream events to middleware           | 3.7        | 0.5 day  |
| 3.9  | Update response schema                        | `AnalyzeDeliveryResponse` with trajectory_points, fps, frame_count           | 3.6        | 0.5 day  |
| 3.10 | Auto-delete video from MinIO after processing | Cleanup video after successful/failed analysis                               | 3.6        | 0.5 hour |
| 3.11 | API integration tests                         | pytest: upload test video → verify speed + trajectory output                 | 3.9        | 1 day    |

**Deliverable:** Upload a `.mp4` to MinIO → get speed_kmh + trajectory_points JSON via SSE. Testable with curl/httpie (no Flutter needed).

---

### M3b: Middleware Updates (Spring Boot) — parallel with M3

| #    | Task                            | Detail                                                                          | Depends On | Effort  |
| ---- | ------------------------------- | ------------------------------------------------------------------------------- | ---------- | ------- |
| 3b.1 | MinIO client integration        | Add AWS S3 SDK, configure MinIO credentials                                     | 0.2        | 0.5 day |
| 3b.2 | Upload endpoint                 | `POST /api/v1/deliveries/upload` → generate presigned PUT URL + delivery_id     | 3b.1       | 1 day   |
| 3b.3 | In-memory delivery status store | `ConcurrentHashMap<String, DeliveryStatus>`, TTL 1 hour                         | —          | 0.5 day |
| 3b.4 | SSE relay endpoint              | `GET /api/v1/deliveries/{id}/stream` → relay events from FastAPI                | 3b.3       | 1 day   |
| 3b.5 | Remove old proxy logic          | Delete `DeliveryAnalysisController` multipart proxy, replace with new endpoints | 3b.2, 3b.4 | 0.5 day |
| 3b.6 | Rate limiting                   | `bucket4j` or Spring `@RateLimiter` — prevent abuse                             | 3b.5       | 0.5 day |

**Deliverable:** Middleware serves presigned URLs and relays SSE events. Testable with curl.

---

### M4: Flutter App

| #    | Task                              | Detail                                                                | Depends On | Effort   |
| ---- | --------------------------------- | --------------------------------------------------------------------- | ---------- | -------- |
| 4.1  | Project scaffold                  | Flutter 3.x, folder structure, dependencies, routing                  | —          | 0.5 day  |
| 4.2  | Home screen                       | "Record Delivery" CTA button, camera guidance tips                    | 4.1        | 0.5 day  |
| 4.3  | Camera screen                     | Camera preview, record/stop, framing guide overlay                    | 4.1        | 2 days   |
| 4.4  | Validate 120fps capture           | Test on physical device (iPhone + Android), fallback to 60fps         | 4.3        | 1 day    |
| 4.5  | `DeliveryAnalyzer` abstraction    | Abstract interface + `CloudAnalyzer` implementation (see ERD §2.1)    | 4.1        | 0.5 day  |
| 4.6  | Upload flow (presigned URL)       | Request presigned URL from middleware, upload to MinIO                | 4.5        | 1 day    |
| 4.7  | SSE client                        | Open SSE stream, parse progress + result events                       | 4.6        | 1 day    |
| 4.8  | Processing screen                 | Progress steps UI: "Uploading..." → "Detecting..." → "Calculating..." | 4.7        | 0.5 day  |
| 4.9  | Result screen — speed display     | Large speed number, pitch length classification, confidence indicator | 4.8        | 1 day    |
| 4.10 | Result screen — trajectory replay | VideoPlayer + CustomPaint overlay synced to playback, glowing trail   | 4.9        | 2-3 days |
| 4.11 | Share functionality               | Native share sheet, export result card as PNG                         | 4.9        | 1 day    |
| 4.12 | `OnDeviceAnalyzer` stub           | Placeholder for Phase 2, returns "not available" or feature flag      | 4.5        | 0.5 hour |

**Deliverable:** Flutter app records, uploads, shows progress, displays speed + trajectory overlay, shares.

---

### M5: Integration & Polish

| #   | Task                            | Detail                                                                        | Depends On  | Effort   |
| --- | ------------------------------- | ----------------------------------------------------------------------------- | ----------- | -------- |
| 5.1 | End-to-end test on device       | Physical phone → record → cloud → result. Measure latency.                    | M3, M3b, M4 | 1 day    |
| 5.2 | Latency optimization            | If >15 sec: profile bottleneck (upload? SAHI? physics?) and optimize          | 5.1         | 1-3 days |
| 5.3 | Error handling pass             | Bad video, no ball detected, timeout, network errors → user-friendly messages | 5.1         | 1 day    |
| 5.4 | Camera guidance refinement      | Improve framing overlay based on real-world testing                           | 5.1         | 0.5 day  |
| 5.5 | Speed accuracy validation       | Compare against known speeds (bowling machine if accessible), tune physics    | 5.1         | 1-2 days |
| 5.6 | Video compression before upload | Re-encode to 720p if >30MB to reduce upload time                              | 5.2         | 0.5 day  |

**Deliverable:** System works end-to-end in ≤15 sec. Errors handled gracefully.

---

### M6: Ship MVP

| #   | Task                            | Detail                                                                | Depends On   | Effort                   |
| --- | ------------------------------- | --------------------------------------------------------------------- | ------------ | ------------------------ |
| 6.1 | Deploy FastAPI to cloud GPU     | Modal or GCP Cloud Run (GPU, scale-to-zero)                           | M5           | 1 day                    |
| 6.2 | Deploy middleware               | Railway / Render / GCP Cloud Run (no GPU needed)                      | M5           | 0.5 day                  |
| 6.3 | Deploy MinIO (or switch to S3)  | If staying local: MinIO in Docker on VPS. If scaling: swap to AWS S3. | M5           | 0.5 day                  |
| 6.4 | TestFlight / internal APK       | Build release Flutter app, distribute for testing                     | M5, 6.1, 6.2 | 0.5 day                  |
| 6.5 | Real-world testing              | 5-10 people bowling in nets, collect feedback                         | 6.4          | 3-5 days                 |
| 6.6 | Fix issues from testing         | Bug fixes, accuracy tuning, UX adjustments                            | 6.5          | 2-3 days                 |
| 6.7 | App store submission (optional) | iOS App Store + Google Play                                           | 6.6          | 1-2 days (+ review time) |

**Deliverable:** MVP live, tested by real users in nets.

---

## 4. Dependency Graph

```
M0 (Infra Setup)
 ├──▶ M1 (Dataset)
 │     └──▶ M2 (Model Training)
 │           └──▶ M3 (Backend Pipeline) ──┐
 ├──▶ M3b (Middleware) ───────────────────┤
 │                                         ├──▶ M5 (Integration) ──▶ M6 (Ship)
 └──▶ M4 (Flutter App) ──────────────────┘
```

**Parallelizable work:**

- M3b (Middleware) can start as soon as M0 is done — no model dependency
- M4 (Flutter) can start as soon as M0 is done — mock the API initially
- M3 (Backend) blocks on M2 (trained model), but scaffolding (3.1-3.3, 3.7-3.8) can start earlier with test videos

---

## 5. Risk-Adjusted Timeline

Estimates assume solo developer working part-time (~20-25 hrs/week). Full-time would roughly halve these.

| Milestone                   | Effort (hrs)    | Elapsed Estimate | Critical Risk                                            |
| --------------------------- | --------------- | ---------------- | -------------------------------------------------------- |
| **M0** Infra Setup          | 8-12 hrs        | Week 1           | Low — commodity Docker setup                             |
| **M1** Dataset & Annotation | 25-35 hrs       | Weeks 2-4        | **High** — annotation is tedious; underestimation likely |
| **M2** Model Training       | 15-25 hrs       | Weeks 4-6        | **High** — may need multiple train/annotate cycles       |
| **M3** Backend Pipeline     | 25-35 hrs       | Weeks 5-8        | Medium — standard integration work                       |
| **M3b** Middleware          | 15-20 hrs       | Weeks 3-5        | Low — straightforward REST/SSE                           |
| **M4** Flutter App          | 40-55 hrs       | Weeks 3-8        | Medium — camera/video playback can be tricky             |
| **M5** Integration          | 20-30 hrs       | Weeks 8-10       | Medium — latency optimization may take time              |
| **M6** Ship                 | 15-25 hrs       | Weeks 10-12      | Low — deployment is mechanical                           |
| **Total**                   | **165-240 hrs** | **~10-14 weeks** |                                                          |

**Most likely bottleneck:** M1 → M2 loop. If the model doesn't reach 0.7 mAP after the first training cycle, you'll need more annotation and retraining. Budget 1-2 extra weeks for this.

---

## 6. Phase 2 Preparation (During Phase 1)

These tasks don't block MVP but set up the Phase 2 on-device migration:

| #    | Task                                             | When to Do     | Effort                | Purpose                                |
| ---- | ------------------------------------------------ | -------------- | --------------------- | -------------------------------------- |
| P2.1 | Record mAP@50 without SAHI (1080px single-pass)  | During M2      | Included in 2.10      | Know if Phase 2 is feasible            |
| P2.2 | Build `DeliveryAnalyzer` abstraction in Flutter  | During M4      | Included in 4.5, 4.12 | Clean swap path                        |
| P2.3 | Test CoreML/ONNX export of trained model         | After M2       | 2-4 hours             | Validate export doesn't break accuracy |
| P2.4 | Benchmark YOLO on-device inference speed         | After M4       | 4-8 hours             | Know real latency on target phones     |
| P2.5 | Save sample failed-detection videos from Phase 1 | Ongoing in M5+ | Minimal               | Build retraining dataset               |

**Phase 2 graduation criteria:**

- [ ] mAP@50 ≥ 0.7 at 1080px without SAHI
- [ ] CoreML/ONNX export maintains accuracy (< 5% mAP drop)
- [ ] On-device inference ≤ 25ms per frame on target phones
- [ ] `OnDeviceAnalyzer` implementation complete + tested

---

## 7. Definition of Done (MVP)

The MVP is shippable when ALL of these are true:

- [ ] Record 120fps video on iPhone (fallback 60fps on Android)
- [ ] Upload 3-5 sec video in <5 sec on WiFi
- [ ] Ball detected in ≥80% of frames in delivery arc
- [ ] Speed calculated within ±5 km/h at 120fps (validated against known speeds)
- [ ] Pitch length classified correctly for ≥80% of deliveries
- [ ] Trajectory overlay renders on video replay
- [ ] Result appears within 15 sec of stopping recording (p50)
- [ ] Share button exports result card as image
- [ ] Error case: "Could not detect ball" message when detection fails
- [ ] Cloud infrastructure scales to zero when idle (cost < $5/mo at low usage)
- [ ] Video deleted from MinIO within 1 hour of processing

---

## 8. Immediate Next Actions

Start here:

1. **Run `docker compose up`** with MinIO + existing FastAPI + middleware containers (M0.1-0.2)
2. **Set up CVAT** and import a batch of extracted frames (M0.3)
3. **Extract frames** from downloaded videos (M1.1)
4. **Start annotating** — this is the longest lead-time item and blocks everything downstream (M1.3)
5. **In parallel:** Scaffold Flutter project and build camera screen (M4.1-4.3)
6. **In parallel:** Build middleware presigned URL endpoint with MinIO (M3b.1-3b.2)
