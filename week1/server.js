import express from "express";
import path from "node:path";
import { fileURLToPath } from "node:url";
import missionHandler from "./api/mission.js";

const app = express();
const root = path.dirname(fileURLToPath(import.meta.url));
const port = process.env.PORT || 3000;

app.use(express.json({ limit: "10kb" }));
app.use(express.static(path.join(root, "public")));

app.get("/healthz", (_req, res) => {
  res.status(200).json({ status: "ok" });
});

app.post("/api/mission", async (req, res) => {
  try {
    await missionHandler(req, res);
  } catch (error) {
    console.error("Mission API error:", error);
    if (!res.headersSent) {
      res.status(500).json({ error: "Could not generate a mission." });
    }
  }
});

app.listen(port, "0.0.0.0", () => {
  console.log(`TouchGrass listening on port ${port}`);
});
