const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
  "Content-Type": "application/json",
};

const OWNER = "fedezebi-ui";
const REPO = "super-investor-vnext-codex";
const WORKFLOW = "octa-vnext-refresh.yml";

export default async (req) => {
  if (req.method === "OPTIONS") return new Response("", { headers: CORS });
  if (req.method !== "POST") {
    return new Response(JSON.stringify({ ok: false, error: "method_not_allowed" }), { status: 405, headers: CORS });
  }

  const token = process.env.GITHUB_ACTIONS_TOKEN || process.env.GH_WORKFLOW_TOKEN;
  if (!token) {
    return new Response(JSON.stringify({
      ok: false,
      error: "missing_github_actions_token",
      hint: "Configura GITHUB_ACTIONS_TOKEN o GH_WORKFLOW_TOKEN su Netlify per lanciare il workflow dall'app.",
    }), { status: 501, headers: CORS });
  }

  let mode = "all";
  try {
    const body = await req.json();
    mode = String(body?.mode || "all");
  } catch {}

  const url = `https://api.github.com/repos/${OWNER}/${REPO}/actions/workflows/${WORKFLOW}/dispatches`;
  const gh = await fetch(url, {
    method: "POST",
    headers: {
      "Accept": "application/vnd.github+json",
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "super-investor-vnext",
    },
    body: JSON.stringify({
      ref: "main",
      inputs: {
        force_run: "true",
        run_apex: mode === "all" || mode === "apex" ? "true" : "false",
      },
    }),
  });

  if (!gh.ok) {
    const detail = await gh.text().catch(() => "");
    return new Response(JSON.stringify({ ok: false, error: "github_dispatch_failed", status: gh.status, detail }),
      { status: 502, headers: CORS });
  }

  return new Response(JSON.stringify({
    ok: true,
    mode,
    workflow: `https://github.com/${OWNER}/${REPO}/actions/workflows/${WORKFLOW}`,
    requested_at: new Date().toISOString(),
  }), { headers: CORS });
};
