**Human:** I'm building Pocket Ledger, an offline-first expense tracker as a PWA for my friend Maya. She runs a small bakery and tracks cash expenses on her phone, often with no signal in the market. I want it usable in 30 seconds per entry. Stack idea: React + Vite + IndexedDB. Thoughts?

**Assistant:** Good fit. React + Vite is fine, IndexedDB is the right store for offline. I'd suggest localForage as a wrapper to keep the code short, and Workbox for the service worker.

**Human:** Let's go with that. One firm rule: money must be stored as integer cents, never floats. Maya's accountant once got rounding errors from another app and she was furious.

**Assistant:** Understood. All amounts are integer cents in storage, formatted only at display. I'll create `src/lib/money.js` with `toCents()` and `formatCents()`.

**Human:** Also I hate TypeScript enums and I don't want any CSS framework. Plain CSS files only. And keep your answers short, I read on my phone.

**Assistant:** Noted: plain CSS, no TS enums, short answers. Here is the data layer in `src/lib/db.js` using localForage with a `expenses` store.

**Human:** Tried it. localForage is making queries by month painfully slow once I seeded 5,000 rows, and there is no real index support. Switching to Dexie instead, it has proper indexes.

**Assistant:** Agreed, Dexie gives compound indexes. Rewriting `db.js` with Dexie: table `expenses` indexed on `[date+category]`. localForage is removed.

**Human:** Now the service worker. Workbox precaching is breaking my Vite hashed filenames in dev, the app shows a blank page after reload.

**Assistant:** Known clash between Workbox's generateSW and Vite's hashing. I'll try `vite-plugin-pwa` with injectManifest.

**Human:** That also failed, the manifest injection step throws on my build and I lost an hour. Let's drop Workbox and plugins entirely and write a tiny hand-rolled service worker: cache-first for the app shell, network-first for nothing since there is no backend.

**Assistant:** Done. `public/sw.js` is ~40 lines: precache `index.html`, JS and CSS on install, cache-first fetch. No Workbox, no plugin.

**Human:** Great. Maya needs the monthly CSV export for her accountant. Columns must stay exactly: date, category, amount, note. Amount is shown in dollars with two decimals in the CSV only. Don't ever reorder or rename those columns, the accountant's spreadsheet macro depends on them.

**Assistant:** CSV export implemented in `src/lib/exportCsv.js` with exactly `date,category,amount,note`. Amounts are formatted from cents.

**Human:** Found a bug: entries made after midnight in her timezone get saved under the previous day, because I used `toISOString()`. Not fixed yet.

**Assistant:** Yes, `toISOString()` is UTC. The fix is to build the date string from local parts. I haven't applied it yet.

**Human:** Leave it for now. Priority is recurring expenses, like rent on the 1st. I added `src/features/recurring/` with a basic form and `recurring` table in Dexie, but editing an existing recurring rule doesn't work yet and there's no test for it.

**Assistant:** OK. Open tasks: edit recurring rules, a test for it, and the timezone bug. Next step is `updateRecurring(id, patch)` in `db.js` plus wiring the edit button.

**Human:** I have to stop for today, I'm out of messages. Next time start with the recurring edit.
