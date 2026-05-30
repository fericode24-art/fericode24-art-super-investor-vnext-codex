import { dispatchWorkflow, jsonResponse, romeTimeParts } from "./_shared/dispatch-workflow.mjs";

export default async () => {
  const rome = romeTimeParts();
  const shouldRun = rome.weekday === 2 && rome.hour === 15 && rome.minute === 30;

  if (!shouldRun) {
    return jsonResponse({ ok: true, skipped: true, reason: "outside_apex_window", rome });
  }

  const result = await dispatchWorkflow({ mode: "all", reason: "netlify_schedule_apex" });
  return jsonResponse(result.body, result.status);
};

export const config = {
  schedule: "30 13,14 * * 2",
};
