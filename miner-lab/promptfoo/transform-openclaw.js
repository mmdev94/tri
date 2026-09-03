/** Map OpenClaw /v1/chat/completions JSON to a string (content or API error). */
module.exports = (json, text) => {
  if (json && json.choices && json.choices[0] && json.choices[0].message) {
    const c = json.choices[0].message.content;
    if (c != null && String(c).length) return String(c);
  }
  if (json && json.error && json.error.message) {
    return `OPENCLAW_ERROR: ${json.error.message}`;
  }
  if (json && json.detail) return `OPENCLAW_ERROR: ${JSON.stringify(json.detail)}`;
  return text == null ? "" : String(text);
};
