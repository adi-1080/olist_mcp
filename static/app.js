// Olist E-Commerce Analytics Frontend Application Logic

let activeChartInstance = null;
let pinnedChartInstances = {};
let currentQueryResponse = null;

document.addEventListener("DOMContentLoaded", () => {
    fetchHealthStatus();
    loadPinnedDashboard();
});

async function fetchHealthStatus() {
    try {
        const res = await fetch("/api/health");
        const data = await res.json();
        const modeToggle = document.getElementById("modeToggle");
        if (modeToggle) {
            // Checkbox checked = Fallback, unchecked = LLM
            modeToggle.checked = (data.agent_mode.toLowerCase() === "fallback");
        }
    } catch (e) {
        console.warn("Could not fetch health status:", e);
    }
}

async function handleModeToggle(event) {
    const isFallback = event.target.checked;
    const targetMode = isFallback ? "fallback" : "llm";

    try {
        const res = await fetch("/api/config/mode", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mode: targetMode })
        });
        if (!res.ok) {
            throw new Error(`Server status ${res.status}`);
        }
        const data = await res.json();
        console.log(`Agent mode updated to: ${data.agent_mode}`);
    } catch (e) {
        console.error("Error updating agent mode:", e);
        // Revert checkbox state on failure
        event.target.checked = !isFallback;
    }
}

function getSelectedMode() {
    const modeToggle = document.getElementById("modeToggle");
    if (!modeToggle) return "llm";
    return modeToggle.checked ? "fallback" : "llm";
}

function switchTab(tabName) {
    document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
    document.querySelectorAll(".tab-section").forEach(sec => sec.classList.remove("active"));

    if (tabName === "chat") {
        document.getElementById("tabChatBtn").classList.add("active");
        document.getElementById("chatSection").classList.add("active");
    } else {
        document.getElementById("tabDashboardBtn").classList.add("active");
        document.getElementById("dashboardSection").classList.add("active");
        loadPinnedDashboard();
    }
}

function submitSampleQuery(queryText) {
    const input = document.getElementById("queryInput");
    input.value = queryText;
    document.getElementById("queryForm").requestSubmit();
}

async function handleQuerySubmit(event) {
    event.preventDefault();
    const input = document.getElementById("queryInput");
    const query = input.value.trim();
    if (!query) return;

    const resultContainer = document.getElementById("resultContainer");
    const loadingIndicator = document.getElementById("loadingIndicator");
    const responseCard = document.getElementById("responseCard");
    const errorBox = document.getElementById("errorBox");

    resultContainer.classList.remove("hidden");
    loadingIndicator.classList.remove("hidden");
    responseCard.classList.add("hidden");
    errorBox.classList.add("hidden");

    try {
        const activeMode = getSelectedMode();
        const res = await fetch("/api/query", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: query, mode: activeMode })
        });

        if (!res.ok) {
            throw new Error(`Server returned status ${res.status}`);
        }

        const data = await res.json();
        currentQueryResponse = data;
        loadingIndicator.classList.add("hidden");

        if (data.is_out_of_bounds || data.empty_result || data.error_message) {
            displayGuardrailError(data);
        } else {
            displayChartResponse(data);
        }
    } catch (err) {
        loadingIndicator.classList.add("hidden");
        displayGuardrailError({
            query: query,
            error_message: `Network/Server Error: ${err.message}`
        });
    }
}

function displayGuardrailError(data) {
    const responseCard = document.getElementById("responseCard");
    const errorBox = document.getElementById("errorBox");
    const errorText = document.getElementById("errorText");

    responseCard.classList.remove("hidden");
    errorBox.classList.remove("hidden");
    
    document.getElementById("responseQueryTitle").textContent = `Query: "${data.query}"`;
    document.getElementById("chartTypeBadge").textContent = "Guardrail Triggered";
    document.getElementById("toolCalledBadge").textContent = data.tool_called || "none";
    document.getElementById("agentModeBadge").textContent = `mode: ${data.agent_mode || "fallback"}`;

    document.getElementById("assumptionsBox").classList.add("hidden");
    document.getElementById("insightBanner").classList.add("hidden");
    document.querySelector(".justification-box").classList.add("hidden");
    document.querySelector(".chart-wrapper").classList.add("hidden");
    document.getElementById("pinBtn").classList.add("hidden");

    errorText.textContent = data.error_message || data.insight || "No data available for this query.";
}

