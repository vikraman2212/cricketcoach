# Engineering Requirements Document: AI Cricket Coach — Speed Gun MVP

**Version:** 1.0  
**Date:** 3 April 2026  
**Status:** Draft for Review  
**Companion:** [PRD_AI_Cricket_Coach_MVP.md](PRD_AI_Cricket_Coach_MVP.md)

---

## 1. System Architecture (MVP)

### Async Processing via MinIO + Webhook + SSE

The architecture uses **MinIO** (S3-compatible object storage) as the video hand-off layer, a **webhook** from MinIO to trigger analysis, and **Server-Sent Events (SSE)** to stream progress/results back to the Flutter client. This decouples upload from processing and avoids streaming large video files through the middleware.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FLUTTER MOBILE APP                                  │
│                                                                             │
│  ┌──────────┐   ┌──────────┐   ┌────────────────┐   ┌──────────────────┐  │
│  │  Camera   │──▶│ Request  │──▶│ Upload video   │──▶│ Open SSE stream  │  │
│  │  Capture  │   │ presigned│   │ direct to MinIO│   │ GET /deliveries/ │  │
│  │  (3-5s,   │   │ URL from │   │ via presigned  │   │   {id}/stream    │  │
│  │  120fps)  │   │ Middleware│   │ PUT URL        │   │                  │  │
│  └──────────┘   └──────────┘   └────────────────┘   └────────┬─────────┘  │
│                                                               │            │
│                       ┌───────────────────────────────────────┘            │
│                       ▼                                                    │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  SSE Events received:                                              │    │
│  │    → { event: "uploaded",    data: "Video received" }              │    │
│  │    → { event: "detecting",   data: "Detecting ball..." }          │    │
│  │    → { event: "tracking",    data: "Tracking trajectory..." }     │    │
│  │    → { event: "calculating", data: "Calculating speed..." }       │    │
│  │    → { event: "complete",    data: {speed_kmh, trajectory, ...} } │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                       │                                                    │
│                       ▼                                                    │
│  ┌───────────────────────────────────┐                                    │
│  │  Render Result + Trajectory       │                                    │
│  │  Overlay via CustomPaint on       │                                    │
│  │  locally-stored video             │                                    │
│  └───────────────────────────────────┘                                    │
└─────────────────────────────────────────────────────────────────────────────┘

 Step 1: Presigned URL           Step 4: SSE stream
 ┌──────────┐                    ┌──────────┐
 │  Flutter  │───GET /upload ───▶│Middleware │◀─── status updates ───┐
 │          │◀── presigned URL──│(Spring)   │───GET /deliveries/{id} │
 └──────────┘                    └──────────┘     /stream (SSE)      │
       │                              │                               │
       │ Step 2: Direct upload        │                               │
       ▼                              │                               │
 ┌──────────┐  Step 3: Webhook  ┌──────────┐                        │
 │  MinIO   │───PUT event ─────▶│ FastAPI  │────────────────────────┘
 │  (S3)    │                   │(speedtrk)│
 │          │◀── GET video ─────│          │
 └──────────┘                   └──────────┘
   Docker                         ┌──────────────────────────────┐
   local                          │ Pipeline:                    │
                                  │  1. Pull video from MinIO    │
                                  │  2. Decode frames (ffmpeg)   │
                                  │  3. YOLO + SAHI detection    │
                                  │  4. ByteTrack + Kalman       │
                                  │  5. Physics engine           │
                                  │  6. Push SSE events          │
                                  │  7. Delete video from MinIO  │
                                  └──────────────────────────────┘
