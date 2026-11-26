"use strict";

function crossrefUrl(doi) {
  return "https://api.crossref.org/works/" + encodeURIComponent(doi);
}

function crossrefDelay(lastStart, now) {
  return Math.max(0, 500 - (now - lastStart));
}

async function fetchCrossref(doi, request = fetch, timeoutMs = 10_000) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await request(crossrefUrl(doi), {
      signal: controller.signal,
      credentials: "omit",
      redirect: "error",
      referrerPolicy: "no-referrer",
    });
    if (!response.ok) return {status: response.status};
    try {
      return {status: response.status, payload: await response.json()};
    } catch (error) {
      if (controller.signal.aborted) return {status: 0};
      return {status: response.status};
    }
  } catch (error) {
    return {status: 0};
  } finally {
    clearTimeout(timeout);
  }
}

if (typeof module !== "undefined") module.exports = {crossrefUrl, crossrefDelay, fetchCrossref};
