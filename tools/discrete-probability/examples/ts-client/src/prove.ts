/**
 * Proof script: drives the live server for both a successful call and a
 * deliberate error case, so the committed proof transcript shows the error
 * path (a tool error throwing, not silently swallowed) as well as the
 * success path. Run via `npm run prove > proof/run_<date>.txt` (see
 * ../../../../scripts for this repo's proof-transcript convention).
 */
import { fileURLToPath } from "node:url";
import path from "node:path";
import { McpStdioSession } from "./client.js";
import type { CompareTwoProportionsResult } from "./types.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const SERVER_SCRIPT = path.resolve(here, "../../../server.py");

async function main(): Promise<void> {
  const session = new McpStdioSession(SERVER_SCRIPT);
  await session.connect();

  try {
    console.log("--- list_tools ---");
    console.log(JSON.stringify(await session.listTools(), null, 2));

    console.log("\n--- compare_two_proportions (300 vs 900 seeds, verify=true) ---");
    const result = await session.callTool<CompareTwoProportionsResult>(
      "compare_two_proportions",
      { successes_a: 168, trials_a: 300, successes_b: 522, trials_b: 900, verify: true },
    );
    console.log(JSON.stringify(result, null, 2));

    console.log("\n--- compare_two_proportions error case (trials_a=0, expect thrown error) ---");
    try {
      await session.callTool("compare_two_proportions", {
        successes_a: 0,
        trials_a: 0,
        successes_b: 1,
        trials_b: 10,
      });
      console.log("UNEXPECTED: call succeeded, should have thrown");
      process.exitCode = 1;
    } catch (err) {
      console.log(`Correctly threw: ${(err as Error).message}`);
    }
  } finally {
    await session.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
