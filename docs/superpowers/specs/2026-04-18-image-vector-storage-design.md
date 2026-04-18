# Image Vector Storage Design
Date: 2026-04-18

## Goal
Store labeled image embeddings in Supabase for offline RL training. Reward images (+R) store both the raw JPEG and vector. Punishment images (-P) store only the vector. Unworthy images (RL model decision = 0) are discarded entirely — never reach the frontend.

## Data Flow

```
Pi captures image
  → preprocessing pipeline (quality filter + MobileNetV2)
  → RL model decides: 0 = discard (no_send), 1 = send
  → If send: WebSocket payload includes base64 JPEG + features dict + full 1287-float state vector
Frontend receives image → displays it
User labels:
  +R → upload raw JPEG to Supabase storage (robocapture-images bucket)
     → insert row into image_vectors (label = 1)
     → send "reward:<image_id>" to Pi
  -P → skip raw image upload
     → insert row into image_vectors (label = -1)
     → send "punishment:<image_id>" to Pi
Pi receives reward/punishment → updates RL model weights
```

## Supabase Schema

```sql
create table image_vectors (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references auth.users,
  image_id    text not null,
  label       int  not null check (label in (1, -1)),
  rl_model    text,
  embedding   vector(1280),
  features    jsonb,
  created_at  timestamptz default now()
);
```

`features` jsonb stores the 7 preprocessed scalars:
- change_pct, brightness, saturation, sharpness, edge_count, mean_frequency, embedding_magnitude

`embedding` stores the 1280-float MobileNetV2 vector (reused directly from Pi — not re-computed).

## Changes Required

### 1. `picam/pi_server.py`
Add `state` and `features` to the WebSocket image payload when decision == 1:
```json
{
  "type": "image",
  "format": "image/jpeg",
  "data": "<base64>",
  "image_id": "<id>",
  "features": { "change_pct": ..., "brightness": ..., ... },
  "state": [1287 floats]
}
```

### 2. `frontend/app/dashboard/page.tsx`
- On image receive: store `data.state` and `data.features` in component state alongside `currentImageId`
- On +R: upload JPEG to storage + insert into `image_vectors` (label=1) + send reward to Pi
- On -P: skip storage upload + insert into `image_vectors` (label=-1) + send punishment to Pi
- Remove the existing +R-only Supabase logic and replace with unified `saveToSupabase(label)` helper

## What Does NOT Change
- RL model update logic on Pi (unchanged)
- WebSocket connection setup (unchanged)
- `captured_images` table (no longer written to — all labeled data goes to `image_vectors`)
- `/api/vectorize` route (unused by this flow — Pi vector is reused directly)
