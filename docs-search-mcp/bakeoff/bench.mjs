// Bake-off of this search against QMD (brain/ARCHITECTURE.md, "Bake-off"). Setup, from docs-search-mcp/:
//   mkdir -p work/qmd && cd work/qmd && npm init -y && npm install @tobilu/qmd@2.8.3
//   export the library as markdown (one file per document, see ARCHITECTURE), npx qmd init,
//   npx qmd collection add corpus --name lib, npx qmd embed --timeout 0      (hours for the full library)
// Run:  cp ../../bakeoff/bench.mjs . && node bench.mjs <mode> ../../tests/<set>.json > qmd.json
//       python3 ../../bakeoff/ours.py ../../tests/<set>.json > ours.json
//       python3 ../../bakeoff/score.py ../../tests/<set>.json qmd.json ../index/docs.db   (and ours.json)
// mode: lex | vec | hybrid | hybrid-norerank. Prints {question: [document path, ...]} (top 10 documents).
import { createStore } from '@tobilu/qmd'
import { readFileSync } from 'node:fs'

const [mode, casesFile] = process.argv.slice(2)
const cases = JSON.parse(readFileSync(casesFile, 'utf8'))
const store = await createStore({ dbPath: process.env.QMD_DB || new URL('./.qmd/index.sqlite', import.meta.url).pathname })
const out = {}
const t0 = Date.now()
for (const c of cases) {
  let rs
  if (mode === 'lex') rs = await store.searchLex(c.q, { limit: 30 })
  else if (mode === 'vec') rs = await store.searchVector(c.q, { limit: 30 })
  else rs = await store.search({ query: c.q, limit: 30, rerank: mode === 'hybrid' })
  const docs = []
  for (const r of rs) {
    const f = String(r.file || r.displayPath || r.path || '').replace(/^qmd:\/\/lib\//, '').replace(/\.md$/, '')
    if (f && !docs.includes(f)) docs.push(f)
    if (docs.length >= 10) break
  }
  out[c.q] = docs
}
console.error(`${mode}: ${cases.length} queries, ${((Date.now() - t0) / cases.length / 1000).toFixed(2)} s/query`)
console.log(JSON.stringify(out))
await store.close()
