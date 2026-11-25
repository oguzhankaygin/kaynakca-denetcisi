"use strict";

const form = document.querySelector("#audit");
const input = document.querySelector("#input");
const status = document.querySelector("#status");
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

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  report.replaceChildren();
  status.textContent = "Denetleniyor…";
  submit.disabled = true;
  try {
    const response = await fetch("/api/denetle", {
      method: "POST",
      headers: {"X-Kaynakca-Request": "1", "Content-Type": "text/plain; charset=utf-8"},
      body: input.value,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    render(data);
    status.textContent = "Denetim tamamlandı.";
  } catch (error) {
    status.textContent = `Denetim başarısız. ${error.message}`;
  } finally {
    submit.disabled = false;
  }
});
