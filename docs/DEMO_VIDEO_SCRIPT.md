# VisualSprint Demo Video Script

**Target length:** ≤ 3 minutes  
**Language:** English with burned-in subtitles (record via OBS/Loom/Xbox Game Bar, add subtitles in CapCut/Descript/YouTube)  
**Reset state before recording:** `POST /api/dev/demo-seed` (or click **Load demo meeting** in `/dev`)

## Recording setup

1. Start the stack:
   ```bash
   npm run dev:api     # http://127.0.0.1:8000
   npm run dev:web     # http://localhost:3000
   ```
2. Open Chrome at `http://localhost:3000` in a clean 1920×1080 window.
3. Reset to a deterministic demo state:
   - Visit `http://localhost:3000/dev`
   - Click **Load demo meeting** (or `curl -X POST http://127.0.0.1:8000/api/dev/demo-seed`)
4. Start screen recorder.

## Shot list & narration

### 0. Landing (0:00–0:20)
- **Visual:** `http://localhost:3000/` — hero, value props, CTA.
- **Narration:** *“VisualSprint turns meetings into structured outcomes. Instead of hunting through notes, it captures live context, extracts decisions, commitments, and blockers, and recommends the next Jira or Slack action.”*
- **Subtitle:** Turn meetings into decisions, commitments, and actions.

### 1. Setup (0:20–0:45)
- **Visual:** Click **Start a meeting** → fill title “Release readiness sync”, 4 participants, notes.
- **Narration:** *“Start by creating a meeting. VisualSprint supports browser live capture, so no desktop install is required.”*
- **Subtitle:** Create a meeting in seconds — no install needed.

### 2. Live session (0:45–1:15)
- **Visual:** `/meetings/{id}/live` — Start capture → allow mic/screen → short animated capture feed.
- **Narration:** *“When the session starts, audio and screen frames are chunked and sent to the ingest pipeline. Speech-to-Text with speaker diarization and Gemini vision frames run in the background.”*
- **Subtitle:** Capture audio + screen; AI extracts transcript and visual signals.

### 3. Demo seed shortcut (1:15–1:25)
- **Visual:** Switch to `/dev` tab, click **Load demo meeting**.
- **Narration:** *“For the hackathon demo I’m using the demo-seed helper, which populates a realistic meeting in under ten seconds.”*
- **Subtitle:** Demo seed loads realistic data instantly.

### 4. Insights & memory (1:25–1:55)
- **Visual:** Meeting detail page → decisions, commitments, blockers, memory match card.
- **Narration:** *“The reasoning agent surfaces a decision to freeze feature work, a commitment from Theo to validate the data fix, and a blocker owned by Avery. It also matches a prior outcome so the team knows this risk was raised before.”*
- **Subtitle:** Decisions, commitments, blockers, and historical memory — automatically.

### 5. Final report (1:55–2:20)
- **Visual:** `/meetings/{id}/report` — executive summary, key takeaways.
- **Narration:** *“Once the session ends, VisualSprint assembles a final report with an executive summary and all structured takeaways.”*
- **Subtitle:** One-click final report with executive summary.

### 6. Action recommendations (2:20–2:50)
- **Visual:** `/meetings/{id}/actions` — Jira create-issue and Slack broadcast cards.
- **Narration:** *“Finally, the action agent recommends concrete next steps: create a high-priority Jira bug for the auth drift, and broadcast the release-freeze decision to Slack. Approve or execute them directly from the portal.”*
- **Subtitle:** Jira + Slack recommendations ready to approve and execute.

### 7. Closing (2:50–3:00)
- **Visual:** Back to landing or GitHub repo.
- **Narration:** *“VisualSprint: capture once, decide clearly, act immediately.”*
- **Subtitle:** Capture once. Decide clearly. Act immediately.

## Upload

1. Export MP4, ≤ 100 MB.
2. Add English subtitles (SRT or burned-in).
3. Upload to YouTube/Vimeo/Loom as unlisted or public.
4. Paste the URL into the Devpost submission.

## Local API reference

```bash
# Reset demo state at any time
curl -X POST http://127.0.0.1:8000/api/dev/demo-seed
```