```

### Request Flow (Step by Step)

| Step | Actor   | Action                                     | Detail                                                                                                                      |
| ---- | ------- | ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------- |
| 1    | Flutter | `POST /api/v1/deliveries/upload`           | Sends config (pitch length, ball color). Middleware validates, creates `delivery_id`, returns presigned MinIO PUT URL       |
| 2    | Flutter | `PUT {presigned_url}`                      | Uploads video directly to MinIO bucket `deliveries/{delivery_id}/video.mp4`. Fast — no middleware proxy.                    |
| 3    | MinIO   | Webhook → FastAPI                          | MinIO fires `s3:ObjectCreated:Put` event to `POST /webhooks/minio`. FastAPI receives notification with bucket + object key. |
| 4    | FastAPI | Pull & process                             | Downloads video from MinIO, runs YOLO+SAHI → ByteTrack → physics. Publishes progress events.                                |
| 5    | Flutter | `GET /api/v1/deliveries/{id}/stream` (SSE) | Opens SSE connection through middleware. Receives real-time progress + final result with trajectory data.                   |
| 6    | FastAPI | Cleanup                                    | Deletes video from MinIO after processing. Result JSON stored in memory/Redis (TTL 1 hour).                                 |

### Key Architecture Decisions

| Decision              | Choice                                 | Rationale                                                                                                                                                                                  |
| --------------------- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Video storage         | MinIO (Docker, S3-compatible)          | Free, local, decouples upload from processing. Swap to S3 for prod later — zero code change.                                                                                               |
| Upload method         | Presigned PUT URL (direct to MinIO)    | Flutter uploads directly — no video streaming through middleware. Faster, no timeout risk.                                                                                                 |
| Processing trigger    | MinIO webhook (`s3:ObjectCreated:Put`) | Automatic — no polling. FastAPI processes as soon as video lands.                                                                                                                          |
| Result delivery       | SSE (Server-Sent Events)               | One-way push (server → client). Flutter gets live progress + final result. Simpler than WebSocket.                                                                                         |
| Inference location    | Cloud (FastAPI on GPU) for Phase 1     | Solo dev; SAHI needs GPU; model updates instant; video retained for debugging/retraining. Graduate to on-device (Phase 2) once model achieves ≥0.7 mAP at 1080px single-pass without SAHI. |
| Video overlay         | Client-side (Flutter CustomPaint)      | Don't re-encode video server-side; send trajectory coords, render on phone                                                                                                                 |
| Middleware role       | Orchestration + SSE relay (for MVP)    | Creates delivery, generates presigned URLs, relays SSE from FastAPI to Flutter                                                                                                             |
| No biomechanics model | bowler-pose deferred                   | Speed Gun only needs ball detection, not keypoint estimation                                                                                                                               |
| Single delivery only  | No session/multi-ball logic            | Simplifies detection window + physics calc                                                                                                                                                 |

---

## 2. Component Specifications

### 2.1 Flutter Mobile App (NEW — Not Yet Started)

**Technology:** Flutter 3.x, Dart, `camera` plugin, `video_player`, `CustomPaint`

#### Screens

| Screen         | Purpose                        | Key Widgets                                                                      |
| -------------- | ------------------------------ | -------------------------------------------------------------------------------- |
| **Home**       | "Record Delivery" CTA          | Single button, camera guidance tips                                              |
| **Camera**     | Record delivery video          | Camera preview, record/stop controls, framing guide overlay                      |
| **Processing** | Upload + live progress via SSE | Progress steps: "Uploading..." → "Detecting ball..." → "Calculating speed..."    |
| **Result**     | Speed + replay + share         | Video player with CustomPaint trajectory, speed display, pitch map, share button |

#### DeliveryAnalyzer Abstraction (Phase 1 → Phase 2 Migration)

The Flutter app abstracts the analysis backend behind a `DeliveryAnalyzer` interface. This ensures the UI layer is unchanged when migrating from cloud (Phase 1) to on-device (Phase 2):

```dart
/// Abstract interface — UI depends only on this
abstract class DeliveryAnalyzer {
  Stream<AnalysisEvent> analyze(String videoPath, DeliveryConfig config);
}

/// Phase 1: Cloud via MinIO upload + SSE
class CloudAnalyzer implements DeliveryAnalyzer {
  @override
  Stream<AnalysisEvent> analyze(String videoPath, DeliveryConfig config) async* {
    // 1. Request presigned URL from middleware
    // 2. Upload video to MinIO
    // 3. Open SSE stream for progress + result
    yield AnalysisEvent.progress('Uploading...');
    yield AnalysisEvent.progress('Detecting ball...');
    yield AnalysisEvent.complete(result);
  }
}

/// Phase 2: On-device YOLO + physics (future)
class OnDeviceAnalyzer implements DeliveryAnalyzer {
  @override
  Stream<AnalysisEvent> analyze(String videoPath, DeliveryConfig config) async* {
    // 1. Run YOLO on frames via CoreML (iOS) / ONNX Runtime (Android)
    // 2. Track ball trajectory locally
    // 3. Calculate speed with on-device physics engine
    yield AnalysisEvent.progress('Analyzing...');
    yield AnalysisEvent.complete(result);
  }
}
```

**Selection logic (in DI/provider):**

```dart
DeliveryAnalyzer getAnalyzer() {
  if (featureFlags.onDeviceInference && modelAvailable()) {
    return OnDeviceAnalyzer();
  }
  return CloudAnalyzer();
}
```

**Phase 1 implementation:** Only `CloudAnalyzer` is built. `OnDeviceAnalyzer` is a stub.

**Phase 2 trigger:** Model achieves ≥0.7 mAP@50 at 1080px single-pass inference (no SAHI required). Export to CoreML / ONNX, bundle with app, implement `OnDeviceAnalyzer`.

#### Camera Requirements

| Requirement | Spec                                      | Notes                                                      |
| ----------- | ----------------------------------------- | ---------------------------------------------------------- |
| Frame rate  | 120 fps preferred, 60 fps minimum         | Use `ResolutionPreset.max` or native slow-mo API           |
| Resolution  | 1080p minimum                             | Needed for SAHI to work (ball is <20px at 640px downscale) |
| Duration    | User-controlled (expect 3-5 sec)          | Cap at 15 sec to limit upload size                         |
| Format      | H.264 MP4                                 | Universal codec, good compression                          |
| Orientation | Landscape recommended                     | Pitch is wider than tall. Enforce or guide.                |
| Storage     | Local file, delete after upload confirmed | Don't fill user's gallery                                  |

#### Video Upload (MinIO Presigned URL)

| Requirement    | Spec                                                                      |
| -------------- | ------------------------------------------------------------------------- |
| Method         | 1. `POST /api/v1/deliveries/upload` → get presigned PUT URL + delivery_id |
|                | 2. `PUT {presigned_url}` → upload video directly to MinIO                 |
| Max size       | ~50 MB (15 sec × 1080p × 120fps)                                          |
| Compression    | Consider re-encoding to 720p before upload if >30MB                       |
| Upload timeout | 15 sec (direct to MinIO, no middleware in path)                           |
| Retry          | 1 automatic retry on network failure                                      |
| Progress       | Show upload % in Flutter UI                                               |

#### SSE Stream (Result Delivery)

After upload, Flutter opens an SSE connection to receive live progress and the final result:

```dart
// Flutter pseudocode
final eventSource = EventSource(
  Uri.parse('$baseUrl/api/v1/deliveries/$deliveryId/stream'),
);

