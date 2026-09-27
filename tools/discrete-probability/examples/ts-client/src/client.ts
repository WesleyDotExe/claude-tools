/**
 * A minimal, reusable Node/TypeScript client for any of this repo's Python
 * MCP stdio servers -- built for an external TS project (e.g. a win-rate
 * balance harness) to call `discrete-probability`'s `compare_two_proportions`
 * without hand-rolling stdio JSON-RPC.
 *
 * Mirrors the extraction logic in `scripts/mcp_client.py`'s `_extract()`:
 * prefer `structuredContent` (present when the tool's return type has a
 * JSON schema the SDK can generate), fall back to parsing the sole text
 * content block as JSON. A tool error (`isError: true`) throws instead of
 * silently returning the error text as if it were a value.
 */
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

export interface CallResult<T = unknown> {
  ok: true;
  value: T;
}

export interface CallError {
  ok: false;
  error: string;
}

/**
 * Spawn `python3 <serverScript>` over stdio, call one tool, then close the
 * connection. For a program making many calls, prefer opening one
 * `McpStdioSession` (below) and reusing it instead of paying process-spawn
 * cost per call.
 */
export async function callTool<T = unknown>(
  serverScript: string,
  toolName: string,
  args: Record<string, unknown> = {},
  pythonCommand = "python3",
): Promise<T> {
  const session = new McpStdioSession(serverScript, pythonCommand);
  try {
    await session.connect();
    return await session.callTool<T>(toolName, args);
  } finally {
    await session.close();
  }
}

/** A reusable connection to one MCP stdio server, for multiple calls without
 * re-spawning the process each time (e.g. a balance harness comparing many
 * pairs of variants in one run). */
export class McpStdioSession {
  private client: Client;
  private transport: StdioClientTransport;
  private connected = false;

  constructor(
    private readonly serverScript: string,
    private readonly pythonCommand = "python3",
  ) {
    this.transport = new StdioClientTransport({
      command: this.pythonCommand,
      args: [this.serverScript],
    });
    this.client = new Client(
      { name: "discrete-probability-ts-client-example", version: "1.0.0" },
      { capabilities: {} },
    );
  }

  async connect(): Promise<void> {
    if (this.connected) return;
    await this.client.connect(this.transport);
    this.connected = true;
  }

  async listTools(): Promise<string[]> {
    const result = await this.client.listTools();
    return result.tools.map((t) => t.name);
  }

  async callTool<T = unknown>(
    toolName: string,
    args: Record<string, unknown> = {},
  ): Promise<T> {
    const result = await this.client.callTool({
      name: toolName,
      arguments: args,
    });

    if (result.isError) {
      const message = extractText(result) ?? "tool returned isError with no text content";
      throw new Error(`${toolName} failed: ${message}`);
    }

    if (result.structuredContent !== undefined) {
      return result.structuredContent as T;
    }

    const text = extractText(result);
    if (text === undefined) {
      return undefined as T;
    }
    try {
      return JSON.parse(text) as T;
    } catch {
      // Not JSON (e.g. a plain-string-returning tool) -- hand back the raw text.
      return text as unknown as T;
    }
  }

  async close(): Promise<void> {
    if (!this.connected) return;
    await this.client.close();
    this.connected = false;
  }
}

function extractText(result: unknown): string | undefined {
  const content = (result as { content?: unknown[] }).content;
  const blocks = (content ?? []) as Array<{ type: string; text?: string }>;
  const texts = blocks.filter((b) => b.type === "text").map((b) => b.text ?? "");
  if (texts.length === 0) return undefined;
  return texts.join("\n");
}