function displayChartResponse(data) {
    const responseCard = document.getElementById("responseCard");
    responseCard.classList.remove("hidden");
    document.getElementById("errorBox").classList.add("hidden");

    document.getElementById("responseQueryTitle").textContent = `"${data.query}"`;
    document.getElementById("chartTypeBadge").textContent = `${data.chart_type.toUpperCase()} CHART`;
    document.getElementById("toolCalledBadge").textContent = `tool: ${data.tool_called}`;
    document.getElementById("agentModeBadge").textContent = `mode: ${data.agent_mode}`;
    document.getElementById("pinBtn").classList.remove("hidden");

    // Assumptions
    const assumptionsBox = document.getElementById("assumptionsBox");
    if (data.assumptions && data.assumptions.length > 0) {
        assumptionsBox.classList.remove("hidden");
        document.getElementById("assumptionsText").textContent = "Assumptions: " + data.assumptions.join(" | ");
    } else {
        assumptionsBox.classList.add("hidden");
    }

    // Insight Banner
    const insightBanner = document.getElementById("insightBanner");
    insightBanner.classList.remove("hidden");
    document.getElementById("insightText").textContent = data.insight;

    // Justification Box
    const justificationBox = document.querySelector(".justification-box");
    justificationBox.classList.remove("hidden");
    document.getElementById("justificationText").textContent = data.justification;

    // Canvas & Chart.js
    const chartWrapper = document.querySelector(".chart-wrapper");
    chartWrapper.classList.remove("hidden");

    if (activeChartInstance) {
        activeChartInstance.destroy();
    }

    const canvas = document.getElementById("activeChartCanvas");
    const ctx = canvas.getContext("2d");
    activeChartInstance = new Chart(ctx, data.chart_config);
}

async function handlePinCurrentChart() {
    if (!currentQueryResponse) return;
    try {
        const res = await fetch("/api/pins", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(currentQueryResponse)
        });

        if (res.ok) {
            alert("Chart successfully pinned to dashboard.");
            loadPinnedDashboard();
        } else {
            alert("Failed to pin chart.");
        }
    } catch (e) {
        console.error("Error pinning chart:", e);
    }
}

async function loadPinnedDashboard() {
    try {
        const res = await fetch("/api/pins");
        const pins = await res.json();
        renderDashboardGrid(pins);
    } catch (e) {
        console.error("Error loading dashboard pins:", e);
    }
}

function renderDashboardGrid(pins) {
    const grid = document.getElementById("dashboardGrid");
    const countBadge = document.getElementById("pinCount");
    if (countBadge) countBadge.textContent = pins.length;

    // Destroy existing pinned charts
    Object.values(pinnedChartInstances).forEach(chart => chart.destroy());
    pinnedChartInstances = {};

    grid.innerHTML = "";

    if (!pins || pins.length === 0) {
        grid.innerHTML = `
            <div id="emptyDashboardState" class="empty-state">
                <h3>No Pinned Charts</h3>
                <p>Run a query in the Query Builder and click "Pin to Dashboard" to save charts here.</p>
            </div>
        `;
        return;
    }

    pins.forEach(pin => {
        const card = document.createElement("div");
        card.className = `pinned-card ${pin.has_significant_change ? "has-diff" : ""}`;
        const canvasId = `pinChartCanvas_${pin.id}`;

        const diffBannerHtml = pin.has_significant_change
            ? `<div class="diff-alert-banner">SIGNIFICANT CHANGE DETECTED: ${pin.change_summary}</div>`
            : "";

        card.innerHTML = `
            <div class="pinned-card-header">
                <div>
                    <h3 style="font-size: 15px; font-weight: 700;">"${pin.query}"</h3>
                    <div style="font-size: 11px; color: #94a3b8; margin-top: 4px;">
                        Pinned: ${new Date(pin.pinned_at).toLocaleDateString()} | Refreshed: ${new Date(pin.last_refreshed_at).toLocaleTimeString()}
                    </div>
                </div>
                <div class="pinned-card-actions">
                    <button class="icon-btn" onclick="refreshPin('${pin.id}')">Refresh</button>
                    <button class="icon-btn delete-btn" onclick="deletePin('${pin.id}')">Delete</button>
                </div>
            </div>
            ${diffBannerHtml}
            <div style="font-size: 13px; color: #059669; font-weight: 500; margin-bottom: 12px;">
                Insight: ${pin.insight}
            </div>
            <div class="chart-wrapper" style="height: 280px;">
                <canvas id="${canvasId}"></canvas>
            </div>
        `;

        grid.appendChild(card);

        // Render Canvas
        setTimeout(() => {
            const canvas = document.getElementById(canvasId);
            if (canvas) {
                const ctx = canvas.getContext("2d");
                pinnedChartInstances[pin.id] = new Chart(ctx, pin.chart_config);
            }
        }, 50);
    });
}

async function refreshPin(pinId) {
    try {
        const res = await fetch(`/api/pins/${pinId}/refresh`, { method: "POST" });
        if (res.ok) {
            loadPinnedDashboard();
        } else {
            alert("Error refreshing pin.");
        }
    } catch (e) {
        console.error("Error refreshing pin:", e);
    }
}

async function deletePin(pinId) {
    if (!confirm("Remove this chart from your pinned dashboard?")) return;
    try {
        const res = await fetch(`/api/pins/${pinId}`, { method: "DELETE" });
        if (res.ok) {
            loadPinnedDashboard();
        }
    } catch (e) {
        console.error("Error deleting pin:", e);
    }
}