eventSource.listen((event) {
  switch (event.event) {
    case 'uploaded':    showProgress('Video received');
    case 'detecting':   showProgress('Detecting ball...');
    case 'tracking':    showProgress('Tracking trajectory...');
    case 'calculating': showProgress('Calculating speed...');
    case 'complete':
      final result = jsonDecode(event.data);
      navigateToResultScreen(result);
    case 'error':
      showError(event.data);
  }
});
```

**SSE Events:**

| Event         | Data                                | When                  |
| ------------- | ----------------------------------- | --------------------- |
| `uploaded`    | `"Video received"`                  | MinIO webhook fires   |
| `detecting`   | `"Detecting ball in N frames..."`   | YOLO+SAHI starts      |
| `tracking`    | `"Tracking trajectory..."`          | ByteTrack starts      |
| `calculating` | `"Calculating speed..."`            | Physics engine starts |
| `complete`    | Full `AnalyzeDeliveryResponse` JSON | Done                  |
| `error`       | Error message string                | Processing failed     |

#### Trajectory Overlay Rendering

The server returns trajectory data as an array of normalized (0-1) coordinates:

```json
{
  "trajectory_points": [
    {"frame": 42, "x": 0.51, "y": 0.23, "confidence": 0.92},
    {"frame": 43, "x": 0.52, "y": 0.31, "confidence": 0.88},
    ...
  ],
  "fps": 120,
  "frame_count": 420
}
```

Flutter renders this by:

1. Playing the original local video file in `VideoPlayer`
2. Overlaying a `CustomPaint` widget synchronized to video playback position
3. Drawing trajectory line/trail up to the current frame
4. Style: glowing trail with fade (exact visual TBD during Flutter dev)

---

### 2.2 Spring Boot Middleware (EXISTS — Needs Rework for MinIO/SSE)

**Current state:** Proxy endpoint forwards multipart to FastAPI (will be replaced).

#### MVP Changes Needed

| Change                                                               | Priority | Effort | Detail                                                                               |
| -------------------------------------------------------------------- | -------- | ------ | ------------------------------------------------------------------------------------ |
| **Upload endpoint** — `POST /api/v1/deliveries/upload`               | Must     | Medium | Validate config, create delivery_id, generate MinIO presigned PUT URL, return both   |
| **SSE relay endpoint** — `GET /api/v1/deliveries/{id}/stream`        | Must     | Medium | Open SSE connection to Flutter. Relay events from FastAPI (or in-memory event bus).  |
| **MinIO client integration** (AWS SDK / `software.amazon.awssdk:s3`) | Must     | Small  | Presigned URL generation. Configure MinIO endpoint + credentials.                    |
| **In-memory delivery status store**                                  | Must     | Small  | `ConcurrentHashMap<String, DeliveryStatus>`. TTL 1 hour. No database needed for MVP. |
| Video validation (max size check in presigned URL policy)            | Must     | Small  | Set max content-length in presigned URL conditions                                   |
| Rate limiting (prevent abuse of free tier)                           | Should   | Small  | Spring `@RateLimiter` or bucket4j                                                    |
| Remove old `DeliveryAnalysisController` proxy logic                  | Must     | Small  | Replace with new upload + SSE endpoints                                              |

#### SSE Implementation (Spring Boot)

```java
@GetMapping(value = "/api/v1/deliveries/{id}/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
public SseEmitter streamDeliveryStatus(@PathVariable String id) {
    SseEmitter emitter = new SseEmitter(60_000L); // 60s timeout
    deliveryEventService.subscribe(id, emitter);
    return emitter;
}
```

#### MinIO Presigned URL Generation

```java
@PostMapping("/api/v1/deliveries/upload")
public UploadResponse createDelivery(@RequestBody UploadRequest config) {
    String deliveryId = UUID.randomUUID().toString();
    String objectKey = "deliveries/" + deliveryId + "/video.mp4";

    String presignedUrl = minioClient.getPresignedObjectUrl(
        GetPresignedObjectUrlArgs.builder()
            .bucket("deliveries")
            .object(objectKey)
            .method(Method.PUT)
            .expiry(5, TimeUnit.MINUTES)
            .build()
    );

    deliveryStore.put(deliveryId, new DeliveryStatus("pending", config));
    return new UploadResponse(deliveryId, presignedUrl);
}
```

#### No Changes Needed (Deferred)

- Database / JPA entities (in-memory store is fine for MVP)
- Auth / session management (anonymous free tier)
- Onboarding controller (deferred to Pro)
- Subscription routing (deferred to Pro)

---

### 2.3 FastAPI Speed Tracking API (EXISTS — Needs Real Inference + MinIO + SSE)

**Current state:** Bootstrap mock service returns hardcoded speeds. Must be replaced with actual ML pipeline triggered by MinIO webhook.

#### New Endpoints

| Endpoint                         | Method    | Purpose                                                                                 |
| -------------------------------- | --------- | --------------------------------------------------------------------------------------- |
| `/webhooks/minio`                | POST      | Receives MinIO bucket notification. Triggers async analysis.                            |
| `/api/v1/deliveries/{id}/status` | GET       | Returns current processing status + result (if complete). Used by middleware SSE relay. |
| `/api/v1/deliveries/{id}/events` | GET (SSE) | Direct SSE stream of processing events. Middleware can relay this.                      |

#### MinIO Webhook Handler

```python
@app.post("/webhooks/minio")
async def minio_webhook(notification: dict, background_tasks: BackgroundTasks):
    """Triggered by MinIO s3:ObjectCreated:Put event."""
    records = notification.get("Records", [])
    for record in records:
        bucket = record["s3"]["bucket"]["name"]
        object_key = record["s3"]["object"]["key"]  # "deliveries/{id}/video.mp4"
        delivery_id = object_key.split("/")[1]

        # Run analysis in background (don't block webhook response)
        background_tasks.add_task(analyze_delivery_async, delivery_id, bucket, object_key)

    return {"status": "accepted"}
```

#### Async Analysis Pipeline (replaces old synchronous flow)

```python
async def analyze_delivery_async(delivery_id: str, bucket: str, object_key: str):
    try:
        # Publish SSE: "uploaded"
        publish_event(delivery_id, "uploaded", "Video received")

        # 1. Pull video from MinIO
        video_path = download_from_minio(bucket, object_key)

        # 2. Decode video to frames
        frames = decode_video(video_path)
        fps = get_video_fps(video_path)

        # Publish SSE: "detecting"
        publish_event(delivery_id, "detecting", f"Detecting ball in {len(frames)} frames...")

        # 3. Ball detection (YOLO + SAHI)
        detections = []
        for frame in frames:
            dets = sahi_predict(model=yolo_model, image=frame, ...)
            detections.append(dets)

        # Publish SSE: "tracking"
        publish_event(delivery_id, "tracking", "Tracking trajectory...")

        # 4. Ball tracking (ByteTrack + Kalman)
        trajectory = track_ball(detections, frame_width, frame_height)
        trajectory = kalman_interpolate(trajectory, max_gap=3)

        # Publish SSE: "calculating"
        publish_event(delivery_id, "calculating", "Calculating speed...")

        # 5. Physics calculation
        result = calculate_physics(trajectory, fps, config)

        # Publish SSE: "complete" with full result
        publish_event(delivery_id, "complete", result.model_dump_json())

        # 6. Cleanup: delete video from MinIO
        delete_from_minio(bucket, object_key)

    except Exception as e:
        publish_event(delivery_id, "error", str(e))
```

    pitch_length = classify_pitch_length(pitch_point, config.pitch_length_meters)

    # 6. Return results
    return {
        "delivery_id": uuid4(),
        "speed_kmh": round(speed_kmh, 1),
        "speed_confidence": calculate_confidence(trajectory),
        "pitch_length": pitch_length,  # "full" | "good" | "short" | "bouncer"
        "trajectory_points": trajectory,
        "fps": fps,
        "frame_count": len(frames)
    }

````

#### Updated API Response Schema

The current `AnalyzeDeliveryResponse` in [schemas.py](../speedtracking-api/app/schemas.py) needs to be extended:

```python
class TrajectoryPoint(BaseModel):
    frame: int
    x: float          # 0.0 - 1.0 (normalized to video width)
    y: float          # 0.0 - 1.0 (normalized to video height)
    confidence: float  # 0.0 - 1.0

class DeliveryPhysics(BaseModel):
    speed_kmh: float
    speed_confidence: float       # 0.0 - 1.0 (NEW)
    pitch_length: str             # "full" | "good" | "short" | "bouncer"

class AnalyzeDeliveryResponse(BaseModel):
    delivery_id: str
    delivery_physics: DeliveryPhysics
    trajectory_points: list[TrajectoryPoint]   # NEW — for client-side overlay
    fps: float                                  # NEW — video frame rate
    frame_count: int                            # NEW — total frames in video
    processing_time_ms: int                     # NEW — server-side latency
````

**Removed from MVP response** (deferred to Pro):

- `biomechanics` block (no pose model)
- `system_evaluations` block (no AI coaching)
- `deviation` block (swing analysis)

#### New Dependencies

Add to [requirements.txt](../speedtracking-api/requirements.txt):

```
ultralytics>=8.3        # YOLOv11 inference
sahi>=0.11              # Slicing Aided Hyper Inference
lap>=0.4                # ByteTrack linear assignment
filterpy>=1.4           # Kalman filter
opencv-python>=4.8      # Video decoding, frame processing
numpy>=1.24             # Array operations
boto3>=1.34             # MinIO/S3 client (S3-compatible API)
sse-starlette>=2.0      # SSE support for FastAPI
```

#### Model Loading

```python
# On startup — load once, reuse for all requests
from ultralytics import YOLO

MODEL_PATH = os.getenv("BALL_DETECTOR_MODEL", "models/cricket_ball_best.pt")
yolo_model = YOLO(MODEL_PATH)
```

Model file (`cricket_ball_best.pt`) must be:

1. Trained via `balltracker_trainer/ball-detector/scripts/train.py`
2. Placed in `speedtracking-api/models/` or provided via environment variable
3. ~6 MB (YOLOv11n)

---

### 2.4 ML Model Training (EXISTS — Needs Execution)

**Only the ball-detector model is needed for MVP.** Bowler-pose is deferred to Pro tier.

#### Training Plan: Ball Detector (YOLOv11n)

| Stage             | Task                                                     | Tool                         | Output                                        |
| ----------------- | -------------------------------------------------------- | ---------------------------- | --------------------------------------------- |
| 1. Extract frames | Run `extract_frames.py` on downloaded videos             | `balltracker_trainer/tools/` | PNG frames in `datasets/cricket-ball/images/` |
| 2. Annotate       | Draw bounding boxes around ball in CVAT                  | CVAT (Docker local)          | YOLO `.txt` label files                       |
| 3. Validate       | Run `validate_annotations.py`                            | `ball-detector/data/`        | Clean dataset                                 |
| 4. Augment        | Run `augment_motion_blur.py`                             | `ball-detector/data/`        | Motion-blurred variants                       |
| 5. Train          | Run `train.py`                                           | `ball-detector/scripts/`     | `best.pt` model weights                       |
| 6. Evaluate       | Run `evaluate.py` + `sahi_inference.py`                  | `ball-detector/scripts/`     | mAP metrics                                   |
| 7. Auto-label     | Run `sahi_inference.py --auto-label` on unlabeled frames | `ball-detector/scripts/`     | More label files → repeat from step 3         |

#### Training Hardware Options

| Option                | Cost                 | Training Time (200 epochs, ~1000 images) | Recommendation                            |
| --------------------- | -------------------- | ---------------------------------------- | ----------------------------------------- |
| **M1 MacBook (MPS)**  | Free                 | ~4-8 hours                               | Fine for experimentation; slower          |
| **Google Colab Free** | Free                 | ~2-3 hours (T4 GPU)                      | Good for initial training; session limits |
| **Google Colab Pro**  | $10/mo               | ~1-2 hours (A100)                        | Best value for serious training           |
| **Lambda Labs**       | ~$1.10/hr (A10G)     | ~1 hour                                  | Best for repeated runs; pay-per-use       |
| **RunPod**            | ~$0.44/hr (RTX 3090) | ~1-1.5 hours                             | Budget cloud GPU                          |

**Recommendation:** Start on M1 MPS for rapid iteration (small dataset, 50 epochs). Move to Colab Pro or Lambda for the full 200-epoch production training run.

#### Annotation Tool: CVAT (Local Docker)

For your case (solo developer, bounding boxes for ball, need local/private):

```bash
# One-time setup
docker compose -f docker-compose.yml up -d

# Access at http://localhost:8080
# Create project → Import images → Draw bboxes → Export YOLO format
```

**Why CVAT over alternatives:**

- **Free & local** (Docker) — your video data stays private
- **YOLO export built-in** — direct `.txt` label output
- **Supports both bbox (ball) AND keypoint (future pose)** annotation
- **Interpolation** — annotate every 5th frame, CVAT interpolates between (huge time saver for ball tracking)

**Alternative:** Label Studio (also Docker-local, simpler UI but less interpolation support).

#### Dataset Requirements

| Attribute       | Target                       | Current                           |
| --------------- | ---------------------------- | --------------------------------- |
| Total frames    | ≥500 annotated (1000+ ideal) | 0                                 |
| Ball colors     | Red (primary), white, pink   | Videos downloaded (not extracted) |
| Camera angle    | Behind stumps only           | Filtered in video_catalog.yaml    |
| Negative frames | ~10% with empty label files  | TBD                               |
| Motion blur     | ~30% of frames               | Augmentation script ready         |
| Red distractors | Present in training data     | Depends on video content          |
| Train/val split | 80/20                        | Automatic in prepare_dataset.py   |

---

### 2.5 Physics Engine (NEW — Must Build)

Core calculation: convert pixel-space ball trajectory to real-world speed.

#### Calibration Approach (Monocular Camera)

With a single phone camera (no stereo vision or LiDAR), we need reference points to establish pixel-to-meter mapping:

**Option A — Pitch-length calibration (Recommended for MVP):**

1. User frames the pitch from behind stumps
2. We know the pitch is 20.12m (standard) or 16m (junior) — configurable
3. Detect the two sets of stumps (or ask user to mark them) to establish the pixel distance for 20.12m
4. All subsequent distance calculations use this ratio

**Option B — Stump-height calibration:**

1. Stumps are 71.1cm tall (standard)
2. Detect stump height in pixels → establish scale
3. Less accurate because stumps are far from ball trajectory plane

**Recommendation:** Option A. User provides `pitch_length_meters` in config (defaults to 20.12). If we can auto-detect stump positions, we calibrate automatically. Otherwise, a one-time manual calibration step.

#### Speed Calculation

```python
def calculate_speed(
    release_point: TrajectoryPoint,
    pitch_point: TrajectoryPoint,
    fps: float,
    pixel_scale: float,  # meters per pixel (from calibration)
) -> tuple[float, float]:
    """
    Returns (speed_kmh, confidence).

    Uses straight-line approximation for MVP.
    Future: parabolic trajectory fitting for gravity correction.
    """
    # Time between release and pitching
    frame_delta = pitch_point.frame - release_point.frame
    time_seconds = frame_delta / fps

    if time_seconds <= 0:
        raise ValueError("Invalid trajectory: pitch before release")

    # Pixel distance
    dx = (pitch_point.x - release_point.x) * frame_width
    dy = (pitch_point.y - release_point.y) * frame_height
    pixel_distance = math.sqrt(dx**2 + dy**2)

    # Convert to meters
    real_distance = pixel_distance * pixel_scale

    # Speed
    speed_mps = real_distance / time_seconds
    speed_kmh = speed_mps * 3.6

    # Confidence based on trajectory completeness and detection quality
    detection_rate = len(trajectory) / frame_delta
    avg_confidence = mean(t.confidence for t in trajectory)
    confidence = min(detection_rate, 1.0) * avg_confidence

    return speed_kmh, confidence
```

#### Pitch Length Classification

```python
def classify_pitch_length(pitch_y_normalized: float, pitch_length_meters: float) -> str:
    """
    Classify where the ball landed relative to the batting crease.
    pitch_y_normalized: 0.0 = bowler's end, 1.0 = batsman's end
    """
    # Distance from batsman's crease (in meters)
    distance_from_batsman = (1.0 - pitch_y_normalized) * pitch_length_meters

    if distance_from_batsman < 2.0:
        return "yorker"
    elif distance_from_batsman < 4.0:
        return "full"
    elif distance_from_batsman < 6.5:
        return "good"
    elif distance_from_batsman < 9.0:
        return "short"
    else:
        return "bouncer"
```

---

## 3. Infrastructure (MVP)

### MinIO (Object Storage — Docker Local)

```yaml
# docker-compose.yml (dev)
services:
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000" # S3 API
      - "9001:9001" # Web console
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - minio-data:/data

volumes:
  minio-data:
```

**Setup after first start:**

1. Create bucket: `deliveries`
2. Configure webhook: MinIO → `POST http://speedtracking-api:8000/webhooks/minio` on `s3:ObjectCreated:Put`
3. Set bucket lifecycle: auto-delete objects older than 1 hour (cleanup failed processing)

**MinIO webhook config (via mc CLI):**

```bash
mc alias set local http://localhost:9000 minioadmin minioadmin
mc mb local/deliveries
mc event add local/deliveries arn:minio:sqs::1:webhook --event put
```

**Production swap:** Change MinIO endpoint to AWS S3 / GCP Cloud Storage. Zero application code change (S3-compatible API).

### Cloud Inference Server

| Attribute | Spec                                         | Notes                                           |
| --------- | -------------------------------------------- | ----------------------------------------------- |
| Provider  | GCP Cloud Run (GPU) or AWS EC2 (g4dn.xlarge) | See options below                               |
| GPU       | NVIDIA T4 (minimum)                          | Needed for SAHI (many forward passes per frame) |
| Memory    | 8 GB+                                        | YOLO model + video frames in memory             |
| Storage   | Ephemeral (process & discard video)          | No persistent storage for MVP                   |
| Scaling   | 0-to-1 (scale to zero when idle)             | Critical for solo dev cost control              |

#### Cloud Options (Cost Comparison)

| Provider                | Service         | GPU        | Cost (idle)      | Cost (active) | Scale-to-zero    |
| ----------------------- | --------------- | ---------- | ---------------- | ------------- | ---------------- |
| **GCP Cloud Run**       | GPU containers  | L4/T4      | $0               | ~$0.60/hr     | Yes              |
| **AWS Lambda**          | Container image | None (CPU) | $0               | ~$0.001/req   | Yes — but no GPU |
| **AWS EC2 g4dn.xlarge** | VM              | T4         | ~$0.53/hr always | Same          | No               |
| **Railway/Render**      | Container       | None (CPU) | $5/mo            | Included      | Yes — but no GPU |
| **Modal**               | Serverless GPU  | T4/A10G    | $0               | ~$0.58/hr     | Yes              |
| **Replicate**           | Model hosting   | T4/A40     | $0               | ~$0.55/hr     | Yes              |

**Recommendation:**

- **Development/Testing:** Run on M1 MacBook (CPU mode, slower but free)
- **Production MVP:** **Modal** or **GCP Cloud Run with GPU** — both scale to zero (you pay $0 when nobody is using it), spin up in <10 sec, and support custom Docker images with YOLO + SAHI

### Docker Deployment (Full Dev Stack)

```yaml
# docker-compose.yml (complete dev environment)
services:
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
      MINIO_NOTIFY_WEBHOOK_ENABLE_PRIMARY: "on"
      MINIO_NOTIFY_WEBHOOK_ENDPOINT_PRIMARY: "http://speedtracking-api:8000/webhooks/minio"
    volumes:
      - minio-data:/data

  speedtracking-api:
    build: ./speedtracking-api
    ports:
      - "8000:8000"
    environment:
      BALL_DETECTOR_MODEL: /models/cricket_ball_best.pt
      MINIO_ENDPOINT: http://minio:9000
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
    volumes:
      - ./speedtracking-api/models:/models
    depends_on:
      - minio

  middleware:
    build: ./middleware
    ports:
      - "8080:8080"
    environment:
      MINIO_ENDPOINT: http://minio:9000
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
      MINIO_PUBLIC_ENDPOINT: http://localhost:9000 # For presigned URLs accessible from Flutter
      SPEEDTRACKING_SERVICE_BASE_URL: http://speedtracking-api:8000
    depends_on:
      - minio
      - speedtracking-api

volumes:
  minio-data:
```

```dockerfile
# speedtracking-api/Dockerfile (MVP)
FROM nvidia/cuda:12.1-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y python3 python3-pip ffmpeg
COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY app/ /app/
COPY models/ /models/

ENV BALL_DETECTOR_MODEL=/models/cricket_ball_best.pt
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Middleware Deployment

The Spring Boot middleware can run on any cheap container platform (no GPU needed):

- **Railway** ($5/mo), **Render** (free tier), or **GCP Cloud Run** (free tier)
- Handles rate limiting, validation, forward to FastAPI GPU service

---

## 4. API Contract (Updated for MVP — MinIO + SSE)

### POST /api/v1/deliveries/upload (Middleware)

Creates a delivery and returns a presigned MinIO URL for direct video upload.

**Request** (application/json):

```json
{
  "pitch_length_meters": 20.12,
  "ball_color": "red",
  "bowling_style": "fast"
}
```

**Response** (201 Created):

```json
{
  "delivery_id": "a1b2c3d4-...",
  "upload_url": "http://minio:9000/deliveries/a1b2c3d4-.../video.mp4?X-Amz-...",
  "upload_expires_in_seconds": 300
}
```

### PUT {upload_url} (Direct to MinIO)

Flutter uploads video directly to MinIO. No middleware in the path.

**Request**: Raw MP4 binary, `Content-Type: video/mp4`  
**Response**: 200 OK (MinIO standard S3 response)

### GET /api/v1/deliveries/{id}/stream (Middleware → SSE)

Server-Sent Events stream. Opened by Flutter after upload completes.

**Response** (text/event-stream):

```
event: uploaded
data: Video received

event: detecting
data: Detecting ball in 420 frames...

event: tracking
data: Tracking trajectory...

event: calculating
data: Calculating speed...

event: complete
data: {"delivery_id":"a1b2c3d4-...","delivery_physics":{"speed_kmh":127.3,"speed_confidence":0.85,"pitch_length":"good"},"trajectory_points":[{"frame":42,"x":0.51,"y":0.12,"confidence":0.91},{"frame":43,"x":0.52,"y":0.18,"confidence":0.89}],"fps":120.0,"frame_count":420,"processing_time_ms":3240}
```

### POST /webhooks/minio (FastAPI — Internal Only)

Called by MinIO when a video is uploaded. Not exposed externally.

**Request** (MinIO bucket notification format):

```json
{
  "Records": [
    {
      "s3": {
        "bucket": { "name": "deliveries" },
        "object": { "key": "deliveries/a1b2c3d4-.../video.mp4" }
      }
    }
  ]
}
```

**Response**: 200 `{"status": "accepted"}`

### Error Responses

```json
// 400 — Bad request (on /upload)
{"detail": "pitch_length_meters must be between 10.0 and 25.0"}

// 404 — Delivery not found (on /stream)
{"detail": "Delivery a1b2c3d4 not found"}

// SSE error event (during processing)
event: error
data: Could not detect ball in video. Ensure the ball is visible and the camera is behind the stumps.
```

---

## 5. Non-Functional Requirements

| Requirement          | Target                                                                | Notes                                                                                                       |
| -------------------- | --------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| **Latency**          | ≤15 sec end-to-end (record stop → result)                             | Phase 1: Upload ~3-5s (direct to MinIO) + inference ~8s + SSE <1s. Phase 2: <5 sec (no upload).             |
| **Availability**     | Best effort (solo dev project)                                        | Phase 1: Scale-to-zero means cold starts (~10-15 sec first request). Phase 2: Always available (on-device). |
| **Video size**       | ≤50 MB per upload                                                     | 15 sec × 1080p × 120fps ≈ 45MB                                                                              |
| **Concurrent users** | 1-5 (MVP)                                                             | Single GPU instance sufficient                                                                              |
| **Data retention**   | Video deleted from MinIO after processing (auto-expire 1hr lifecycle) | No persistent video storage                                                                                 |
| **Privacy**          | No PII collected in MVP (anonymous)                                   | GDPR-ready: no accounts, no tracking                                                                        |

---

## 6. Testing Strategy

| Test Type               | Scope                                 | Tool                                |
| ----------------------- | ------------------------------------- | ----------------------------------- |
| **ML model evaluation** | mAP@50 ≥ 0.7 on val set               | `evaluate.py` + `sahi_inference.py` |
| **Speed accuracy**      | ±5 km/h vs radar gun (if available)   | Manual validation with known speeds |
| **API integration**     | Upload video → get trajectory + speed | pytest + httpx                      |
| **Video processing**    | Various fps, resolutions, durations   | Test videos corpus                  |
| **Flutter UI**          | Camera → upload → result flow         | Flutter integration tests           |
| **End-to-end**          | Record on phone → see result          | Manual on physical device           |

---

## 7. What Exists vs What Must Be Built

### Already Built (Can Reuse)

| Component                       | Location                                      | Status           | MVP Usage                             |
| ------------------------------- | --------------------------------------------- | ---------------- | ------------------------------------- |
| Ball detector training pipeline | `balltracker_trainer/ball-detector/`          | Scripts complete | Train the model                       |
| Video download tools            | `balltracker_trainer/tools/`                  | Working          | Download training videos              |
| Frame extraction                | `balltracker_trainer/tools/extract_frames.py` | Working          | Extract training frames               |
| Data augmentation (motion blur) | `ball-detector/data/augment_motion_blur.py`   | Written          | Augment training data                 |
| Annotation validation           | `ball-detector/data/validate_annotations.py`  | Written          | Validate labels                       |
| SAHI inference script           | `ball-detector/scripts/sahi_inference.py`     | Written          | Evaluate model + auto-label           |
| ByteTrack tracking demo         | `ball-detector/scripts/track_demo.py`         | Written          | Reference for tracking integration    |
| FastAPI endpoint structure      | `speedtracking-api/app/`                      | Bootstrap mock   | Rework for MinIO webhook + SSE events |
| Spring Boot middleware          | `middleware/`                                 | Proxy working    | Rework for presigned URLs + SSE relay |
| Model export                    | `ball-detector/scripts/export_model.py`       | Written          | Export trained model                  |

### Must Build (New)

| Component                                                    | Effort                   | Dependency                   |
| ------------------------------------------------------------ | ------------------------ | ---------------------------- |
| **Annotated training dataset**                               | ~20-40 hours of labeling | Frames extracted from videos |
| **Trained ball detector model**                              | ~4-8 hours training (M1) | Annotated dataset            |
| **MinIO webhook handler** in FastAPI                         | ~1 day                   | MinIO Docker setup           |
| **Real inference pipeline** in FastAPI (YOLO+SAHI+ByteTrack) | ~2-3 days                | Trained model                |
| **SSE event publishing** in FastAPI                          | ~0.5 day                 | Event pipeline               |
| **Physics engine** (speed calc + pitch classification)       | ~2-3 days                | Working inference            |
| **Presigned URL endpoint** in middleware                     | ~0.5 day                 | MinIO client library         |
| **SSE relay endpoint** in middleware                         | ~1 day                   | FastAPI SSE working          |
| **Docker Compose** (MinIO + FastAPI + Middleware)            | ~1 day                   | All services                 |
| **Flutter mobile app**                                       | ~2-3 weeks               | API contract finalized       |

### Not Needed for MVP (Defer)

| Component                              | Deferred To        | Current Status                               |
| -------------------------------------- | ------------------ | -------------------------------------------- |
| Bowler-pose training pipeline          | Pro tier (Phase 3) | Scripts exist, don't train yet               |
| Database schema / JPA entities         | Pro tier           | JPA configured, no entities                  |
| Auth / user accounts                   | Pro tier           | Not started                                  |
| AI Coach chat (LLM)                    | Pro tier           | Not started                                  |
| Swing/seam analysis                    | Pro tier           | Not started                                  |
| Flutter web dashboard                  | Academy tier       | Not started                                  |
| Onboarding flow                        | Pro tier           | Empty controller exists                      |
| On-device YOLO inference (CoreML/ONNX) | Phase 2            | `OnDeviceAnalyzer` stub in Flutter           |
| On-device physics engine (Dart)        | Phase 2            | Physics logic exists server-side, port later |

---

## 8. Platform Evolution Roadmap

The architecture evolves across three phases. Each phase is self-contained and shippable.

### Phase 1: Cloud Speed Gun (MVP — current)

```
[ Flutter ] ──upload──▶ [ MinIO ] ──webhook──▶ [ FastAPI + YOLO + SAHI ] ──SSE──▶ [ Flutter ]
```

- **Why cloud:** Model unproven; need video for debugging/retraining; SAHI GPU-bound
- **Video retained:** Failed detections → download video → analyze → retrain model
- **Exit criteria:** Ball detector ≥0.7 mAP@50 on validation set

### Phase 2: On-Device Speed Gun

```
[ Flutter ] ──frames──▶ [ CoreML / ONNX Runtime ] ──trajectory──▶ [ Dart Physics Engine ] ──result──▶ [ Flutter ]
```

- **Graduation criteria:** Model achieves ≥0.7 mAP@50 at 1080px single-pass (no SAHI)
- **What changes:**
  - Export trained YOLOv11n to CoreML (iOS) + ONNX (Android)
  - Implement `OnDeviceAnalyzer` in Flutter (see §2.1)
  - Port physics engine from Python to Dart (or call via Flutter FFI)
  - MinIO / webhook / SSE infrastructure becomes optional (keep for fallback)
- **On-device inference budget (3-sec delivery at 120fps = 360 frames):**
  - Keyframe strategy: analyze every 3rd frame → ~120 YOLO passes
  - YOLOv11n at 1080px on iPhone 14 (CoreML): ~15-25ms per pass
  - Total: ~2-3 sec inference + ~0.5 sec physics = **<5 sec total**
- **Video never leaves the phone** → eliminates privacy concerns
- **Works offline** → usable at nets without WiFi

### Phase 3: Biomechanics Pro (Hybrid)

```
[ Flutter ] ──on-device ball──▶ [ Speed result ]
                                             └──upload video (opt-in)──▶ [ Cloud Pose Model ] ──SSE──▶ [ Flutter skeletal overlay ]
```

- **Ball detection:** On-device (Phase 2 path)
- **Pose estimation:** Cloud — YOLOv11s-Pose too large for most phones (~40MB, slow inference)
- **Monetized:** Pro tier subscription covers GPU cost
- **Video upload is opt-in** — only for biomechanics analysis, not speed
