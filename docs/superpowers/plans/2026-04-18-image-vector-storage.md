# Image Vector Storage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store labeled image embeddings (1287-float state vectors) in Supabase `image_vectors` table when a user rewards (+R, label=1) or punishes (-P, label=-1) an image; raw JPEG stored to Supabase storage only for +R.

**Architecture:** Pi already computes the full state vector during preprocessing — we include it in the WebSocket payload so the frontend can forward it directly to Supabase without re-computing. A unified `saveToSupabase(label)` helper in the dashboard replaces the existing +R-only upload logic.

**Tech Stack:** Python (Pi WebSocket), Next.js 16 + TypeScript (frontend), Supabase (pgvector + storage)

---

### Task 1: Create `image_vectors` table in Supabase

**Files:**
- No code files — SQL run in Supabase dashboard

- [ ] **Step 1: Enable pgvector extension**

In the Supabase dashboard → SQL Editor, run:
```sql
create extension if not exists vector;
```

- [ ] **Step 2: Create the table**

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

- [ ] **Step 3: Enable RLS and add insert policy**

```sql
alter table image_vectors enable row level security;

create policy "Users can insert their own vectors"
  on image_vectors for insert
  with check (auth.uid() = user_id);

create policy "Users can read their own vectors"
  on image_vectors for select
  using (auth.uid() = user_id);
```

- [ ] **Step 4: Verify**

In Supabase → Table Editor, confirm `image_vectors` appears with correct columns.

---

### Task 2: Add state vector + features to Pi WebSocket payload

**Files:**
- Modify: `picam/pi_server.py` (lines 111–119)

- [ ] **Step 1: Update the image send block to include features and state**

Replace the existing send block (lines 111–119):
```python
if decision == 1:
    with open(current_image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    await websocket.send(json.dumps({
        "type": "image",
        "format": "image/jpeg",
        "data": b64,
        "image_id": image_id
    }))
```

With:
```python
if decision == 1:
    with open(current_image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    await websocket.send(json.dumps({
        "type": "image",
        "format": "image/jpeg",
        "data": b64,
        "image_id": image_id,
        "features": {
            "change_pct":          results['stage_0_5']['change_percentage'],
            "brightness":          results['stage_1']['brightness'],
            "saturation":          results['stage_1']['saturation'],
            "sharpness":           results['stage_1']['sharpness'],
            "edge_count":          results['stage_1']['edge_count'],
            "mean_frequency":      results['stage_1']['mean_frequency'],
            "embedding_magnitude": results['stage_2']['embedding_magnitude'],
        },
        "state": state,
    }))
```

- [ ] **Step 2: Commit**

```bash
git add picam/pi_server.py
git commit -m "feat: include features and state vector in WebSocket image payload"
```

- [ ] **Step 3: Verify on Pi**

Start the server and trigger a capture from the frontend. In the Pi terminal, confirm no errors. In browser DevTools → Network → WS → the image message should now contain `features` and `state` keys.

---

### Task 3: Update frontend to store state vector and save to Supabase on label

**Files:**
- Modify: `frontend/app/dashboard/page.tsx`

- [ ] **Step 1: Add `currentState` and `currentFeatures` state variables**

After the existing `currentImageId` state declaration (around line 57):
```typescript
const [currentImageId, setCurrentImageId]     = useState("");
const [currentState, setCurrentState]         = useState<number[]>([]);
const [currentFeatures, setCurrentFeatures]   = useState<Record<string, number>>({});
```

- [ ] **Step 2: Populate state/features when image is received**

In the WebSocket `onmessage` handler, after `setCurrentImageId(data.image_id)` (around line 83):
```typescript
setCurrentImageId(data.image_id);
setCurrentState(data.state ?? []);
setCurrentFeatures(data.features ?? {});
```

- [ ] **Step 3: Replace the existing Supabase upload block with a unified saveToSupabase helper**

Find and remove the existing block (lines 139–158):
```typescript
if (action === "+R" && user?.id) {
  setUploadStatus("uploading");
  try {
    const storagePath = `${user.id}/${currentImageId}.jpg`;
    const res  = await fetch(capturedImageSrc);
    const blob = await res.blob();
    const { error: storageError } = await supabase.storage
      .from("robocapture-images")
      .upload(storagePath, blob, { contentType: "image/jpeg", upsert: false });
    if (!storageError) {
      await supabase.from("captured_images").insert({
        user_id: user.id, image_id: currentImageId,
        storage_path: storagePath, rl_model: activeModel,
      });
    }
    setUploadStatus(storageError ? "error" : "saved");
  } catch {
    setUploadStatus("error");
  }
}
```

Replace with:
```typescript
if (action !== "skip" && user?.id) {
  setUploadStatus("uploading");
  const label = action === "+R" ? 1 : -1;
  try {
    if (action === "+R") {
      const storagePath = `${user.id}/${currentImageId}.jpg`;
      const res  = await fetch(capturedImageSrc);
      const blob = await res.blob();
      await supabase.storage
        .from("robocapture-images")
        .upload(storagePath, blob, { contentType: "image/jpeg", upsert: false });
    }

    const embedding = currentState.slice(7);   // last 1280 floats
    const { error } = await supabase.from("image_vectors").insert({
      user_id:   user.id,
      image_id:  currentImageId,
      label,
      rl_model:  activeModel,
      embedding: `[${embedding.join(",")}]`,
      features:  currentFeatures,
    });
    setUploadStatus(error ? "error" : "saved");
  } catch {
    setUploadStatus("error");
  }
}
```

- [ ] **Step 4: Update the `sendAction` useCallback dependency array**

The `useCallback` deps array (end of `sendAction`, around line 162) must include the two new state variables:
```typescript
}, [capturedImageSrc, actionTaken, currentImageId, currentState, currentFeatures, user, activeModel]);
```

- [ ] **Step 5: Commit**

```bash
git add frontend/app/dashboard/page.tsx
git commit -m "feat: store labeled embeddings in image_vectors on reward/punishment"
```

- [ ] **Step 6: Verify end-to-end**

1. Start Pi server: `python picam/pi_server.py`
2. Start frontend: `cd frontend && npm run dev`
3. Connect dashboard, click Capture Image
4. Click +R — check Supabase → `image_vectors` for a row with `label=1`
5. Capture again, click -P — check for a row with `label=-1`, confirm no new file in storage bucket
6. Confirm `embedding` column has 1280 values, `features` has the 7 scalar keys

---

### Task 4: Push to main

- [ ] **Step 1: Pull latest and push**

```bash
git pull origin main --rebase
git push origin main
```

- [ ] **Step 2: Pull on Pi**

```bash
# on Pi
cd ~/robocapture
git pull origin main
sudo fuser -k 8765/tcp
python picam/pi_server.py
```
