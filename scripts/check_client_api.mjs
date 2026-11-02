/** Inspect application browser output for accidental direct local API requests. */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { resolve } from 'node:path';
const root = resolve(process.env.FRONTEND_BUILD_DIR ?? resolve(process.cwd(), 'frontend'));
function scan(path) {
  for (const name of readdirSync(path)) {
    const file = resolve(path,name);
    if (statSync(file).isDirectory()) scan(file);
    else if (name.endsWith('.js')) {
      const source=readFileSync(file,'utf8');
      if (/fetch\(\s*["'`]https?:\/\/(?:localhost|127\.0\.0\.1|\[::1\])(?::\d+)?\//.test(source)) throw new Error('Direct localhost API request in browser output: '+name);
    }
  }
}
const client=readFileSync(resolve(root,'src/lib/api.ts'),'utf8');
if (!client.includes('fetch(`/api/backend/${path}`') || /NEXT_PUBLIC_.*(?:TOKEN|SECRET|PASSWORD)/i.test(client)) throw new Error('Client API boundary changed');
scan(resolve(root,'.next/static'));
console.log('Browser API boundary verified: same-origin bridge, no direct localhost fetch URLs. Framework URL literals are not treated as API requests.');
