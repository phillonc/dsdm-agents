/* DSDM Agents Console
 *
 * A dependency-free single-page app. Views are pure functions that return an
 * HTML string; `render` swaps them in and then wires up event listeners. All
 * server state lives in `state`, refreshed by explicit loads and, while work is
 * running, by a single polling timer.
 */
(function () {
  "use strict";

  // ------------------------------------------------------------------ state

  var state = {
    token: new URLSearchParams(window.location.search).get("token") || "",
    boot: null,
    route: { name: "overview", params: {} },
    runs: [],
    run: null,
    runCursor: 0,
    events: [],
    projects: [],
    recent: [],
    rooms: [],
    room: null,
    files: null,
    doc: null,
    readiness: null,
    routeError: null,
    busy: false,
    draft: null,
  };

  var poller = null;

  // ------------------------------------------------------------------ utils

  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function qs(selector, root) {
    return (root || document).querySelector(selector);
  }

  function qsa(selector, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(selector));
  }

  function on(selector, event, handler, root) {
    qsa(selector, root).forEach(function (node) {
      node.addEventListener(event, handler);
    });
  }

  function timeOf(iso) {
    if (!iso) return "";
    var date = new Date(iso);
    if (isNaN(date.getTime())) return "";
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  }

  function relative(iso) {
    if (!iso) return "-";
    var date = new Date(iso);
    if (isNaN(date.getTime())) return "-";
    var seconds = Math.round((Date.now() - date.getTime()) / 1000);
    if (seconds < 45) return "just now";
    if (seconds < 3600) return Math.round(seconds / 60) + " min ago";
    if (seconds < 86400) return Math.round(seconds / 3600) + " hr ago";
    var days = Math.round(seconds / 86400);
    if (days < 30) return days + (days === 1 ? " day ago" : " days ago");
    return date.toLocaleDateString();
  }

  function duration(startIso, endIso) {
    if (!startIso) return "";
    var start = new Date(startIso).getTime();
    var end = endIso ? new Date(endIso).getTime() : Date.now();
    var seconds = Math.max(0, Math.round((end - start) / 1000));
    if (seconds < 60) return seconds + "s";
    var minutes = Math.floor(seconds / 60);
    if (minutes < 60) return minutes + "m " + (seconds % 60) + "s";
    return Math.floor(minutes / 60) + "h " + (minutes % 60) + "m";
  }

  function fileSize(bytes) {
    if (bytes == null) return "";
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / 1024 / 1024).toFixed(1) + " MB";
  }

  function titleCase(value) {
    return String(value || "").replace(/[_-]+/g, " ").replace(/\b\w/g, function (c) {
      return c.toUpperCase();
    });
  }

  var STATUS_STYLES = {
    queued: { label: "Queued", cls: "badge" },
    running: { label: "Running", cls: "badge badge-accent", pulse: true },
    waiting: { label: "Needs you", cls: "badge badge-warn", pulse: true },
    completed: { label: "Completed", cls: "badge badge-ok" },
    failed: { label: "Failed", cls: "badge badge-danger" },
    stopped: { label: "Stopped", cls: "badge badge-warn" },
  };

  function statusBadge(status) {
    var style = STATUS_STYLES[status] || { label: titleCase(status), cls: "badge" };
    return (
      '<span class="' + style.cls + '">' +
      (style.pulse ? '<span class="dot dot-pulse"></span>' : "") +
      esc(style.label) +
      "</span>"
    );
  }

  function isActive(status) {
    return status === "queued" || status === "running" || status === "waiting";
  }

  // ---------------------------------------------------------------- markdown

  function renderMarkdown(source) {
    var blocks = [];
    var text = String(source || "").replace(/\r\n/g, "\n");

    text = text.replace(/```([\w-]*)\n([\s\S]*?)```/g, function (_match, lang, code) {
      blocks.push('<pre><code data-lang="' + esc(lang) + '">' + esc(code.replace(/\n$/, "")) + "</code></pre>");
      return "%%BLOCK" + (blocks.length - 1) + "%%";
    });

    function inline(value) {
      return esc(value)
        .replace(/`([^`]+)`/g, "<code>$1</code>")
        .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
        .replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>")
        .replace(
          /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,
          '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
        );
    }

    var lines = text.split("\n");
    var html = [];
    var listType = null;
    var paragraph = [];
    var tableRows = [];

    function flushParagraph() {
      if (paragraph.length) {
        html.push("<p>" + paragraph.map(inline).join("<br />") + "</p>");
        paragraph = [];
      }
    }

    function flushList() {
      if (listType) {
        html.push("</" + listType + ">");
        listType = null;
      }
    }

    function flushTable() {
      if (!tableRows.length) return;
      var cells = tableRows.map(function (row) {
        return row.replace(/^\||\|$/g, "").split("|").map(function (cell) {
          return cell.trim();
        });
      });
      var head = cells[0];
      var body = cells.slice(1).filter(function (row) {
        return !/^-{2,}$|^:?-+:?$/.test(row[0] || "");
      });
      var out = ["<table><thead><tr>"];
      head.forEach(function (cell) {
        out.push("<th>" + inline(cell) + "</th>");
      });
      out.push("</tr></thead><tbody>");
      body.forEach(function (row) {
        out.push("<tr>");
        row.forEach(function (cell) {
          out.push("<td>" + inline(cell) + "</td>");
        });
        out.push("</tr>");
      });
      out.push("</tbody></table>");
      html.push(out.join(""));
      tableRows = [];
    }

    lines.forEach(function (raw) {
      var line = raw.replace(/\s+$/, "");

      if (/^\s*%%BLOCK\d+%%\s*$/.test(line)) {
        flushParagraph(); flushList(); flushTable();
        html.push(line.trim());
        return;
      }
      if (!line.trim()) {
        flushParagraph(); flushList(); flushTable();
        return;
      }
      if (/^\s*\|.*\|\s*$/.test(line)) {
        flushParagraph(); flushList();
        tableRows.push(line.trim());
        return;
      }
      flushTable();

      var heading = /^(#{1,6})\s+(.*)$/.exec(line);
      if (heading) {
        flushParagraph(); flushList();
        var level = Math.min(heading[1].length, 4);
        html.push("<h" + level + ">" + inline(heading[2]) + "</h" + level + ">");
        return;
      }
      if (/^\s*([-*_])\s*(\1\s*){2,}$/.test(line)) {
        flushParagraph(); flushList();
        html.push("<hr />");
        return;
      }
      if (/^\s*>\s?/.test(line)) {
        flushParagraph(); flushList();
        html.push("<blockquote>" + inline(line.replace(/^\s*>\s?/, "")) + "</blockquote>");
        return;
      }
      var bullet = /^\s*[-*+]\s+(.*)$/.exec(line);
      if (bullet) {
        flushParagraph();
        if (listType !== "ul") { flushList(); html.push("<ul>"); listType = "ul"; }
        html.push("<li>" + inline(bullet[1]) + "</li>");
        return;
      }
      var ordered = /^\s*\d+[.)]\s+(.*)$/.exec(line);
      if (ordered) {
        flushParagraph();
        if (listType !== "ol") { flushList(); html.push("<ol>"); listType = "ol"; }
        html.push("<li>" + inline(ordered[1]) + "</li>");
        return;
      }
      flushList();
      paragraph.push(line.trim());
    });

    flushParagraph(); flushList(); flushTable();

    return html.join("\n").replace(/%%BLOCK(\d+)%%/g, function (_m, index) {
      return blocks[Number(index)] || "";
    });
  }

  // --------------------------------------------------------------------- api

  function request(method, path, body) {
    var url = "/api" + path;
    if (state.token) {
      url += (url.indexOf("?") === -1 ? "?" : "&") + "token=" + encodeURIComponent(state.token);
    }
    var options = { method: method, headers: {} };
    if (state.token) options.headers["X-Console-Token"] = state.token;
    if (body !== undefined) {
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    }
    return fetch(url, options).then(function (response) {
      return response
        .json()
        .catch(function () {
          return {};
        })
        .then(function (payload) {
          if (!response.ok) {
            var error = new Error(payload.error || "Request failed (" + response.status + ")");
            error.status = response.status;
            throw error;
          }
          return payload;
        });
    });
  }

  var api = {
    bootstrap: function () { return request("GET", "/bootstrap"); },
    readiness: function () { return request("GET", "/readiness"); },
    projects: function () { return request("GET", "/projects"); },
    files: function (project, path) {
      return request("GET", "/projects/" + encodeURIComponent(project) + "/files?path=" + encodeURIComponent(path || ""));
    },
    file: function (project, path) {
      return request("GET", "/projects/" + encodeURIComponent(project) + "/file?path=" + encodeURIComponent(path));
    },
    runs: function () { return request("GET", "/runs"); },
    startRun: function (payload) { return request("POST", "/runs", payload); },
    run: function (id) { return request("GET", "/runs/" + encodeURIComponent(id)); },
    runEvents: function (id, cursor) {
      return request("GET", "/runs/" + encodeURIComponent(id) + "/events?cursor=" + (cursor || 0));
    },
    approve: function (runId, approvalId, approved, note) {
      return request("POST", "/runs/" + encodeURIComponent(runId) + "/approvals/" + encodeURIComponent(approvalId), {
        approved: approved,
        note: note || "",
      });
    },
    stopRun: function (id) { return request("POST", "/runs/" + encodeURIComponent(id) + "/stop", {}); },
    rooms: function () { return request("GET", "/rooms"); },
    room: function (project) { return request("GET", "/rooms/" + encodeURIComponent(project)); },
    createRoom: function (payload) { return request("POST", "/rooms", payload); },
    exportRoom: function (project) { return request("POST", "/rooms/" + encodeURIComponent(project) + "/export", {}); },
  };

  // ------------------------------------------------------------------ toasts

  function toast(title, message, kind) {
    var host = qs("#toasts");
    var node = document.createElement("div");
    node.className = "toast" + (kind ? " is-" + kind : "");
    node.innerHTML = "<div><strong>" + esc(title) + "</strong><span>" + esc(message || "") + "</span></div>";
    host.appendChild(node);
    setTimeout(function () {
      node.style.opacity = "0";
      setTimeout(function () { node.remove(); }, 250);
    }, kind === "error" ? 7000 : 4200);
  }

  function fail(error) {
    toast("Something went wrong", error && error.message ? error.message : String(error), "error");
  }

  // ------------------------------------------------------------- components

  function pageHeader(eyebrow, title, lede, actions) {
    return (
      '<header class="page-header"><div>' +
      (eyebrow ? '<div class="eyebrow">' + esc(eyebrow) + "</div>" : "") +
      "<h1>" + esc(title) + "</h1>" +
      (lede ? '<p class="lede">' + esc(lede) + "</p>" : "") +
      "</div>" +
      (actions ? '<div class="header-actions">' + actions + "</div>" : "") +
      "</header>"
    );
  }

  function emptyState(icon, title, message, action) {
    return (
      '<div class="empty"><div class="empty-icon" aria-hidden="true">' + esc(icon) + "</div>" +
      "<h3>" + esc(title) + "</h3><p>" + esc(message) + "</p>" +
      (action || "") +
      "</div>"
    );
  }

  function healthRing(score) {
    var value = Math.max(0, Math.min(100, Number(score) || 0));
    var radius = 30;
    var circumference = 2 * Math.PI * radius;
    var offset = circumference * (1 - value / 100);
    var colour = value >= 75 ? "var(--ok)" : value >= 50 ? "var(--warn)" : "var(--danger)";
    return (
      '<svg width="76" height="76" viewBox="0 0 76 76" role="img" aria-label="Health ' + value + ' out of 100">' +
      '<circle cx="38" cy="38" r="' + radius + '" fill="none" stroke="var(--surface-3)" stroke-width="7" />' +
      '<circle cx="38" cy="38" r="' + radius + '" fill="none" stroke="' + colour + '" stroke-width="7" ' +
      'stroke-linecap="round" stroke-dasharray="' + circumference + '" stroke-dashoffset="' + offset + '" ' +
      'transform="rotate(-90 38 38)" />' +
      "</svg>"
    );
  }

  function stageMeta(stageId) {
    var stages = (state.boot && state.boot.catalog.stages) || [];
    for (var i = 0; i < stages.length; i += 1) {
      if (stages[i].id === stageId) return stages[i];
    }
    return { id: stageId, name: titleCase(stageId), summary: "" };
  }

  function oversightMeta(id) {
    var levels = (state.boot && state.boot.catalog.oversightLevels) || [];
    for (var i = 0; i < levels.length; i += 1) {
      if (levels[i].id === id) return levels[i];
    }
    return { id: id, name: titleCase(id) };
  }

  // ------------------------------------------------------------------- views

  function viewOverview() {
    var counts = state.boot.counts;
    var readiness = state.readiness || state.boot.readiness;
    var runs = state.runs.slice(0, 6);
    var activeRuns = state.runs.filter(function (run) { return isActive(run.status); });

    var banner = "";
    if (!readiness.ready) {
      banner =
        '<div class="banner banner-danger"><div><strong>Setup needs attention</strong>' +
        '<div class="banner-body">' + readiness.blockingCount +
        " item(s) must be fixed before agents can run. " +
        '<a href="#/setup">Open Setup</a>.</div></div></div>';
    } else if (activeRuns.length) {
      banner =
        '<div class="banner banner-accent"><div><strong>' + activeRuns.length +
        " delivery run(s) in progress</strong>" +
        '<div class="banner-body"><a href="#/activity">Watch live activity</a>.</div></div></div>';
    }

    var stats =
      '<div class="grid grid-4">' +
      '<div class="stat"><div class="stat-label">Projects</div><div class="stat-value">' + counts.projects +
      '</div><div class="stat-note">Folders of delivered documents</div></div>' +
      '<div class="stat"><div class="stat-label">Delivery rooms</div><div class="stat-value">' + counts.rooms +
      '</div><div class="stat-note">Teams with a tracked mission</div></div>' +
      '<div class="stat"><div class="stat-label">Running now</div><div class="stat-value">' + activeRuns.length +
      '</div><div class="stat-note">Live agent activity</div></div>' +
      '<div class="stat"><div class="stat-label">Setup</div><div class="stat-value">' +
      (readiness.ready ? "Ready" : "Action") +
      '</div><div class="stat-note">' + esc(readiness.provider.name) + "</div></div>" +
      "</div>";

    var stageCards = state.boot.catalog.stages
      .filter(function (stage) { return stage.in_full_delivery; })
      .map(function (stage, index) {
        return (
          '<div class="stage-row">' +
          '<span class="stage-marker">' + (index + 1) + "</span>" +
          "<div><div class=\"stage-name\">" + esc(stage.name) + "</div>" +
          '<div class="stage-note">' + esc(stage.question) + "</div></div>" +
          '<div class="spacer"></div>' +
          '<button class="btn btn-sm btn-secondary" data-run-stage="' + esc(stage.id) + '">Run this stage</button>' +
          "</div>"
        );
      })
      .join("");

    var runsTable = runs.length
      ? '<table class="table"><thead><tr><th>Run</th><th>Type</th><th>Status</th><th>Started</th></tr></thead><tbody>' +
        runs
          .map(function (run) {
            return (
              '<tr class="clickable" data-run="' + esc(run.id) + '">' +
              '<td class="cell-strong">' + esc(run.title) + '<div class="cell-muted">' + esc(truncate(run.brief, 62)) + "</div></td>" +
              "<td>" + esc(titleCase(run.kind)) + "</td>" +
              "<td>" + statusBadge(run.status) + "</td>" +
              '<td class="cell-muted">' + esc(relative(run.startedAt || run.createdAt)) + "</td>" +
              "</tr>"
            );
          })
          .join("") +
        "</tbody></table>"
      : emptyState("◷", "No delivery runs yet", "Start your first piece of work and the agents will take it from there.",
          '<a class="btn btn-primary" href="#/new">Start delivery</a>');

    var recent = state.recent.length
      ? '<div class="file-list">' +
        state.recent
          .slice(0, 8)
          .map(function (item) {
            return (
              '<button class="file-row" data-doc-project="' + esc(item.project) + '" data-doc-path="' + esc(item.path) + '">' +
              '<span class="file-icon" aria-hidden="true">▤</span>' +
              '<span class="file-name">' + esc(item.name) + "</span>" +
              '<span class="file-size">' + esc(relative(item.modifiedAt)) + "</span>" +
              "</button>"
            );
          })
          .join("") +
        "</div>"
      : emptyState("▤", "No documents yet", "Completed stages write their documents here.");

    return (
      pageHeader(
        "Overview",
        "Delivery at a glance",
        "Your AI delivery team follows the DSDM lifecycle: every stage produces documents you can read, review and share.",
        '<a class="btn btn-primary" href="#/new">Start delivery</a>'
      ) +
      '<div class="stack">' +
      banner +
      stats +
      '<div class="grid grid-2">' +
      '<div class="card"><div class="card-header"><div><h2>Recent runs</h2>' +
      '<div class="sub">What your delivery team has been working on</div></div>' +
      '<a class="btn btn-sm btn-ghost" href="#/activity">View all</a></div>' +
      '<div class="card-body tight">' + runsTable + "</div></div>" +
      '<div class="card"><div class="card-header"><div><h2>Latest documents</h2>' +
      '<div class="sub">Newest deliverables across every project</div></div>' +
      '<a class="btn btn-sm btn-ghost" href="#/documents">Browse</a></div>' +
      '<div class="card-body tight">' + recent + "</div></div>" +
      "</div>" +
      '<div class="card"><div class="card-header"><div><h2>The delivery lifecycle</h2>' +
      '<div class="sub">Run the whole thing, or just the stage you need</div></div></div>' +
      '<div class="stage-list">' + stageCards + "</div></div>" +
      "</div>"
    );
  }

  function truncate(value, limit) {
    var text = String(value || "");
    return text.length > limit ? text.slice(0, limit - 1) + "…" : text;
  }

  // -- start delivery wizard -------------------------------------------------

  var EXAMPLES = [
    "A customer self-service portal so clients can track orders without calling support",
    "An internal expenses approval tool that replaces our spreadsheet process",
    "A mobile-friendly booking system for our three clinics",
  ];

  function ensureDraft() {
    if (!state.draft) {
      state.draft = {
        step: 1,
        scope: "delivery",
        brief: "",
        project: "",
        stages: ["feasibility"],
        oversight: state.boot.defaults.oversight,
        runtime: state.boot.defaults.runtime,
        provider: state.boot.defaults.provider,
        template: state.boot.defaults.template,
      };
    }
    return state.draft;
  }

  function viewNew() {
    var draft = ensureDraft();
    var steps = ["Describe", "Scope", "Oversight", "Review"];
    var stepper =
      '<div class="stepper">' +
      steps
        .map(function (label, index) {
          var number = index + 1;
          var cls = number === draft.step ? "step is-active" : number < draft.step ? "step is-done" : "step";
          return (
            '<div class="' + cls + '"><span class="step-num">' + (number < draft.step ? "✓" : number) + "</span>" +
            esc(label) + "</div>" +
            (number < steps.length ? '<span class="step-line"></span>' : "")
          );
        })
        .join("") +
      "</div>";

    var body = "";
    if (draft.step === 1) body = stepDescribe(draft);
    else if (draft.step === 2) body = stepScope(draft);
    else if (draft.step === 3) body = stepOversight(draft);
    else body = stepReview(draft);

    var back = draft.step > 1 ? '<button class="btn btn-secondary" data-step-back>Back</button>' : "";
    var next =
      draft.step < 4
        ? '<button class="btn btn-primary" data-step-next>Continue</button>'
        : '<button class="btn btn-primary btn-lg" data-start-run>' +
          (draft.scope === "room-plan" ? "Create delivery room" : "Start delivery") +
          "</button>";

    return (
      pageHeader("New work", "Start a delivery", "Describe what the business needs. The agents handle the method.") +
      stepper +
      '<div class="card"><div class="card-body">' + body + "</div>" +
      '<div class="card-header" style="border-top:1px solid var(--border);border-bottom:none;">' +
      '<div class="sub">Step ' + draft.step + " of 4</div>" +
      '<div class="row">' + back + next + "</div></div></div>"
    );
  }

  function stepDescribe(draft) {
    return (
      '<div class="stack">' +
      '<label class="field"><span class="field-label">What do you want to deliver?</span>' +
      '<span class="field-hint">Write it in business language — the outcome, who it is for, and why it matters. ' +
      "No technical detail required.</span>" +
      '<textarea id="brief" placeholder="For example: a customer self-service portal so clients can track their orders without calling support…">' +
      esc(draft.brief) +
      "</textarea></label>" +
      '<div class="row">' +
      '<span class="field-hint">Need a starting point:</span>' +
      EXAMPLES.map(function (example, index) {
        return '<button class="btn btn-sm btn-secondary" data-example="' + index + '">' + esc(truncate(example, 44)) + "</button>";
      }).join("") +
      "</div>" +
      '<label class="field"><span class="field-label">Project name <span class="field-hint">(optional)</span></span>' +
      '<span class="field-hint">Used to name the folder your documents are saved in. Left blank, one is generated for you.</span>' +
      '<input type="text" id="project" value="' + esc(draft.project) + '" placeholder="customer-portal" /></label>' +
      "</div>"
    );
  }

  function stepScope(draft) {
    var scopes = [
      {
        id: "delivery",
        title: "Full delivery",
        desc: "Run every stage end to end, from feasibility through to implementation.",
        meta: state.boot.catalog.fullDeliveryStageIds.length + " stages · the complete DSDM lifecycle",
      },
      {
        id: "stages",
        title: "Selected stages",
        desc: "Pick only the stages you need right now — useful when work is already under way.",
        meta: "You choose which stages run, in lifecycle order",
      },
      {
        id: "room-plan",
        title: "Delivery room only",
        desc: "Set up the team, mission and governance without running any agents yet.",
        meta: "Instant · no AI usage",
      },
    ];

    var picker = scopes
      .map(function (scope) {
        return (
          '<button type="button" class="choice' + (draft.scope === scope.id ? " is-selected" : "") +
          '" aria-pressed="' + (draft.scope === scope.id) + '" data-scope="' + scope.id + '">' +
          '<span class="choice-title">' + esc(scope.title) + "</span>" +
          '<span class="choice-desc">' + esc(scope.desc) + "</span>" +
          '<span class="choice-meta">' + esc(scope.meta) + "</span>" +
          "</button>"
        );
      })
      .join("");

    var extra = "";
    if (draft.scope === "stages") {
      extra =
        '<div class="stack"><div class="field-label">Which stages?</div>' +
        '<div class="choice-grid">' +
        state.boot.catalog.stages
          .map(function (stage) {
            var selected = draft.stages.indexOf(stage.id) !== -1;
            return (
              '<button type="button" class="choice' + (selected ? " is-selected" : "") +
              '" aria-pressed="' + selected + '" data-stage="' + stage.id + '">' +
              '<span class="choice-title">' + esc(stage.name) +
              (selected ? ' <span class="badge badge-accent">Selected</span>' : "") + "</span>" +
              '<span class="choice-desc">' + esc(stage.summary) + "</span>" +
              '<span class="choice-meta">Produces: ' + esc(stage.deliverables.join(", ")) + "</span>" +
              "</button>"
            );
          })
          .join("") +
        "</div></div>";
    } else if (draft.scope === "room-plan") {
      extra =
        '<div class="stack"><div class="field-label">Delivery template</div>' +
        '<div class="choice-grid">' +
        state.boot.catalog.roomTemplates
          .map(function (template) {
            return (
              '<button type="button" class="choice' + (draft.template === template.id ? " is-selected" : "") +
              '" aria-pressed="' + (draft.template === template.id) + '" data-template="' + template.id + '">' +
              '<span class="choice-title">' + esc(template.name) + "</span>" +
              '<span class="choice-desc">' + esc(template.summary) + "</span>" +
              "</button>"
            );
          })
          .join("") +
        "</div></div>";
    }

    return '<div class="stack"><div class="choice-grid">' + picker + "</div>" + extra + "</div>";
  }

  function stepOversight(draft) {
    if (draft.scope === "room-plan") {
      return (
        '<div class="banner banner-accent"><div><strong>No oversight settings needed</strong>' +
        '<div class="banner-body">Setting up a delivery room only records the mission, the team and the ' +
        "governance checklist. No agents run, so nothing needs approving.</div></div></div>"
      );
    }

    var levels = state.boot.catalog.oversightLevels
      .map(function (level) {
        return (
          '<button type="button" class="choice' + (draft.oversight === level.id ? " is-selected" : "") +
          '" aria-pressed="' + (draft.oversight === level.id) + '" data-oversight="' + level.id + '">' +
          '<span class="choice-title">' + esc(level.name) +
          (level.recommended ? ' <span class="badge badge-accent">Recommended</span>' : "") + "</span>" +
          '<span class="choice-desc">' + esc(level.summary) + "</span>" +
          '<span class="choice-meta">' + esc(level.detail) + "</span>" +
          "</button>"
        );
      })
      .join("");

    var engines = state.boot.catalog.runtimes
      .map(function (runtime) {
        return (
          '<button type="button" class="choice' + (draft.runtime === runtime.id ? " is-selected" : "") +
          '" aria-pressed="' + (draft.runtime === runtime.id) + '" data-runtime="' + runtime.id + '">' +
          '<span class="choice-title">' + esc(runtime.name) + "</span>" +
          '<span class="choice-desc">' + esc(runtime.summary) + "</span>" +
          "</button>"
        );
      })
      .join("");

    return (
      '<div class="stack">' +
      '<div><div class="field-label">How closely do you want to supervise the team?</div>' +
      '<p class="field-hint" style="margin-bottom:10px">You can stop a run at any time, whichever level you pick.</p>' +
      '<div class="choice-grid">' + levels + "</div></div>" +
      '<details class="disclosure" style="border:1px solid var(--border);border-radius:var(--radius)">' +
      "<summary>Advanced options</summary>" +
      '<div class="disclosure-body stack">' +
      '<div><div class="field-label">Execution engine</div>' +
      '<div class="choice-grid" style="margin-top:8px">' + engines + "</div></div>" +
      '<p class="field-hint">Currently using ' + esc(state.boot.readiness.provider.name) +
      " as the AI provider. Change it in your .env file.</p>" +
      "</div></details>" +
      "</div>"
    );
  }

  function stepReview(draft) {
    var rows = [];
    rows.push(["What", draft.brief || "(not set)"]);
    rows.push(["Project folder", draft.project || "Generated automatically"]);
    if (draft.scope === "room-plan") {
      rows.push(["Scope", "Delivery room setup only — no agents run"]);
      rows.push(["Template", titleCase(draft.template)]);
    } else {
      var stageIds = draft.scope === "delivery" ? state.boot.catalog.fullDeliveryStageIds : draft.stages;
      rows.push([
        "Stages",
        stageIds
          .map(function (id) { return stageMeta(id).name; })
          .join(" → "),
      ]);
      rows.push(["Oversight", oversightMeta(draft.oversight).name + " — " + oversightMeta(draft.oversight).summary]);
      rows.push(["AI provider", state.boot.readiness.provider.name]);
    }

    var note =
      draft.scope === "room-plan"
        ? ""
        : '<div class="banner banner-accent"><div><strong>What happens next</strong>' +
          '<div class="banner-body">Work starts immediately and you can watch each step live. ' +
          "Documents are written to your project folder as they are produced" +
          (draft.oversight === "automated" ? "." : ", and you will be asked to approve key actions along the way.") +
          "</div></div></div>";

    return (
      '<div class="stack">' +
      '<table class="table">' +
      "<tbody>" +
      rows
        .map(function (row) {
          return (
            '<tr><td style="width:170px" class="cell-muted">' + esc(row[0]) + "</td>" +
            '<td class="cell-strong">' + esc(row[1]) + "</td></tr>"
          );
        })
        .join("") +
      "</tbody></table>" +
      note +
      "</div>"
    );
  }

  // -- activity --------------------------------------------------------------

  function viewActivity() {
    if (!state.runs.length) {
      return (
        pageHeader("Activity", "Delivery runs", "Everything your agent team has worked on.") +
        '<div class="card">' +
        emptyState("◷", "Nothing has run yet", "Start a delivery and this page will show live progress for every stage.",
          '<a class="btn btn-primary" href="#/new">Start delivery</a>') +
        "</div>"
      );
    }

    return (
      pageHeader("Activity", "Delivery runs", "Everything your agent team has worked on.",
        '<a class="btn btn-primary" href="#/new">Start delivery</a>') +
      '<div class="card"><table class="table"><thead><tr>' +
      "<th>Run</th><th>Type</th><th>Stages</th><th>Status</th><th>Duration</th><th>Started</th>" +
      "</tr></thead><tbody>" +
      state.runs
        .map(function (run) {
          var done = run.stages.filter(function (stage) { return stage.status === "completed"; }).length;
          return (
            '<tr class="clickable" data-run="' + esc(run.id) + '">' +
            '<td class="cell-strong">' + esc(run.title) +
            '<div class="cell-muted">' + esc(truncate(run.brief, 70)) + "</div></td>" +
            "<td>" + esc(titleCase(run.kind)) + "</td>" +
            '<td class="cell-muted">' + (run.stages.length ? done + " / " + run.stages.length : "—") + "</td>" +
            "<td>" + statusBadge(run.status) +
            (run.pendingApprovals ? ' <span class="badge badge-warn">' + run.pendingApprovals + " to approve</span>" : "") +
            "</td>" +
            '<td class="cell-muted">' + esc(duration(run.startedAt, run.finishedAt)) + "</td>" +
            '<td class="cell-muted">' + esc(relative(run.startedAt || run.createdAt)) + "</td>" +
            "</tr>"
          );
        })
        .join("") +
      "</tbody></table></div>"
    );
  }

  function viewRun() {
    var run = state.run;
    if (!run) return '<div class="loading-state"><div class="spinner"></div><p>Loading run…</p></div>';

    var done = run.stages.filter(function (stage) { return stage.status === "completed"; }).length;
    var percent = run.stages.length ? Math.round((done / run.stages.length) * 100) : run.status === "completed" ? 100 : 0;
    var fillClass = run.status === "failed" ? " is-danger" : run.status === "completed" ? " is-ok" : "";

    var pending = (run.approvals || []).filter(function (approval) { return approval.status === "pending"; });
    var approvals = pending
      .map(function (approval) {
        // A stage checkpoint has no meaningful payload to show - its question
        // is already the title - so only tool approvals render the detail box.
        var payload =
          approval.tool === "stage_checkpoint"
            ? ""
            : Object.keys(approval.payload || {})
                .map(function (key) { return key + ": " + approval.payload[key]; })
                .join("\n");
        return (
          '<div class="approval-card">' +
          '<div><div class="approval-title">' + esc(approval.title) + "</div>" +
          '<div class="approval-detail">' + esc(approval.detail) + "</div></div>" +
          (payload ? '<div class="approval-payload">' + esc(payload) + "</div>" : "") +
          '<div class="row"><button class="btn btn-success" data-approve="' + esc(approval.id) + '">Approve</button>' +
          '<button class="btn btn-danger" data-decline="' + esc(approval.id) + '">Decline</button>' +
          '<span class="field-hint">Requested ' + esc(relative(approval.requestedAt)) + "</span></div>" +
          "</div>"
        );
      })
      .join("");

    var stages = run.stages.length
      ? '<div class="stage-list">' +
        run.stages
          .map(function (stage, index) {
            var marker = stage.status === "completed" ? "✓" : stage.status === "failed" ? "!" : String(index + 1);
            var note =
              stage.status === "completed"
                ? stage.fileCount + " document(s) · " + duration(stage.startedAt, stage.finishedAt)
                : stage.status === "running"
                ? "In progress · " + duration(stage.startedAt, null)
                : stage.status === "failed"
                ? "Did not complete"
                : stageMeta(stage.id).question || "Waiting";
            return (
              '<div class="stage-row is-' + esc(stage.status) + '">' +
              '<span class="stage-marker">' + esc(marker) + "</span>" +
              '<div><div class="stage-name">' + esc(stage.name) + "</div>" +
              '<div class="stage-note">' + esc(note) + "</div></div></div>"
            );
          })
          .join("") +
        "</div>"
      : "";

    var feed = state.events.length
      ? state.events
          .slice(-250)
          .map(function (event) {
            var meta = [];
            if (event.data && event.data.agent) meta.push(event.data.agent);
            if (event.data && event.data.label) meta.push(event.data.label);
            if (event.data && event.data.tool) meta.push(event.data.tool);
            if (event.data && event.data.iteration) meta.push("step " + event.data.iteration);
            return (
              '<div class="feed-item level-' + esc(event.level) + " kind-" + esc(event.kind) + '">' +
              '<span class="feed-time">' + esc(timeOf(event.at)) + "</span>" +
              '<span><span class="feed-message">' + esc(event.message) + "</span>" +
              (meta.length ? '<span class="feed-meta">' + esc(meta.join(" · ")) + "</span>" : "") +
              "</span></div>"
            );
          })
          .join("")
      : '<div class="feed-item"><span class="feed-time"></span><span class="feed-message">Waiting for the first update…</span></div>';

    var outputs = (run.outputs || [])
      .map(function (output) {
        var files = (output.files || [])
          .map(function (path) {
            var parts = path.split("/");
            var project = parts.shift();
            return (
              '<button class="file-row" data-doc-project="' + esc(project) + '" data-doc-path="' + esc(parts.join("/")) + '">' +
              '<span class="file-icon" aria-hidden="true">▤</span>' +
              '<span class="file-name">' + esc(parts.join("/")) + "</span></button>"
            );
          })
          .join("");
        return (
          '<details class="disclosure"' + (output.success ? "" : " open") + ">" +
          "<summary>" + esc(output.stageName) + " — " +
          (output.success ? "completed" : "did not complete") +
          (output.files && output.files.length ? " · " + output.files.length + " document(s)" : "") +
          "</summary>" +
          '<div class="disclosure-body stack">' +
          '<div class="markdown">' + renderMarkdown(truncate(output.output, 12000)) + "</div>" +
          (files ? '<div class="file-list">' + files + "</div>" : "") +
          "</div></details>"
        );
      })
      .join("");

    var actions =
      (isActive(run.status) ? '<button class="btn btn-danger" data-stop-run>Stop run</button>' : "") +
      '<a class="btn btn-secondary" href="#/activity">All runs</a>' +
      (run.project ? '<a class="btn btn-secondary" href="#/documents/' + encodeURIComponent(run.project) + '">Open documents</a>' : "");

    return (
      pageHeader(titleCase(run.kind) + " run", run.title, run.brief, actions) +
      '<div class="stack">' +
      (approvals ? '<div class="stack">' + approvals + "</div>" : "") +
      '<div class="card card-pad"><div class="row" style="margin-bottom:10px">' +
      statusBadge(run.status) +
      '<span class="field-hint">' + esc(run.summary || (isActive(run.status) ? "Work in progress" : "")) + "</span>" +
      '<div class="spacer"></div>' +
      '<span class="field-hint">' + esc(oversightMeta(run.oversight).name) + " oversight · " +
      esc(duration(run.startedAt, run.finishedAt)) + "</span></div>" +
      '<div class="progress-track"><div class="progress-fill' + fillClass + '" style="width:' + percent + '%"></div></div>' +
      (run.error ? '<p class="field-hint" style="margin-top:10px;color:var(--danger)">' + esc(run.error) + "</p>" : "") +
      "</div>" +
      '<div class="split">' +
      '<div class="card"><div class="card-header"><h2>Stages</h2></div>' + (stages || emptyState("◇", "No stages", "This run does not use the stage lifecycle.")) + "</div>" +
      '<div class="card"><div class="card-header"><div><h2>Live activity</h2>' +
      '<div class="sub">What the agents are doing, as it happens</div></div>' +
      (isActive(run.status) ? '<span class="badge badge-accent"><span class="dot dot-pulse"></span>Live</span>' : "") +
      "</div>" +
      '<div class="feed" id="feed">' + feed + "</div>" +
      (outputs || "") +
      '<details class="disclosure"><summary>Technical log</summary>' +
      '<div class="disclosure-body"><div class="console-log">' + esc((run.console || []).join("\n")) + "</div></div></details>" +
      "</div></div></div>"
    );
  }

  // -- documents -------------------------------------------------------------

  function viewDocuments() {
    var project = state.route.params.project;
    if (!project) {
      return (
        pageHeader("Documents", "Project library", "Every document your delivery team has produced.") +
        (state.projects.length
          ? '<div class="grid grid-3">' +
            state.projects
              .map(function (item) {
                return (
                  '<button class="card card-pad" style="text-align:left;cursor:pointer;font:inherit;color:inherit" ' +
                  'data-project="' + esc(item.name) + '">' +
                  '<div class="row"><strong>' + esc(item.name) + "</strong>" +
                  (item.room ? '<span class="badge badge-accent">Delivery room</span>' : "") + "</div>" +
                  '<p class="cell-muted" style="margin-top:6px">' +
                  esc(item.room && item.room.mission ? truncate(item.room.mission, 96) : item.fileCount + " files") +
                  "</p>" +
                  '<p class="stat-note">Updated ' + esc(relative(item.modifiedAt)) + " · " + item.fileCount + " files</p>" +
                  "</button>"
                );
              })
              .join("") +
            "</div>"
          : '<div class="card">' +
            emptyState("▤", "No projects yet", "Documents appear here once a delivery stage finishes.",
              '<a class="btn btn-primary" href="#/new">Start delivery</a>') +
            "</div>")
      );
    }

    var path = state.files ? state.files.path : "";
    var segments = path ? path.split("/") : [];
    var crumbs =
      '<div class="breadcrumbs"><button data-crumb="">' + esc(project) + "</button>" +
      segments
        .map(function (segment, index) {
          var target = segments.slice(0, index + 1).join("/");
          return '<span class="sep">/</span><button data-crumb="' + esc(target) + '">' + esc(segment) + "</button>";
        })
        .join("") +
      "</div>";

    var listing = state.files
      ? '<div class="file-list">' +
        (path ? '<button class="file-row" data-crumb="' + esc(segments.slice(0, -1).join("/")) +
          '"><span class="file-icon">↰</span><span class="file-name">Up one level</span></button>' : "") +
        state.files.folders
          .map(function (folder) {
            return (
              '<button class="file-row" data-folder="' + esc(folder.path) + '">' +
              '<span class="file-icon" aria-hidden="true">▸</span>' +
              '<span class="file-name">' + esc(folder.name) + "</span></button>"
            );
          })
          .join("") +
        state.files.files
          .map(function (file) {
            var selected = state.doc && state.doc.path === file.path;
            return (
              '<button class="file-row' + (selected ? " is-selected" : "") + '" data-file="' + esc(file.path) + '">' +
              '<span class="file-icon" aria-hidden="true">' + (file.kind === "markdown" ? "▤" : "◦") + "</span>" +
              '<span class="file-name">' + esc(file.name) + "</span>" +
              '<span class="file-size">' + esc(fileSize(file.size)) + "</span></button>"
            );
          })
          .join("") +
        (!state.files.folders.length && !state.files.files.length
          ? emptyState("▤", "Empty folder", "Nothing has been written here yet.")
          : "") +
        "</div>"
      : '<div class="loading-state"><div class="spinner"></div></div>';

    var viewer = state.doc
      ? '<div class="card"><div class="card-header"><div><h2>' + esc(state.doc.path.split("/").pop()) + "</h2>" +
        '<div class="sub">' + esc(fileSize(state.doc.size)) + " · updated " + esc(relative(state.doc.modifiedAt)) + "</div></div>" +
        '<button class="btn btn-sm btn-secondary" data-copy-doc>Copy text</button></div>' +
        '<div class="card-body doc-scroll">' +
        (state.doc.kind === "binary"
          ? '<p class="field-hint">This file type cannot be previewed in the browser.</p>'
          : state.doc.kind === "markdown"
          ? '<div class="markdown">' + renderMarkdown(state.doc.content) + "</div>"
          : '<pre class="console-log" style="max-height:none">' + esc(state.doc.content) + "</pre>") +
        (state.doc.truncated ? '<p class="field-hint" style="margin-top:12px">Preview truncated — open the file on disk to see all of it.</p>' : "") +
        "</div></div>"
      : '<div class="card">' + emptyState("▤", "Select a document", "Choose a file on the left to read it here.") + "</div>";

    return (
      pageHeader("Documents", project, "", '<a class="btn btn-secondary" href="#/documents">All projects</a>') +
      '<div class="split">' +
      '<div class="card"><div class="card-header">' + crumbs + "</div>" + listing + "</div>" +
      viewer +
      "</div>"
    );
  }

  // -- delivery rooms --------------------------------------------------------

  function viewRooms() {
    var project = state.route.params.project;
    if (project) return viewRoomDetail();

    return (
      pageHeader(
        "Delivery rooms",
        "Delivery rooms",
        "A delivery room holds the mission, the assigned team, the decisions taken and anything blocking progress.",
        '<a class="btn btn-primary" href="#/new">Set up a room</a>'
      ) +
      (state.rooms.length
        ? '<div class="card"><table class="table"><thead><tr>' +
          "<th>Project</th><th>Mission</th><th>Template</th><th>Status</th><th>Blockers</th><th>Updated</th>" +
          "</tr></thead><tbody>" +
          state.rooms
            .map(function (room) {
              return (
                '<tr class="clickable" data-room="' + esc(room.project) + '">' +
                '<td class="cell-strong">' + esc(room.project) + "</td>" +
                '<td class="cell-muted">' + esc(truncate(room.mission, 70)) + "</td>" +
                "<td>" + esc(titleCase(room.template)) + "</td>" +
                "<td>" + esc(titleCase(room.status)) + "</td>" +
                '<td class="num">' +
                (room.openBlockers
                  ? '<span class="badge badge-danger">' + room.openBlockers + "</span>"
                  : '<span class="badge badge-ok">0</span>') +
                "</td>" +
                '<td class="cell-muted">' + esc(relative(room.updatedAt)) + "</td>" +
                "</tr>"
              );
            })
            .join("") +
          "</tbody></table></div>"
        : '<div class="card">' +
          emptyState("◇", "No delivery rooms yet", "Set one up to give a project a mission, a team and a governance trail.",
            '<a class="btn btn-primary" href="#/new">Set up a room</a>') +
          "</div>")
    );
  }

  function viewRoomDetail() {
    if (!state.room) return '<div class="loading-state"><div class="spinner"></div><p>Loading room…</p></div>';

    var status = state.room.status;
    var health = status.health || {};
    var project = state.route.params.project;

    var agents = state.room.agents.length
      ? '<table class="table"><thead><tr><th>Role</th><th>Agent</th><th>Stage</th><th>Status</th></tr></thead><tbody>' +
        state.room.agents
          .map(function (agent) {
            return (
              "<tr><td class=\"cell-strong\">" + esc(agent.role) + "</td>" +
              '<td class="cell-muted">' + esc(agent.agent_name) + "</td>" +
              "<td>" + esc(stageMeta(agent.phase).name) + "</td>" +
              "<td>" + esc(titleCase(agent.status)) + "</td></tr>"
            );
          })
          .join("") +
        "</tbody></table>"
      : emptyState("◇", "No team assigned", "The template did not assign any roles.");

    function listCard(title, subtitle, items, render) {
      return (
        '<div class="card"><div class="card-header"><div><h2>' + esc(title) + "</h2>" +
        '<div class="sub">' + esc(subtitle) + "</div></div>" +
        '<span class="badge">' + items.length + "</span></div>" +
        (items.length
          ? '<div class="card-body tight"><div class="file-list">' +
            items.map(render).join("") +
            "</div></div>"
          : emptyState("—", "Nothing recorded", "This section fills in as the room progresses."))
        + "</div>"
      );
    }

    var blockers = listCard("Blockers", "Anything holding delivery up", state.room.blockers, function (blocker) {
      var severity = blocker.severity === "critical" || blocker.severity === "high" ? "badge-danger" : "badge-warn";
      return (
        '<div class="file-row" style="cursor:default"><span class="file-icon">!</span>' +
        '<span class="file-name" style="white-space:normal"><strong>' + esc(blocker.title) + "</strong>" +
        '<div class="cell-muted">' + esc(blocker.suggested_resolution) + "</div></span>" +
        '<span class="badge ' + severity + '">' + esc(titleCase(blocker.severity)) + "</span></div>"
      );
    });

    var decisions = listCard("Decisions", "Choices made, and why", state.room.decisions, function (decision) {
      return (
        '<div class="file-row" style="cursor:default"><span class="file-icon">◆</span>' +
        '<span class="file-name" style="white-space:normal"><strong>' + esc(decision.title) + "</strong>" +
        '<div class="cell-muted">' + esc(decision.decision) + "</div></span></div>"
      );
    });

    var handoffs = listCard("Handoffs", "Work passed between roles", state.room.handoffs, function (handoff) {
      return (
        '<div class="file-row" style="cursor:default"><span class="file-icon">→</span>' +
        '<span class="file-name" style="white-space:normal"><strong>' +
        esc(handoff.from_agent) + " → " + esc(handoff.to_agent) + "</strong>" +
        '<div class="cell-muted">' + esc(handoff.summary) + "</div></span></div>"
      );
    });

    var goals = (status.goals || [])
      .map(function (goal) { return "<li>" + esc(goal) + "</li>"; })
      .join("");
    var risks = (status.risks || [])
      .map(function (risk) { return "<li>" + esc(risk) + "</li>"; })
      .join("");
    var actions = (health.recommended_actions || status.next_actions || [])
      .map(function (action) { return "<li>" + esc(action) + "</li>"; })
      .join("");

    return (
      pageHeader(
        "Delivery room",
        project,
        status.mission,
        '<button class="btn btn-primary" data-run-room>Run this room</button>' +
        '<button class="btn btn-secondary" data-export-room>Export dashboard</button>' +
        '<a class="btn btn-secondary" href="#/rooms">All rooms</a>'
      ) +
      '<div class="stack">' +
      '<div class="grid grid-4">' +
      '<div class="stat"><div class="health-ring">' + healthRing(health.overall) +
      '<div><div class="health-value">' + (health.overall || 0) + '<span style="font-size:15px;color:var(--text-muted)">/100</span></div>' +
      '<div class="health-caption">' + esc(titleCase(health.status || "unknown")) + " · confidence " +
      (health.confidence || 0) + "</div></div></div></div>" +
      '<div class="stat"><div class="stat-label">Team</div><div class="stat-value">' +
      (status.completed_agent_count || 0) + "/" + (status.agent_count || 0) +
      '</div><div class="stat-note">Roles complete</div></div>' +
      '<div class="stat"><div class="stat-label">Open blockers</div><div class="stat-value">' +
      (status.open_blocker_count || 0) + '</div><div class="stat-note">Need resolution</div></div>' +
      '<div class="stat"><div class="stat-label">Stage</div><div class="stat-value" style="font-size:20px">' +
      esc(status.active_phase ? stageMeta(status.active_phase).name : "Not started") + '</div><div class="stat-note">' +
      esc(titleCase(status.template)) + " template</div></div>" +
      "</div>" +
      '<div class="grid grid-2" style="align-items:start">' +
      '<div class="card"><div class="card-header"><h2>Mission</h2></div><div class="card-body stack">' +
      (goals ? '<div><div class="field-label">Goals</div><ul>' + goals + "</ul></div>" : "") +
      (risks ? '<div><div class="field-label">Risks</div><ul>' + risks + "</ul></div>" : "") +
      (actions ? '<div><div class="field-label">Recommended next actions</div><ul>' + actions + "</ul></div>" : "") +
      "</div></div>" +
      '<div class="card"><div class="card-header"><div><h2>Team</h2>' +
      '<div class="sub">Roles assigned by the ' + esc(status.template) + " template</div></div></div>" + agents + "</div>" +
      "</div>" +
      '<div class="grid grid-3">' + blockers + decisions + handoffs + "</div>" +
      "</div>"
    );
  }

  // -- setup -----------------------------------------------------------------

  function viewSetup() {
    var readiness = state.readiness || state.boot.readiness;
    var icons = { ok: "✓", error: "!", optional: "–" };

    return (
      pageHeader(
        "Setup",
        "System check",
        "Everything the console needs in order to run your delivery team.",
        '<button class="btn btn-secondary" data-refresh-readiness>Re-check</button>'
      ) +
      '<div class="stack">' +
      (readiness.ready
        ? '<div class="banner"><div><strong>Ready to go</strong><div class="banner-body">' +
          "All required checks passed. You can start a delivery whenever you like.</div></div></div>"
        : '<div class="banner banner-danger"><div><strong>' + readiness.blockingCount +
          " item(s) need attention</strong><div class=\"banner-body\">" +
          "Agents cannot run until these are resolved. Each item below has the fix next to it." +
          "</div></div></div>") +
      '<div class="grid grid-3">' +
      '<div class="stat"><div class="stat-label">AI provider</div><div class="stat-value" style="font-size:20px">' +
      esc(readiness.provider.name) + '</div><div class="stat-note">Set with LLM_PROVIDER in .env</div></div>' +
      '<div class="stat"><div class="stat-label">Execution engine</div><div class="stat-value" style="font-size:20px">' +
      esc(readiness.runtime === "pi" ? "pi.dev" : "Built-in") + '</div><div class="stat-note">Set with AGENT_RUNTIME in .env</div></div>' +
      '<div class="stat"><div class="stat-label">Working folder</div><div class="stat-value" style="font-size:14px;word-break:break-all">' +
      esc(readiness.workingDirectory) + '</div><div class="stat-note">Documents are saved under generated/</div></div>' +
      "</div>" +
      '<div class="card"><div class="card-header"><div><h2>Checks</h2>' +
      '<div class="sub">Settings are read from your .env file when the console starts</div></div></div>' +
      readiness.checks
        .map(function (check) {
          return (
            '<div class="check-row">' +
            '<span class="check-icon ' + esc(check.status) + '">' + esc(icons[check.status] || "•") + "</span>" +
            "<div><div class=\"check-label\">" + esc(check.label) + "</div>" +
            '<div class="check-detail">' + esc(check.detail) + "</div>" +
            (check.fix ? '<div class="check-fix">' + esc(check.fix) + "</div>" : "") +
            "</div></div>"
          );
        })
        .join("") +
      "</div>" +
      '<div class="card card-pad"><h2>Prefer the command line?</h2>' +
      '<p class="field-hint" style="margin-top:6px">Everything here maps to a CLI command. ' +
      "For example, a full delivery is <code>python main.py --workflow --input \"…\"</code>, " +
      "and a single stage is <code>python main.py --phase feasibility --input \"…\"</code>.</p></div>" +
      "</div>"
    );
  }

  // ------------------------------------------------------------------ render

  function render() {
    var main = qs("#main");
    var html;
    if (!state.boot) {
      html = '<div class="loading-state"><div class="spinner"></div><p>Starting the console…</p></div>';
    } else if (state.routeError) {
      html =
        pageHeader("", "That page could not be loaded", state.routeError) +
        '<div class="card">' +
        emptyState(
          "!",
          "Nothing to show here",
          "The item may have been renamed or removed. Try again from the Overview.",
          '<a class="btn btn-primary" href="#/overview">Back to Overview</a>'
        ) +
        "</div>";
    } else {
      switch (state.route.name) {
        case "new": html = viewNew(); break;
        case "activity": html = viewActivity(); break;
        case "run": html = viewRun(); break;
        case "documents": html = viewDocuments(); break;
        case "rooms": html = viewRooms(); break;
        case "setup": html = viewSetup(); break;
        default: html = viewOverview();
      }
    }
    main.innerHTML = html;
    bind();
    updateChrome();
  }

  function updateChrome() {
    var route = state.route.name;
    var navRoute = route === "run" ? "activity" : route;
    qsa(".nav-item").forEach(function (item) {
      item.classList.toggle("is-active", item.dataset.route === navRoute);
    });

    var active = state.runs.filter(function (run) { return isActive(run.status); }).length;
    var badge = qs("#nav-active-count");
    badge.hidden = !active;
    badge.textContent = String(active);

    var readiness = state.readiness || (state.boot && state.boot.readiness);
    var setupBadge = qs("#nav-setup-count");
    if (readiness && !readiness.ready) {
      setupBadge.hidden = false;
      setupBadge.textContent = String(readiness.blockingCount);
    } else {
      setupBadge.hidden = true;
    }

    if (readiness) {
      qs("#sidebar-meta").textContent = readiness.provider.name + " · " +
        (readiness.runtime === "pi" ? "pi.dev engine" : "built-in engine");
    }
  }

  // ------------------------------------------------------------------- binds

  function bind() {
    on("[data-run]", "click", function (event) {
      go("#/runs/" + event.currentTarget.dataset.run);
    });
    on("[data-project]", "click", function (event) {
      go("#/documents/" + encodeURIComponent(event.currentTarget.dataset.project));
    });
    on("[data-room]", "click", function (event) {
      go("#/rooms/" + encodeURIComponent(event.currentTarget.dataset.room));
    });
    on("[data-doc-project]", "click", function (event) {
      var node = event.currentTarget;
      go("#/documents/" + encodeURIComponent(node.dataset.docProject) + "?file=" + encodeURIComponent(node.dataset.docPath));
    });
    on("[data-run-stage]", "click", function (event) {
      ensureDraft();
      state.draft.scope = "stages";
      state.draft.stages = [event.currentTarget.dataset.runStage];
      state.draft.step = 1;
      go("#/new");
    });

    bindWizard();
    bindRun();
    bindDocuments();
    bindRoom();

    on("[data-refresh-readiness]", "click", function () {
      api.readiness().then(function (data) {
        state.readiness = data;
        toast("Re-checked", data.ready ? "Everything is ready." : data.blockingCount + " item(s) still need attention.",
          data.ready ? "success" : "error");
        render();
      }).catch(fail);
    });
  }

  function bindWizard() {
    var draft = state.draft;
    if (!draft) return;

    var brief = qs("#brief");
    if (brief) {
      brief.addEventListener("input", function () { draft.brief = brief.value; });
      brief.focus();
    }
    var project = qs("#project");
    if (project) project.addEventListener("input", function () { draft.project = project.value; });

    on("[data-example]", "click", function (event) {
      draft.brief = EXAMPLES[Number(event.currentTarget.dataset.example)];
      render();
    });
    on("[data-scope]", "click", function (event) {
      draft.scope = event.currentTarget.dataset.scope;
      render();
    });
    on("[data-stage]", "click", function (event) {
      var id = event.currentTarget.dataset.stage;
      var index = draft.stages.indexOf(id);
      if (index === -1) draft.stages.push(id); else draft.stages.splice(index, 1);
      var order = state.boot.catalog.stages.map(function (stage) { return stage.id; });
      draft.stages.sort(function (a, b) { return order.indexOf(a) - order.indexOf(b); });
      render();
    });
    on("[data-oversight]", "click", function (event) {
      draft.oversight = event.currentTarget.dataset.oversight;
      render();
    });
    on("[data-runtime]", "click", function (event) {
      draft.runtime = event.currentTarget.dataset.runtime;
      render();
    });
    on("[data-template]", "click", function (event) {
      draft.template = event.currentTarget.dataset.template;
      render();
    });
    on("[data-step-back]", "click", function () {
      draft.step = Math.max(1, draft.step - 1);
      render();
    });
    on("[data-step-next]", "click", function () {
      if (draft.step === 1 && draft.brief.trim().length < 10) {
        toast("A little more detail", "Describe what you want to deliver in at least 10 characters.", "error");
        return;
      }
      if (draft.step === 2 && draft.scope === "stages" && !draft.stages.length) {
        toast("Choose a stage", "Select at least one stage to run.", "error");
        return;
      }
      draft.step = Math.min(4, draft.step + 1);
      render();
    });
    on("[data-start-run]", "click", startFromDraft);
  }

  function startFromDraft() {
    if (state.busy) return;
    var draft = state.draft;
    state.busy = true;
    qsa("[data-start-run]").forEach(function (button) {
      button.disabled = true;
      button.textContent = "Starting…";
    });

    var done = function () { state.busy = false; };

    if (draft.scope === "room-plan") {
      api
        .createRoom({ mission: draft.brief, project: draft.project || null, template: draft.template, overwrite: false })
        .then(function (result) {
          state.draft = null;
          toast("Delivery room created", result.project, "success");
          return loadRooms().then(function () { go("#/rooms/" + encodeURIComponent(result.project)); });
        })
        .catch(fail)
        .then(done, done);
      return;
    }

    api
      .startRun({
        kind: draft.scope === "delivery" ? "delivery" : "stage",
        brief: draft.brief,
        stages: draft.stages,
        oversight: draft.oversight,
        runtime: draft.runtime,
        project: draft.project || null,
        template: draft.template,
      })
      .then(function (run) {
        state.draft = null;
        toast("Delivery started", "Watch progress live on the run page.", "success");
        return loadRuns().then(function () { go("#/runs/" + run.id); });
      })
      .catch(fail)
      .then(done, done);
  }

  function bindRun() {
    on("[data-approve]", "click", function (event) {
      respondApproval(event.currentTarget.dataset.approve, true);
    });
    on("[data-decline]", "click", function (event) {
      respondApproval(event.currentTarget.dataset.decline, false);
    });
    on("[data-stop-run]", "click", function () {
      if (!state.run) return;
      api
        .stopRun(state.run.id)
        .then(function () { toast("Stopping", "The step in progress will finish first."); })
        .catch(fail);
    });
    var feed = qs("#feed");
    if (feed) feed.scrollTop = feed.scrollHeight;
  }

  function respondApproval(approvalId, approved) {
    if (!state.run) return;
    qsa("[data-approve],[data-decline]").forEach(function (button) { button.disabled = true; });
    api
      .approve(state.run.id, approvalId, approved)
      .then(function () {
        toast(approved ? "Approved" : "Declined", approved ? "The agent will continue." : "The agent will skip that action.");
        return refreshRun();
      })
      .catch(fail);
  }

  function bindDocuments() {
    on("[data-folder]", "click", function (event) {
      loadFiles(state.route.params.project, event.currentTarget.dataset.folder);
    });
    on("[data-crumb]", "click", function (event) {
      loadFiles(state.route.params.project, event.currentTarget.dataset.crumb);
    });
    on("[data-file]", "click", function (event) {
      loadDoc(state.route.params.project, event.currentTarget.dataset.file);
    });
    on("[data-copy-doc]", "click", function () {
      if (!state.doc || !navigator.clipboard) return;
      navigator.clipboard.writeText(state.doc.content).then(function () {
        toast("Copied", "The document text is on your clipboard.", "success");
      });
    });
  }

  function bindRoom() {
    on("[data-export-room]", "click", function () {
      api
        .exportRoom(state.route.params.project)
        .then(function (result) { toast("Dashboard exported", result.path, "success"); })
        .catch(fail);
    });
    on("[data-run-room]", "click", function () {
      if (!state.room) return;
      api
        .startRun({
          kind: "room",
          brief: state.room.status.mission,
          project: state.route.params.project,
          template: state.room.status.template,
          oversight: "automated",
        })
        .then(function (run) {
          toast("Delivery room running", "Agents are working through the mission.", "success");
          return loadRuns().then(function () { go("#/runs/" + run.id); });
        })
        .catch(fail);
    });
  }

  // ------------------------------------------------------------------ loaders

  function loadRuns() {
    return api.runs().then(function (data) {
      state.runs = data.runs;
    });
  }

  function loadProjects() {
    return api.projects().then(function (data) {
      state.projects = data.projects;
      state.recent = data.recent;
    });
  }

  function loadRooms() {
    return api.rooms().then(function (data) {
      state.rooms = data.rooms;
    });
  }

  function loadFiles(project, path) {
    return api
      .files(project, path)
      .then(function (data) {
        state.files = data;
        render();
      })
      .catch(fail);
  }

  function loadDoc(project, path) {
    return api
      .file(project, path)
      .then(function (data) {
        state.doc = data;
        render();
      })
      .catch(fail);
  }

  function refreshRun() {
    if (!state.run) return Promise.resolve();
    return api.runEvents(state.run.id, state.runCursor).then(function (data) {
      if (data.events.length) {
        state.events = state.events.concat(data.events);
        state.runCursor = data.cursor;
      }
      var changed =
        data.run.status !== state.run.status ||
        data.events.length ||
        data.approvals.length !== (state.run.approvals || []).filter(function (a) { return a.status === "pending"; }).length;
      if (!changed) return null;
      return api.run(state.run.id).then(function (detail) {
        state.run = detail;
        var index = state.runs.findIndex(function (item) { return item.id === detail.id; });
        if (index !== -1) state.runs[index] = detail;
        render();
      });
    });
  }

  // ------------------------------------------------------------------- router

  function go(hash) {
    if (window.location.hash === hash) route();
    else window.location.hash = hash;
  }

  function parseRoute() {
    var raw = (window.location.hash || "#/overview").slice(1);
    var queryIndex = raw.indexOf("?");
    var query = {};
    if (queryIndex !== -1) {
      new URLSearchParams(raw.slice(queryIndex + 1)).forEach(function (value, key) {
        query[key] = value;
      });
      raw = raw.slice(0, queryIndex);
    }
    var parts = raw.split("/").filter(Boolean);
    var head = parts[0] || "overview";
    if (head === "runs") return { name: "run", params: { id: parts[1], query: query } };
    if (head === "documents") return { name: "documents", params: { project: parts[1] ? decodeURIComponent(parts[1]) : null, query: query } };
    if (head === "rooms") return { name: "rooms", params: { project: parts[1] ? decodeURIComponent(parts[1]) : null, query: query } };
    return { name: head, params: { query: query } };
  }

  function route() {
    stopPolling();
    var next = parseRoute();
    var previous = state.route;
    state.route = next;
    state.routeError = null;

    if (next.name !== "run" || !previous || previous.params.id !== next.params.id) {
      if (next.name === "run") {
        state.run = null;
        state.events = [];
        state.runCursor = 0;
      }
    }
    if (next.name !== "documents" || (previous.params && previous.params.project !== next.params.project)) {
      state.files = null;
      state.doc = null;
    }

    render();

    var loader;
    switch (next.name) {
      case "overview":
        loader = Promise.all([loadRuns(), loadProjects()]);
        break;
      case "activity":
        loader = loadRuns();
        break;
      case "run":
        loader = api.run(next.params.id).then(function (detail) {
          state.run = detail;
          state.events = [];
          state.runCursor = 0;
          return api.runEvents(detail.id, 0).then(function (data) {
            state.events = data.events;
            state.runCursor = data.cursor;
          });
        });
        break;
      case "documents":
        loader = next.params.project
          ? api.files(next.params.project, "").then(function (data) {
              state.files = data;
              if (next.params.query && next.params.query.file) {
                return api.file(next.params.project, next.params.query.file).then(function (doc) {
                  state.doc = doc;
                });
              }
              return null;
            })
          : loadProjects();
        break;
      case "rooms":
        loader = next.params.project
          ? api.room(next.params.project).then(function (data) { state.room = data; })
          : loadRooms();
        break;
      case "setup":
        loader = api.readiness().then(function (data) { state.readiness = data; });
        break;
      default:
        loader = Promise.resolve();
    }

    loader
      .then(function () { render(); startPolling(); })
      .catch(function (error) {
        state.routeError = error && error.message ? error.message : String(error);
        render();
      });
  }

  function startPolling() {
    stopPolling();
    if (state.route.name === "run") {
      poller = setInterval(function () {
        if (!state.run) return;
        if (!isActive(state.run.status)) { stopPolling(); return; }
        refreshRun().catch(function () { /* transient: keep polling */ });
      }, 1500);
    } else if (state.route.name === "activity" || state.route.name === "overview") {
      poller = setInterval(function () {
        loadRuns()
          .then(function () {
            if (state.runs.some(function (run) { return isActive(run.status); })) render();
            else updateChrome();
          })
          .catch(function () {});
      }, 4000);
    }
  }

  function stopPolling() {
    if (poller) {
      clearInterval(poller);
      poller = null;
    }
  }

  // -------------------------------------------------------------------- theme

  function initTheme() {
    var stored = null;
    try { stored = window.localStorage.getItem("dsdm-console-theme"); } catch (error) { /* private mode */ }
    var prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    setTheme(stored || (prefersDark ? "dark" : "light"));

    qs("#theme-toggle").addEventListener("click", function () {
      setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
    });
  }

  function setTheme(theme) {
    document.documentElement.dataset.theme = theme;
    qs("#theme-toggle-label").textContent = theme === "dark" ? "Light mode" : "Dark mode";
    try { window.localStorage.setItem("dsdm-console-theme", theme); } catch (error) { /* private mode */ }
  }

  // --------------------------------------------------------------------- boot

  function start() {
    initTheme();
    window.addEventListener("hashchange", route);
    api
      .bootstrap()
      .then(function (data) {
        state.boot = data;
        state.readiness = data.readiness;
        return Promise.all([loadRuns(), loadProjects()]);
      })
      .then(function () { route(); })
      .catch(function (error) {
        qs("#main").innerHTML =
          '<div class="card card-pad"><h1>The console could not start</h1>' +
          '<p class="lede" style="color:var(--text-muted);margin-top:8px">' + esc(error.message) + "</p>" +
          '<p class="field-hint" style="margin-top:12px">If an access token is required, open the exact URL printed ' +
          "in the terminal when the console started.</p></div>";
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
