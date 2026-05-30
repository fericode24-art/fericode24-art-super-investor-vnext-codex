import { dispatchWorkflow, jsonResponse } from "./_shared/dispatch-workflow.mjs";

export default async () => {
  const result = await dispatchWorkflow({ mode: "all", reason: "netlify_schedule_smoke" });
  return jsonResponse(result.body, result.status);
};

export const config = {
  schedule: "*/5 * * * *",
};
