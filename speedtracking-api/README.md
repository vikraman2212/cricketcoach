# speedtracking-api

Bootstrap FastAPI service for the AI Cricket Coach runtime path.

Current scope:

- Exposes `POST /api/v1/deliveries/analyze` using the multipart contract from the design doc
- Exposes `GET /health` for local integration checks
- Returns deterministic bootstrap telemetry so Flutter and Spring Boot integration can start before CV inference is fully wired

This service does **not** run the actual YOLO, SAHI, ByteTrack, or biomechanics pipeline yet.
It provides the serving boundary and response contract that those components will plug into.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Contract

`POST /api/v1/deliveries/analyze`

Multipart fields:

- `video`: uploaded delivery video
- `configurations`: JSON string with `pitch_length_meters`, `ball_color`, `ball_weight_grams`, `bowling_style`, `bowler_height_cm`

The service also loads defaults from [balltracker_trainer/ball-detector/configs/inference_config.yaml](/Users/viknarasimhan/Documents/aicoach/balltracker_trainer/ball-detector/configs/inference_config.yaml) when fields are omitted.
