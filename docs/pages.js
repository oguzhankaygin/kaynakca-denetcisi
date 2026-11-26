"use strict";

const pyodideUrl = "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/";
const crossrefOption = document.querySelector("#crossref");
const actions = document.querySelector("#report-actions");
let browserPython;
let lastCrossrefStart = -Infinity;
let markdown;

async function loadBrowserPython(progress) {
  if (browserPython) return browserPython;
  progress("İlk kullanım için Python (Pyodide) yükleniyor…");
  if (typeof globalThis.loadPyodide !== "function") {
    await new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = pyodideUrl + "pyodide.js";
      script.onload = resolve;
      script.onerror = () => {
        script.remove();
        reject(new Error("Pyodide betiği yüklenemedi."));
      };
      document.head.append(script);
    });
  }
  const pyodide = await globalThis.loadPyodide({indexURL: pyodideUrl});
  progress("Denetim paketi yükleniyor…");
  const manifest = await fetch("./py/manifest.json");
  if (!manifest.ok) throw new Error("Paket listesi alınamadı.");
  const names = await manifest.json();
  pyodide.FS.mkdirTree("/audit/kaynakca");
  await Promise.all(names.map(async (name) => {
    const response = await fetch("./py/kaynakca/" + name);
    if (!response.ok) throw new Error("Paket dosyası alınamadı.");
    pyodide.FS.writeFile("/audit/kaynakca/" + name, new Uint8Array(await response.arrayBuffer()));
  }));
  pyodide.runPython("import sys\nsys.path.insert(0, '/audit')\nfrom kaynakca.browser import collect_dois, audit_json");
  browserPython = pyodide;
  return pyodide;
}

window.auditBibliography = async (text, progress) => {
  actions.hidden = true;
  const online = crossrefOption.checked;
  let python;
  try {
    python = await loadBrowserPython(progress);
  } catch {
    throw new Error("Python ortamı yüklenemedi. İnternet bağlantınızı kontrol edip yeniden deneyin.");
  }

  try {
    let responses = null;
    if (online) {
      const collect = python.globals.get("collect_dois");
      let dois;
      try {
        dois = Object.entries(JSON.parse(collect(text)));
      } finally {
        collect.destroy();
      }
      responses = {};
      for (const [index, [key, doi]] of dois.entries()) {
        progress(`Crossref kayıtları sorgulanıyor (${index + 1}/${dois.length})…`);
        let delay = crossrefDelay(lastCrossrefStart, performance.now());
        while (delay > 0) {
          await new Promise((resolve) => setTimeout(resolve, delay));
          delay = crossrefDelay(lastCrossrefStart, performance.now());
        }
        lastCrossrefStart = performance.now();
        responses[key] = await fetchCrossref(doi);
      }
    }
    progress("Kaynakça denetleniyor…");
    const audit = python.globals.get("audit_json");
    try {
      const result = JSON.parse(audit(text, responses === null ? null : JSON.stringify(responses)));
      markdown = result.markdown;
      actions.hidden = false;
      return result.report;
    } finally {
      audit.destroy();
    }
  } catch {
    throw new Error("Kaynakça işlenemedi. Metni veya BibTeX sözdizimini kontrol edip yeniden deneyin.");
  }
};

document.querySelector("#markdown").addEventListener("click", () => {
  const url = URL.createObjectURL(new Blob([markdown], {type: "text/markdown;charset=utf-8"}));
  const link = document.createElement("a");
  link.href = url;
  link.download = "kaynakca-raporu.md";
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
document.querySelector("#print").addEventListener("click", () => window.print());
