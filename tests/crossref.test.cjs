"use strict";

const {test} = require("node:test");
const assert = require("node:assert/strict");
const {crossrefUrl, crossrefDelay, fetchCrossref} = require("../docs/crossref.js");

test("DOI sabit Crossref adresine tek bir yol bileşeni olarak eklenir", () => {
  const url = new URL(crossrefUrl("10.1234/a/b%?&ı"));
  assert.equal(url.origin, "https://api.crossref.org");
  assert.equal(url.pathname, "/works/10.1234%2Fa%2Fb%25%3F%26%C4%B1");
  assert.equal(url.search, "");
});

test("Crossref istek başlangıçları arasında en az 500 ms bırakılır", () => {
  assert.equal(crossrefDelay(-Infinity, 100), 0);
  assert.equal(crossrefDelay(100, 100), 500);
  assert.equal(crossrefDelay(100, 599), 1);
  assert.equal(crossrefDelay(100, 600), 0);
  assert.equal(crossrefDelay(100, 900), 0);
});

test("Crossref isteği yalnızca DOI ile kimlik bilgisi ve yönlendirme olmadan yapılır", async () => {
  const payload = {message: {title: ["Kurgusal iz"]}};
  const result = await fetchCrossref("10.1234/iz", async (url, options) => {
    assert.equal(url, "https://api.crossref.org/works/10.1234%2Fiz");
    assert.equal(options.credentials, "omit");
    assert.equal(options.redirect, "error");
    assert.equal(options.referrerPolicy, "no-referrer");
    assert.equal(options.body, undefined);
    return {ok: true, status: 200, json: async () => payload};
  });
  assert.deepEqual(result, {status: 200, payload});
});

test("Crossref HTTP, bozuk JSON ve ağ hataları ayrıştırılır", async () => {
  assert.deepEqual(await fetchCrossref("10.1234/iz", async () => ({ok: false, status: 404})), {status: 404});
  assert.deepEqual(await fetchCrossref("10.1234/iz", async () => new Response("bozuk")), {status: 200});
  assert.deepEqual(await fetchCrossref("10.1234/iz", async () => { throw new Error("ağ"); }), {status: 0});
});

test("Crossref zaman aşımı yanıt gövdesini okumayı da iptal eder", async () => {
  const result = await fetchCrossref("10.1234/iz", async (url, {signal}) => ({
    ok: true,
    status: 200,
    json: () => new Promise((resolve, reject) => {
      signal.addEventListener("abort", () => reject(signal.reason), {once: true});
    }),
  }), 5);
  assert.deepEqual(result, {status: 0});
});
