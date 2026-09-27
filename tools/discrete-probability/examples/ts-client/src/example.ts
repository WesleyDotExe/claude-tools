/**
 * Runnable example: an external TypeScript project (e.g. a balance-testing
 * harness comparing two variants' win rates) calling this repo's
 * `discrete-probability` MCP server's `compare_two_proportions` tool.
 *
 * Models the scenario `special-projects/wishlist.md`'s `[ai-tcg-caller]`
 * entry names: deciding whether an observed win-rate gap between an
 * in-band run (300 seeds) and an out-of-band run (900 seeds) is real or
 * within the ~2.9-point standard-error noise band those sample sizes imply
 * -- instead of comparing the two raw percentages by eye.
 *
 * Run with: `npm install && npm run example` (from this directory).
 */
import { fileURLToPath } from "node:url";
import path from "node:path";
import { McpStdioSession } from "./client.js";
import type { CompareTwoProportionsResult } from "./types.js";

const here = path.dirname(fileURLToPath(import.meta.url));
// This example lives at tools/discrete-probability/examples/ts-client/src/ --
// the server it drives is three directories up. An external project should
// instead point this at wherever it vendors/checks out this repo.
const SERVER_SCRIPT = path.resolve(here, "../../../server.py");

async function main(): Promise<void> {
  const session = new McpStdioSession(SERVER_SCRIPT);
  await session.connect();

  try {
    console.log("Tools exposed:", await session.listTools());

    // In-band run: 168 wins out of 300 seeds (56.0%).
    // Out-of-band run: 522 wins out of 900 seeds (58.0%).
    // A 2-point gap looks small, but is it distinguishable from noise at
    // these sample sizes (the harness's own ~2.9pt-SE concern)?
    const result = await session.callTool<CompareTwoProportionsResult>(
      "compare_two_proportions",
      {
        successes_a: 168,
        trials_a: 300,
        successes_b: 522,
        trials_b: 900,
        verify: true,
      },
    );

    console.log("\ncompare_two_proportions result:");
    console.log(JSON.stringify(result, null, 2));

    console.log(`\nVerdict: ${result.verdict}`);
    if (result.simulation) {
      console.log(
        `Permutation-test cross-check agrees on the significance call: ` +
          `${result.simulation.agrees_on_significance_call}`,
      );
    }

    // What a harness actually branches on:
    if (result.significant) {
      console.log("\n-> Treat this as a real balance difference, not noise.");
    } else {
      console.log(
        "\n-> Gap is within noise for these sample sizes -- do not act on it yet.",
      );
    }
  } finally {
    await session.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
