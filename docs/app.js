"use strict";

const form = document.querySelector("#audit");
const input = document.querySelector("#input");
const statusMessage = document.querySelector("#status");
const report = document.querySelector("#report");
const submit = form.querySelector("button");
const theme = document.querySelector("#theme");

function setTheme(dark) {
  document.documentElement.dataset.theme = dark ? "dark" : "light";
  theme.setAttribute("aria-pressed", String(dark));
}
setTheme(matchMedia("(prefers-color-scheme: dark)").matches);
theme.addEventListener("click", () => setTheme(theme.getAttribute("aria-pressed") !== "true"));

function append(parent, tag, value) {
  const node = document.createElement(tag);
  if (value !== undefined) node.textContent = value;
  parent.append(node);
  return node;
}

function findings(parent, items) {
  if (!items.length) return;
  const labels = {hata: "Hata", uyari: "Uyarı", bilgi: "Bilgi"};
  const list = append(parent, "ul");
  for (const finding of items) {
    append(list, "li", `${labels[finding.severity]} · ${finding.message} Öneri: ${finding.suggestion}`);
  }
}

function render(data) {
  const summary = data.summary;
  append(report, "h2", "Denetim raporu");
  append(report, "p", data.notice);
  append(report, "p", `${summary.references} kaynak · Baskın stil: ${summary.style} · ` +
    `${summary.hata} hata, ${summary.uyari} uyarı, ${summary.bilgi} bilgi`);
  if (data.findings.length) {
    append(report, "h3", "Belge bulguları");
    findings(report, data.findings);
  }
  for (const ref of data.references) {
    const article = append(report, "article");
    append(article, "h3", `${ref.index}. ${ref.title || "Başlık ayrıştırılamadı"}`);
    append(article, "p", `Stil tahmini: ${ref.style} (%${Math.round(ref.confidence * 100)})`);
    if (ref.findings.length) findings(article, ref.findings);
    else append(article, "p", "Biçim bulgusu yok.");
    if (ref.crossref) append(article, "p", ref.crossref.message);
    append(article, "h4", "Elle doğrulama kontrol listesi");
    const checklist = append(article, "ul");
    checklist.className = "checklist";
    for (const [name, url] of Object.entries(ref.links)) {
      const item = append(checklist, "li");
      const checkbox = append(item, "input");
      checkbox.type = "checkbox";
      checkbox.setAttribute("aria-label", `${ref.index}. kaynak için ${name} kontrolü tamamlandı`);
      const link = append(item, "a", name);
      link.href = url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
    }
  }
}

async function auditLocally(text) {
  const response = await fetch("/api/denetle", {
    method: "POST",
    headers: {"X-Kaynakca-Request": "1", "Content-Type": "text/plain; charset=utf-8"},
    body: text,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error);
  return data;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (submit.disabled) return;
  report.replaceChildren();
  statusMessage.textContent = "Denetleniyor…";
  submit.disabled = true;
  try {
    const audit = form.hasAttribute("data-browser") ? window.auditBibliography : auditLocally;
    if (!audit) throw new Error("Tarayıcı denetimi yüklenemedi. Sayfayı yenileyip yeniden deneyin.");
    const data = await audit(input.value, (message) => { statusMessage.textContent = message; });
    render(data);
    statusMessage.textContent = "Denetim tamamlandı.";
  } catch (error) {
    statusMessage.textContent = `Denetim başarısız. ${error.message}`;
  } finally {
    submit.disabled = false;
  }
});
