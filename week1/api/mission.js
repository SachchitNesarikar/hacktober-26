// Public endpoint: calls the optional Hugging Face inference API when configured.

export const access = "public";
export const methods = ["POST"];

const pool = {
  move: [
    { icon: "↟", title: "Take the scenic route.", desc: "Head outside for a short walk. Choose a street or path you don't usually take, notice three things you would normally miss, and let your mind wander." },
    { icon: "◒", title: "A tiny mobility reset.", desc: "Find a safe, comfortable spot. Spend a few minutes on gentle ankle circles, hip openers, shoulder rolls and easy stretches. Keep every movement pain-free." },
    { icon: "↗", title: "Walk and think.", desc: "Pick one thing you've been turning over in your head. Walk at an easy pace and think it through without opening a podcast or checking messages." }
  ],
  learn: [
    { icon: "⌘", title: "Solve one thing on paper.", desc: "Choose a small problem or concept you've been learning. Work on paper for one focused session. At the end, explain the key insight in three sentences from memory." },
    { icon: "▤", title: "Read beyond the headline.", desc: "Take a book or printed article somewhere comfortable away from your desk. Read a few pages, then write down one idea that changed or sharpened your thinking." },
    { icon: "◎", title: "Teach an invisible student.", desc: "Pick something you learned recently. Explain it out loud as if teaching a curious beginner. Notice where you get vague, and make that the next thing you study." }
  ],
  grow: [
    { icon: "❋", title: "Notice five small things.", desc: "Step outside and find five details you usually overlook: a plant, a pattern, a sound, a building detail or a change in the light. No photos needed." },
    { icon: "↟", title: "Explore one street over.", desc: "Choose a safe route you rarely take. Walk slowly, find one place or detail you hadn't noticed, and return with a tiny new piece of local knowledge." },
    { icon: "◌", title: "Make something by hand.", desc: "Use what's around you to sketch, write a few lines, arrange a small space or start a tiny creative experiment. Aim for curiosity, not a finished product." }
  ]
};

export default async function (req, res) {
  const body = req.body || {};
  const focus = ["move", "learn", "grow"].includes(body.focus) ? body.focus : "move";
  const minutes = [5, 15, 30].includes(Number(body.minutes)) ? Number(body.minutes) : 15;
  const goal = typeof body.goal === "string" ? body.goal.slice(0, 100).trim() : "";
  const fallback = pool[focus][Math.floor(Math.random() * pool[focus].length)];
  const token = process.env.HF_TOKEN;

  // Optional Hugging Face token enables generation with an open-weight model.
  // The curated fallback keeps the app usable without API credentials.
  if (!token) return res.json({ mission: fallback, source: "fallback" });

  try {
    const response = await fetch("https://router.huggingface.co/v1/chat/completions", {
      method: "POST",
      headers: { Authorization: "Bearer " + token, "Content-Type": "application/json" },
      signal: AbortSignal.timeout(18000),
      body: JSON.stringify({
        model: "google/gemma-3-4b-it",
        messages: [
          { role: "system", content: "You create one safe, achievable real-world micro-mission that reduces screen time. Return only valid JSON with keys icon (one short unicode symbol), title (maximum 7 words), desc (2 short sentences). Do not include markdown. Exercise suggestions must be beginner-friendly and pain-free; no dangerous or inaccessible instructions." },
          { role: "user", content: "Focus: " + focus + ". Time available: " + minutes + " minutes. Personal goal: " + (goal || "none provided") + ". Make it specific, low-friction, and genuinely offline." }
        ],
        max_tokens: 180,
        temperature: 0.8
      })
    });
    if (!response.ok) return res.json({ mission: fallback, source: "fallback" });
    const data = await response.json();
    const raw = data.choices?.[0]?.message?.content || "";
    const cleaned = raw.replace(/^[`\s]*json/i, "").replace(/[`\s]*$/, "");
    const parsed = JSON.parse(cleaned);
    if (typeof parsed.title !== "string" || typeof parsed.desc !== "string" || parsed.title.length > 90 || parsed.desc.length > 500) {
      return res.json({ mission: fallback, source: "fallback" });
    }
    return res.json({
      mission: { icon: typeof parsed.icon === "string" ? parsed.icon.slice(0, 4) : "✳", title: parsed.title, desc: parsed.desc },
      source: "open-model"
    });
  } catch (error) {
    return res.json({ mission: fallback, source: "fallback" });
  }
}
