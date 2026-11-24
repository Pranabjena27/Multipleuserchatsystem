/**
 * ConnectX Analytics & NLP Interactive Laboratory Client
 * Powers interactive testers for Sentiment, Spam Heuristics, Categorization, Summarization, and Moderation.
 */

document.addEventListener("DOMContentLoaded", () => {
  // 1. Sentiment Analyzer Interactive Test
  const testSentimentBtn = document.getElementById("btn-test-sentiment");
  const sentimentInput = document.getElementById("input-test-sentiment");
  const sentimentResult = document.getElementById("result-test-sentiment");

  if (testSentimentBtn && sentimentInput && sentimentResult) {
    testSentimentBtn.addEventListener("click", () => {
      const text = sentimentInput.value.trim();
      if (!text) return;

      sentimentResult.textContent = "Analyzing valence, boosters, and negations in Python...";
      fetch("/analytics/test-sentiment", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      })
        .then((r) => r.json())
        .then((data) => {
          const color =
            data.label === "positive"
              ? "var(--success)"
              : data.label === "negative"
                ? "var(--danger)"
                : "var(--text-muted)";

          sentimentResult.innerHTML = `
            <div><strong>Polarity Label:</strong> <span style="color:${color};font-weight:700;">${data.label.toUpperCase()}</span></div>
            <div><strong>Normalized Score:</strong> ${data.score} (Pos: ${(data.positive * 100).toFixed(0)}%, Neu: ${(data.neutral * 100).toFixed(0)}%, Neg: ${(data.negative * 100).toFixed(0)}%)</div>
            <div style="margin-top:6px;font-size:0.8rem;color:var(--text-secondary);background:var(--bg-tertiary);padding:6px;border-radius:4px;">
              <strong>Diagnostic Explanation:</strong> ${data.explanation}
            </div>
          `;
        })
        .catch(() => {
          sentimentResult.textContent = "Analysis failed.";
        });
    });
  }

  // 2. Spam Detector Interactive Test
  const testSpamBtn = document.getElementById("btn-test-spam");
  const spamInput = document.getElementById("input-test-spam");
  const spamResult = document.getElementById("result-test-spam");

  if (testSpamBtn && spamInput && spamResult) {
    testSpamBtn.addEventListener("click", () => {
      const text = spamInput.value.trim();
      if (!text) return;

      spamResult.textContent = "Computing Shannon entropy, link counts, and spam heuristics...";
      fetch("/analytics/test-spam", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      })
        .then((r) => r.json())
        .then((data) => {
          const badge = data.is_spam
            ? `<span class="badge-status badge-banned">FLAGGED AS SPAM</span>`
            : `<span class="badge-status badge-active">CLEAN MESSAGE</span>`;

          const reasons = data.reasons && data.reasons.length > 0
            ? `<ul>${data.reasons.map((r) => `<li>${r}</li>`).join("")}</ul>`
            : "None";

          spamResult.innerHTML = `
            <div><strong>Verdict:</strong> ${badge} (Score: ${data.score})</div>
            <div><strong>Shannon Entropy:</strong> ${data.entropy} bits/symbol &bull; <strong>URLs Detected:</strong> ${data.url_count}</div>
            <div><strong>Capitalization Ratio:</strong> ${(data.caps_ratio * 100).toFixed(1)}%</div>
            <div><strong>Diagnostic Reasons:</strong> ${reasons}</div>
            <div style="margin-top:6px;font-size:0.8rem;color:var(--text-secondary);background:var(--bg-tertiary);padding:6px;border-radius:4px;">
              <strong>Explanation:</strong> ${data.explanation}
            </div>
          `;
        })
        .catch(() => {
          spamResult.textContent = "Spam test failed.";
        });
    });
  }

  // 3. Message Categorizer Interactive Test
  const testCatBtn = document.getElementById("btn-test-cat");
  const catInput = document.getElementById("input-test-cat");
  const catResult = document.getElementById("result-test-cat");

  if (testCatBtn && catInput && catResult) {
    testCatBtn.addEventListener("click", () => {
      const text = catInput.value.trim();
      if (!text) return;

      catResult.textContent = "Evaluating linguistic patterns and regex signatures...";
      fetch("/analytics/test-categorize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      })
        .then((r) => r.json())
        .then((data) => {
          catResult.innerHTML = `
            <div><strong>Granular Tag:</strong> <span class="badge-category badge-cat-${data.category}">${data.category}</span></div>
            <div><strong>Academic Macro Category:</strong> <span style="font-weight:700;color:var(--primary);">${data.macro_category.replace(/_/g, ' ').toUpperCase()}</span></div>
            <div><strong>Confidence:</strong> ${(data.confidence * 100).toFixed(0)}%</div>
            <div style="margin-top:6px;font-size:0.8rem;color:var(--text-secondary);background:var(--bg-tertiary);padding:6px;border-radius:4px;">
              <strong>Explanation:</strong> ${data.explanation}
            </div>
          `;
        })
        .catch(() => {
          catResult.textContent = "Classification failed.";
        });
    });
  }

  // 4. Summarizer Interactive Test
  const testSumBtn = document.getElementById("btn-test-sum");
  const sumInput = document.getElementById("input-test-sum");
  const sumResult = document.getElementById("result-test-sum");

  if (testSumBtn && sumInput && sumResult) {
    testSumBtn.addEventListener("click", () => {
      const text = sumInput.value.trim();
      if (!text) return;

      sumResult.textContent = "Building term frequency graph and extracting key sentences...";
      fetch("/analytics/test-summarize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      })
        .then((r) => r.json())
        .then((data) => {
          const s = data.summary;
          const bullets = s.bullets && s.bullets.length > 0
            ? s.bullets.map((b) => `<li>${b}</li>`).join("")
            : "<li>No sentences selected</li>";
          const actions = s.action_items && s.action_items.length > 0
            ? s.action_items.map((a) => `<li>${a}</li>`).join("")
            : "";
          const topics = s.key_topics && s.key_topics.length > 0
            ? s.key_topics.map((t) => `<span class="badge-category badge-cat-general" style="margin-right:4px;">${t}</span>`).join("")
            : "";

          sumResult.innerHTML = `
            <div><strong>Extracted Key Points:</strong></div>
            <ul>${bullets}</ul>
            ${actions ? `<div style="margin-top:8px;"><strong>Action Items:</strong><ul>${actions}</ul></div>` : ""}
            ${topics ? `<div style="margin-top:8px;"><strong>Key Topics:</strong> ${topics}</div>` : ""}
          `;
        })
        .catch(() => {
          sumResult.textContent = "Summarization failed.";
        });
    });
  }

  // 5. Content Moderation Interactive Test
  const testModBtn = document.getElementById("btn-test-mod");
  const modInput = document.getElementById("input-test-mod");
  const modResult = document.getElementById("result-test-mod");

  if (testModBtn && modInput && modResult) {
    testModBtn.addEventListener("click", () => {
      const text = modInput.value.trim();
      if (!text) return;

      modResult.textContent = "Evaluating moderation policies, toxicity patterns, and severity...";
      fetch("/analytics/test-moderation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      })
        .then((r) => r.json())
        .then((data) => {
          const badgeClass =
            data.severity === "critical"
              ? "badge-banned"
              : data.severity === "high" || data.severity === "medium"
                ? "badge-pending"
                : "badge-active";

          modResult.innerHTML = `
            <div><strong>Severity:</strong> <span class="badge-status ${badgeClass}">${data.severity.toUpperCase()}</span> &bull; <strong>Recommended Action:</strong> [${data.action.toUpperCase()}]</div>
            <div><strong>Sanitized Text:</strong> <code style="font-size:0.85rem;">${data.cleaned_content || text}</code></div>
            <div><strong>Violations:</strong> ${data.policy_violations.length > 0 ? data.policy_violations.join(", ") : "None"}</div>
            <div style="margin-top:6px;font-size:0.8rem;color:var(--text-secondary);background:var(--bg-tertiary);padding:6px;border-radius:4px;">
              <strong>Admin Explanation:</strong> ${data.explanation}
            </div>
          `;
        })
        .catch(() => {
          modResult.textContent = "Moderation test failed.";
        });
    });
  }
});
