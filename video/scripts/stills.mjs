// Render many MapScene stills with one bundle (bundling costs ~20 s; per-still CLI calls would repeat it).
// Usage: node scripts/stills.mjs <jobs.json>   jobs: [{"props": "<file>", "out": "<png>", "frame": 120}]
import {bundle} from '@remotion/bundler';
import {renderStill, selectComposition} from '@remotion/renderer';
import fs from 'node:fs';
import path from 'node:path';

const jobs = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts')});
for (const job of jobs) {
  const inputProps = JSON.parse(fs.readFileSync(job.props, 'utf8'));
  const composition = await selectComposition({serveUrl, id: 'MapScene', inputProps});
  const frame = Math.min(job.frame, composition.durationInFrames - 1);
  await renderStill({composition, serveUrl, output: job.out, inputProps, frame, imageFormat: 'png'});
  console.log('still', path.basename(job.out));
}
