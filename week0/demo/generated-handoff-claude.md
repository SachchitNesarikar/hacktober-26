<handoff>
You are taking over an in-progress software project from another AI assistant.
<project>Pocket Ledger</project>
<goal>Pocket Ledger: an offline-first expense tracker PWA that lets Maya (a bakery owner with poor signal at the market) log a cash expense in about 30 seconds.</goal>
<do_not_change>
- Store all money as integer cents, never floats; format only at display
- Do not reorder or rename the CSV columns date,category,amount,note
- Do not reintroduce Workbox or vite-plugin-pwa
- Do not add a CSS framework
</do_not_change>
<constraints>
- Must work fully offline
- Entry must take about 30 seconds on a phone
- Audience is one non-technical user (Maya) on a phone
</constraints>
<user_preferences>
- Keep answers short; the developer reads on a phone
- No TypeScript enums
- No CSS frameworks, plain CSS only
</user_preferences>
<architecture>
- React + Vite single-page PWA with no backend
- Dexie (IndexedDB) is the only data store, table `expenses` indexed on [date+category] and a `recurring` table
- Hand-rolled service worker `public/sw.js` (~40 lines): precache app shell on install, cache-first fetch
</architecture>
<decisions>
- Use Dexie instead of localForage (why: localForage was too slow for monthly queries at 5,000 rows and has no real indexes)
- Use a hand-written service worker instead of Workbox or vite-plugin-pwa (why: Workbox and the plugin both broke with Vite's hashed filenames/build)
- Plain CSS files, no CSS framework (why: developer preference)
- Monthly CSV export lives in src/lib/exportCsv.js with columns date,category,amount,note (why: Maya's accountant has a macro that depends on those exact columns)
</decisions>
<failed_attempts>
- localForage as the storage layer (failed because: slow month queries with 5,000 rows, no index support)
- Workbox generateSW precaching (failed because: conflicts with Vite hashed filenames, blank page after reload)
- vite-plugin-pwa with injectManifest (failed because: manifest injection step throws during build)
</failed_attempts>
<files>
- src/lib/money.js: toCents() and formatCents()
- src/lib/db.js: Dexie database setup
- src/lib/exportCsv.js: monthly CSV export
- public/sw.js: hand-rolled service worker
- src/features/recurring/: recurring expenses form and logic (in progress)
</files>
<recent_changes>
- Replaced localForage with Dexie and rewrote db.js
- Removed Workbox and plugin attempts; added public/sw.js
- Added CSV export with fixed columns
- Added recurring table and basic form
</recent_changes>
<known_bugs>
- Entries made after midnight local time are saved under the previous day because toISOString() uses UTC; fix is to build the date from local date parts (not applied yet)
</known_bugs>
<open_tasks>
- Make editing an existing recurring rule work
- Write a test for recurring rule editing
- Fix the timezone date bug (deprioritised for now)
</open_tasks>
<current_state>Core entry, Dexie storage, offline service worker and CSV export work. Recurring expenses exist as a basic form and table but editing a rule is not implemented and untested.</current_state>
<next_action>Implement updateRecurring(id, patch) in src/lib/db.js and wire up the edit button in src/features/recurring/.</next_action>
<rules>
- Treat DO NOT CHANGE items and decisions as binding unless the developer explicitly reverses them.
- Do not retry anything listed under 'Already tried and failed' without a new reason.
- If something you need is missing from this memory, ask the developer instead of guessing.
- Start by restating the goal and next action in two sentences, then continue the work.
</rules>
</handoff>