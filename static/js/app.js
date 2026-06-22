// --- Global Application State ---
const API_BASE = window.location.protocol === 'file:' ? 'http://127.0.0.1:8000' : '';
const DEFAULT_GRID = [
    { Abbreviation: "VER", FullName: "Max Verstappen", TeamName: "Red Bull Racing" },
    { Abbreviation: "PER", FullName: "Sergio Perez", TeamName: "Red Bull Racing" },
    { Abbreviation: "HAM", FullName: "Lewis Hamilton", TeamName: "Mercedes" },
    { Abbreviation: "RUS", FullName: "George Russell", TeamName: "Mercedes" },
    { Abbreviation: "LEC", FullName: "Charles Leclerc", TeamName: "Ferrari" },
    { Abbreviation: "SAI", FullName: "Carlos Sainz", TeamName: "Ferrari" },
    { Abbreviation: "NOR", FullName: "Lando Norris", TeamName: "McLaren" },
    { Abbreviation: "PIA", FullName: "Oscar Piastri", TeamName: "McLaren" },
    { Abbreviation: "ALO", FullName: "Fernando Alonso", TeamName: "Aston Martin" },
    { Abbreviation: "STR", FullName: "Lance Stroll", TeamName: "Aston Martin" },
    { Abbreviation: "ALB", FullName: "Alexander Albon", TeamName: "Williams" },
    { Abbreviation: "GAS", FullName: "Pierre Gasly", TeamName: "Alpine" },
    { Abbreviation: "OCO", FullName: "Esteban Ocon", TeamName: "Alpine" },
    { Abbreviation: "TSU", FullName: "Yuki Tsunoda", TeamName: "RB" },
    { Abbreviation: "RIC", FullName: "Daniel Ricciardo", TeamName: "RB" },
    { Abbreviation: "MAG", FullName: "Kevin Magnussen", TeamName: "Haas" },
    { Abbreviation: "HUL", FullName: "Nico Hulkenberg", TeamName: "Haas" },
    { Abbreviation: "BOT", FullName: "Valtteri Bottas", TeamName: "Kick Sauber" },
    { Abbreviation: "ZHO", FullName: "Zhou Guanyu", TeamName: "Kick Sauber" }
];
let activeDrivers = [...DEFAULT_GRID];
let activeModel = null;
let driverOffsets = {};

// Team Hex color code mapping
const TEAM_COLORS = {
    'red bull': '#3671C6',
    'mercedes': '#27F4D2',
    'ferrari': '#F91536',
    'mclaren': '#F58020',
    'aston martin': '#229971',
    'alpine': '#0093CC',
    'williams': '#37BEDD',
    'haas': '#B6BABD',
    'sauber': '#52E252',
    'rb': '#6692FF',
    'cyber_cyan': '#00E5FF',
    'cyber_pink': '#FF007F'
};

const TIRE_COLORS = {
    'SOFT': '#FF3333',
    'MEDIUM': '#FFD300',
    'HARD': '#FFFFFF',
    'INTERMEDIATE': '#39FF14',
    'WET': '#00A0FF'
};

// --- DOM Element Selectors ---
const loaderOverlay = document.getElementById("telemetry-loader");
const loaderStatusText = document.getElementById("loader-status");

const selectSeason = document.getElementById("select-season");
const selectGp = document.getElementById("select-gp");
const selectSession = document.getElementById("select-session");
const btnConnect = document.getElementById("btn-connect");
const apiIndicator = document.getElementById("api-status-indicator");
const apiText = document.getElementById("api-status-text");

// HUD elements
const hudTrackTemp = document.getElementById("hud-track-temp");
const hudAirTemp = document.getElementById("hud-air-temp");
const hudHumidity = document.getElementById("hud-humidity");
const hudRainStatus = document.getElementById("hud-rain-status");

// ML elements
const mlModelInfo = document.getElementById("ml-model-info");
const modelValGp = document.getElementById("model-val-gp");
const modelValMae = document.getElementById("model-val-mae");
const modelValR2 = document.getElementById("model-val-r2");

// Driver selectors
const selectDriverA = document.getElementById("select-driver-a");
const selectDriverB = document.getElementById("select-driver-b");
const telemetryMetrics = document.getElementById("telemetry-metrics");
const sectorMetrics = document.getElementById("sector-metrics");
const telemetryPlots = document.getElementById("telemetry-plots");

// --- Initialization on Page Load ---
document.addEventListener("DOMContentLoaded", () => {
    setupTabNavigation();
    populateGpsList();
    setupEventListeners();
    populateSimulatorDriverConfig();
    
    // Trigger F1 Start Lights loader sequencer
    runStartLightsLoader();
    
    // Start Hero elements
    initHeroSpeedCanvas();
    startRaceCountdownTicker();
    
    // Initialize fullscreen buttons on all charts
    setupFullscreenCharts();
});

// Setup tab pane navigation
function setupTabNavigation() {
    const tabLinks = document.querySelectorAll(".tab-link");
    const tabPanes = document.querySelectorAll(".tab-pane");

    tabLinks.forEach(link => {
        link.addEventListener("click", () => {
            const targetTab = link.getAttribute("data-tab");
            
            tabLinks.forEach(l => l.classList.remove("active"));
            tabPanes.forEach(p => p.classList.remove("active"));

            link.classList.add("active");
            document.getElementById(targetTab).classList.add("active");
            
            // Relayout Plotly charts since hidden containers throw off width calculations
            setTimeout(() => {
                const plotlyPlots = document.querySelectorAll(".plotly-div");
                plotlyPlots.forEach(div => {
                    if (div.children.length > 0) {
                        Plotly.Plots.resize(div);
                    }
                });
            }, 100);
        });
    });
}

// Fetch calendar schedule
async function populateGpsList() {
    try {
        const year = selectSeason.value;
        const res = await fetch(`${API_BASE}/api/gps?year=${year}`);
        const data = await res.json();
        
        selectGp.innerHTML = "";
        data.gps.forEach(gp => {
            const opt = document.createElement("option");
            opt.value = gp;
            opt.textContent = gp;
            selectGp.appendChild(opt);
        });
        
        // Select British Grand Prix by default if available
        const defaultIndex = data.gps.findIndex(g => g.includes("British") || g.includes("Silverstone"));
        if (defaultIndex !== -1) {
            selectGp.selectedIndex = defaultIndex;
        }
        
        selectGp.disabled = false;
    } catch (e) {
        console.error("Failed to populate schedule:", e);
    }
}

function setupEventListeners() {
    selectSeason.addEventListener("change", populateGpsList);

    // Timing Connection API
    btnConnect.addEventListener("click", connectTimingSession);

    // Driver Comparison triggers
    selectDriverA.addEventListener("change", fetchAndRenderTelemetry);
    selectDriverB.addEventListener("change", fetchAndRenderTelemetry);

    // Stint Optimizer triggers
    document.getElementById("btn-run-optimizer").addEventListener("click", runStrategyOptimizer);
    document.getElementById("select-decay-compound").addEventListener("change", updateTireDecayPlot);
    document.getElementById("input-decay-start").addEventListener("change", updateTireDecayPlot);
    document.getElementById("input-decay-life").addEventListener("change", updateTireDecayPlot);
    document.getElementById("check-fuel-correction").addEventListener("change", updateTireDecayPlot);
    document.getElementById("select-opt-driver").addEventListener("change", () => {
        updateTireDecayPlot();
        runStrategyOptimizer();
    });

    // Undercut Analyzer triggers
    const ucGapInput = document.getElementById("input-uc-gap");
    const ucGapValue = document.getElementById("val-uc-gap");
    ucGapInput.addEventListener("input", () => {
        ucGapValue.textContent = `${ucGapInput.value} s`;
    });
    document.getElementById("btn-run-undercut").addEventListener("click", runUndercutAnalysis);

    // Standings Simulator triggers
    document.getElementById("check-sim-rain").addEventListener("change", (e) => {
        const params = document.getElementById("sim-rain-params");
        if (e.target.checked) {
            params.classList.remove("hidden");
        } else {
            params.classList.add("hidden");
        }
    });
    document.getElementById("btn-run-sim").addEventListener("click", runRaceSimulation);
    
    // Add Driver Slot trigger
    document.getElementById("btn-sim-add-slot").addEventListener("click", () => {
        addDriverToSimList();
    });

    // Chatbot send
    document.getElementById("btn-chat-send").addEventListener("click", sendChatMessage);
    document.getElementById("chat-input-text").addEventListener("keypress", (e) => {
        if (e.key === "Enter") sendChatMessage();
    });
}

// --- API Request & State Controllers ---

async function connectTimingSession() {
    const year = selectSeason.value;
    const gp = selectGp.value;
    const sessionType = selectSession.value;
    
    console.log("Connect button clicked. Inputs captured:", { year, gp, sessionType });
    
    // Defensive check to prevent throwing errors if schedule is still loading
    if (!gp || gp === "Loading schedule...") {
        alert("Timing schedule is still loading. Please wait a moment or select a different season to refresh the Grand Prix list.");
        return;
    }
    
    showLoader(`CONNECTING TO ${year} ${gp.toUpperCase()} (${sessionType.toUpperCase()})...`);
    
    // Add subtitle notice about download latency
    const loaderBox = document.querySelector(".loader-box");
    const oldNotice = document.getElementById("loader-notice");
    if (oldNotice) oldNotice.remove();
    
    const subtitleNotice = document.createElement("div");
    subtitleNotice.style.fontSize = "10px";
    subtitleNotice.style.color = "var(--text-muted)";
    subtitleNotice.style.marginTop = "0.5rem";
    subtitleNotice.style.letterSpacing = "1px";
    subtitleNotice.id = "loader-notice";
    subtitleNotice.textContent = "FETCHING TIMING DATA (MAY TAKE UP TO 60S FOR UNCACHED SESSIONS)...";
    
    if (loaderBox) {
        loaderBox.appendChild(subtitleNotice);
    }
    const payload = {
        year: parseInt(year),
        gp: gp,
        session_type: sessionType
    };

    try {
        const res = await fetch(`${API_BASE}/api/connect`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || "API Failure");
        }

        const data = await res.json();
        
        // Update App State
        activeSession = data;
        activeDrivers = data.drivers;
        driverOffsets = data.driver_offsets;
        activeModel = data.model;

        // Update Header HUD status
        if (data.weather) {
            hudTrackTemp.textContent = `${data.weather.TrackTemp.toFixed(1)} °C`;
            hudAirTemp.textContent = `${data.weather.AirTemp.toFixed(1)} °C`;
            hudHumidity.textContent = `${data.weather.Humidity.toFixed(1)}%`;
            hudRainStatus.textContent = data.weather.Rainfall ? "🌧️ WET SESSION" : "☀️ DRY TRACK";
            hudRainStatus.className = data.weather.Rainfall ? "hud-value status-warning" : "hud-value status-safe";
        }

        // Sidebar indicators
        apiIndicator.className = "status-dot online";
        apiText.textContent = `CONNECTED: ${payload.gp}`;
        
        // ML stats display
        modelValGp.textContent = data.model.gp;
        modelValMae.textContent = `${data.model.mae.toFixed(3)} s`;
        modelValR2.textContent = `${(data.model.r2 * 100).toFixed(1)}%`;
        mlModelInfo.classList.remove("hidden");

        // Populate comparison drivers
        populateDriverDropdowns();

        // Populate strategy optimize selectors
        populateStrategySelectors();

        // Populate simulator checklist
        populateSimulatorDriverConfig();

        // Auto trigger first load telemetry comparison
        fetchAndRenderTelemetry();
        updateTireDecayPlot();
        runStrategyOptimizer();

    } catch (e) {
        alert(`F1 API Connection failed: ${e.message}`);
        apiIndicator.className = "status-dot offline";
        apiText.textContent = "OFFLINE (API ERROR)";
    } finally {
        hideLoader();
    }
}

function populateDriverDropdowns() {
    selectDriverA.innerHTML = "";
    selectDriverB.innerHTML = "";

    activeDrivers.forEach((d, idx) => {
        const optA = document.createElement("option");
        optA.value = d.Abbreviation;
        optA.textContent = `${d.Abbreviation} (${d.FullName})`;
        selectDriverA.appendChild(optA);

        const optB = document.createElement("option");
        optB.value = d.Abbreviation;
        optB.textContent = `${d.Abbreviation} (${d.FullName})`;
        selectDriverB.appendChild(optB);
    });

    // Default to HAM vs VER if in lists
    const hasHAM = activeDrivers.some(d => d.Abbreviation === "HAM");
    const hasVER = activeDrivers.some(d => d.Abbreviation === "VER");

    if (hasHAM) selectDriverA.value = "HAM";
    if (hasVER) selectDriverB.value = "VER";

    selectDriverA.disabled = false;
    selectDriverB.disabled = false;
}

function populateStrategySelectors() {
    const selectOptDrv = document.getElementById("select-opt-driver");
    selectOptDrv.innerHTML = `<option value="0.0">Average Grid</option>`;
    
    activeDrivers.forEach(d => {
        const offset = driverOffsets[d.Abbreviation] || 0.0;
        const opt = document.createElement("option");
        opt.value = offset;
        opt.textContent = `${d.Abbreviation} (Offset: ${offset > 0 ? '+' : ''}${offset.toFixed(3)}s)`;
        selectOptDrv.appendChild(opt);
    });
    
    selectOptDrv.disabled = false;
}

function populateSimulatorDriverConfig() {
    const listDiv = document.getElementById("sim-drivers-config-list");
    listDiv.innerHTML = ""; // Clear list
    
    // Add default driver slots
    addDriverToSimList("VER", "MEDIUM", 20, "HARD");
    addDriverToSimList("HAM", "MEDIUM", 22, "HARD");
    addDriverToSimList("NOR", "SOFT", 15, "MEDIUM");
}

function addDriverToSimList(selectedAbbr = "", selectedStint1 = "MEDIUM", selectedPit = "20", selectedStint2 = "HARD") {
    const listDiv = document.getElementById("sim-drivers-config-list");
    
    // Remove placeholder text if present
    const placeholder = listDiv.querySelector(".placeholder-text");
    if (placeholder) placeholder.remove();

    // Create a unique ID for this card/slot
    const cardId = 'sim-slot-' + Math.random().toString(36).substr(2, 9);
    
    const configCard = document.createElement("div");
    configCard.className = "driver-sim-card";
    configCard.id = cardId;
    
    // Generate driver options for the dropbox
    let driverOptions = '<option value="">-- Select Driver --</option>';
    activeDrivers.forEach(d => {
        const selectedAttr = d.Abbreviation === selectedAbbr ? 'selected' : '';
        driverOptions += `<option value="${d.Abbreviation}" ${selectedAttr}>${d.Abbreviation} (${d.FullName})</option>`;
    });

    // Generate tyre compound options
    const compoundsList = ["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"];
    let stint1Options = "";
    let stint2Options = "";
    compoundsList.forEach(comp => {
        stint1Options += `<option value="${comp}" ${comp === selectedStint1 ? 'selected' : ''}>${comp}</option>`;
        stint2Options += `<option value="${comp}" ${comp === selectedStint2 ? 'selected' : ''}>${comp}</option>`;
    });

    configCard.innerHTML = `
        <div class="driver-sim-title" style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
            <div style="display: flex; align-items: center; gap: 0.5rem; flex: 1;">
                <span class="driver-color-indicator" style="background-color: var(--accent-cyan); width: 10px; height: 10px; border-radius: 50%; display: inline-block;"></span>
                <select class="sim-driver-select" style="background: rgba(30, 41, 59, 0.9); border: 1px solid rgba(255,255,255,0.1); color: var(--text-light); font-family: var(--font-display); font-size: 11px; padding: 0.2rem; border-radius: 4px; flex: 1;">
                    ${driverOptions}
                </select>
            </div>
            <button onclick="removeSimSlot('${cardId}')" class="btn-remove-sim-driver" style="background: transparent; border: none; color: var(--accent-pink); font-size: 10px; font-weight: 700; cursor: pointer; letter-spacing: 0.5px; margin-left: 0.5rem;">REMOVE</button>
        </div>
        <div class="driver-sim-stints" style="display: flex; gap: 0.5rem; margin-top: 0.5rem;">
            <div class="form-group" style="flex: 1;">
                <label style="font-size: 9px;">Start Tyre</label>
                <select class="sim-stint-1" style="background: rgba(30, 41, 59, 0.9); border: 1px solid rgba(255,255,255,0.1); color: var(--text-light); font-size: 11px; padding: 0.2rem; border-radius: 4px; width: 100%;">
                    ${stint1Options}
                </select>
            </div>
            <div class="form-group" style="flex: 0.8;">
                <label style="font-size: 9px;">Pit Lap</label>
                <input type="number" class="sim-pit-lap" value="${selectedPit}" min="1" max="52" style="background: rgba(30, 41, 59, 0.9); border: 1px solid rgba(255,255,255,0.1); color: var(--text-light); font-size: 11px; padding: 0.2rem; border-radius: 4px; width: 100%;">
            </div>
            <div class="form-group" style="flex: 1;">
                <label style="font-size: 9px;">Next Tyre</label>
                <select class="sim-stint-2" style="background: rgba(30, 41, 59, 0.9); border: 1px solid rgba(255,255,255,0.1); color: var(--text-light); font-size: 11px; padding: 0.2rem; border-radius: 4px; width: 100%;">
                    ${stint2Options}
                </select>
            </div>
        </div>
    `;
    listDiv.appendChild(configCard);
    
    // Add event listener to select element to update driver color indicator
    const select = configCard.querySelector('.sim-driver-select');
    const indicator = configCard.querySelector('.driver-color-indicator');
    
    const updateIndicatorColor = () => {
        const val = select.value;
        if (val) {
            indicator.style.backgroundColor = getTeamColor(val);
        } else {
            indicator.style.backgroundColor = 'var(--text-muted)';
        }
    };
    
    select.addEventListener('change', updateIndicatorColor);
    updateIndicatorColor(); // Initial call
}

window.removeSimSlot = function(cardId) {
    const card = document.getElementById(cardId);
    if (card) card.remove();
    
    const listDiv = document.getElementById("sim-drivers-config-list");
    if (listDiv.children.length === 0) {
        listDiv.innerHTML = '<p class="placeholder-text">Add driver slots to start configuring strategies.</p>';
    }
};

// --- Telemetry Compare & Plotly Functions ---

async function fetchAndRenderTelemetry() {
    const driverA = selectDriverA.value;
    const driverB = selectDriverB.value;

    if (!driverA || !driverB) return;
    if (driverA === driverB) {
        alert("Please select two different drivers.");
        return;
    }

    showLoader("ALIGNING SENSOR DATA GRIDS...");

    try {
        const res = await fetch(`${API_BASE}/api/telemetry`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ driver_a: driverA, driver_b: driverB })
        });

        if (!res.ok) throw new Error("Alignment failure");
        const data = await res.json();

        // 1. Display lap metadata card row
        document.getElementById("label-lap-a").textContent = `${driverA} (${data.metadata.team_a}) Lap`;
        document.getElementById("label-lap-b").textContent = `${driverB} (${data.metadata.team_b}) Lap`;
        document.getElementById("val-lap-a").textContent = `${data.metadata.lap_time_a.toFixed(3)}s`;
        document.getElementById("val-lap-b").textContent = `${data.metadata.lap_time_b.toFixed(3)}s`;
        
        const delta = data.metadata.lap_time_a - data.metadata.lap_time_b;
        const deltaVal = document.getElementById("val-delta");
        deltaVal.textContent = `${delta > 0 ? '+' : ''}${delta.toFixed(3)}s`;
        deltaVal.style.color = delta < 0 ? "#00FF88" : "#FF3366";

        // Sector winners
        document.getElementById("val-sec1").textContent = `${data.sectors.s1_gap > 0 ? '+' : ''}${data.sectors.s1_gap.toFixed(3)}s`;
        document.getElementById("val-sec1").style.color = data.sectors.s1_gap < 0 ? "#00FF88" : "#FF3366";
        document.getElementById("val-sec2").textContent = `${data.sectors.s2_gap > 0 ? '+' : ''}${data.sectors.s2_gap.toFixed(3)}s`;
        document.getElementById("val-sec2").style.color = data.sectors.s2_gap < 0 ? "#00FF88" : "#FF3366";
        document.getElementById("val-sec3").textContent = `${data.sectors.s3_gap > 0 ? '+' : ''}${data.sectors.s3_gap.toFixed(3)}s`;
        document.getElementById("val-sec3").style.color = data.sectors.s3_gap < 0 ? "#00FF88" : "#FF3366";

        telemetryMetrics.classList.remove("hidden");
        sectorMetrics.classList.remove("hidden");
        telemetryPlots.classList.remove("hidden");

        // 2. Plotly chart outputs
        renderSpeedComparisonChart(data.telemetry, data.metadata);
        renderPedalComparisonChart(data.telemetry, data.metadata);
        renderGearComparisonChart(data.telemetry, data.metadata);
        renderStyleSignatureRadar(data.telemetry, data.metadata);
        
        if (data.coords && data.coords.x) {
            renderDominanceMap(data.coords, data.metadata);
        }

    } catch (e) {
        console.error(e);
        alert(`Telemetry fetch failed: ${e.message}`);
    } finally {
        hideLoader();
    }
}

// --- Plotly charts setups ---

function getDrsRanges(distances, drsValues) {
    if (!distances || !drsValues) return [];
    const ranges = [];
    let inRange = false;
    let startDist = 0;
    for (let i = 0; i < drsValues.length; i++) {
        const val = drsValues[i];
        const dist = distances[i];
        // Active DRS is represented by values >= 10 in FastF1 telemetry
        const active = val >= 10;
        if (active && !inRange) {
            startDist = dist;
            inRange = true;
        } else if (!active && inRange) {
            ranges.push([startDist, dist]);
            inRange = false;
        }
    }
    if (inRange) {
        ranges.push([startDist, distances[distances.length - 1]]);
    }
    return ranges;
}

function renderSpeedComparisonChart(tel, meta) {
    const colors = getContrastColors(meta.driver_a, meta.driver_b);
    const colorA = colors[0];
    const colorB = colors[1];

    const traceSpeedA = {
        x: tel.Distance,
        y: tel[`Speed_${meta.driver_a}`],
        name: `${meta.driver_a} Speed`,
        type: 'scatter',
        mode: 'lines',
        line: { color: colorA, width: 2 }
    };

    const traceSpeedB = {
        x: tel.Distance,
        y: tel[`Speed_${meta.driver_b}`],
        name: `${meta.driver_b} Speed`,
        type: 'scatter',
        mode: 'lines',
        line: { color: colorB, width: 2, dash: 'dash' }
    };

    const traceDelta = {
        x: tel.Distance,
        y: tel.DeltaTime,
        name: `Time Delta (A-B)`,
        type: 'scatter',
        mode: 'lines',
        fill: 'tozeroy',
        fillcolor: 'rgba(138, 43, 226, 0.15)',
        line: { color: '#8A2BE2', width: 1.5 },
        xaxis: 'x',
        yaxis: 'y2'
    };
    // Trace for legend entry of DRS Active Zones
    const traceDrsLegend = {
        x: [null],
        y: [null],
        name: 'DRS Active Zone',
        type: 'scatter',
        mode: 'lines',
        line: { color: 'rgba(0, 229, 255, 0.4)', width: 8 },
        showlegend: true
    };
    const layout = getBasePlotlyLayout(`Telemetry Comparison: ${meta.driver_a} vs ${meta.driver_b}`);
    
    // Explicitly anchor the delta subplot to the main distance axis
    layout.xaxis = { title: "Distance (m)", gridcolor: '#222938', color: '#94A3B8' };
    layout.yaxis = { title: "Speed (km/h)", gridcolor: '#222938', color: '#94A3B8', domain: [0.4, 1.0] };
    layout.yaxis2 = { title: "Delta (s)", gridcolor: '#222938', color: '#94A3B8', domain: [0.0, 0.3], anchor: 'x' };
    // Highlight DRS zones
    const drsValues = tel[`DRS_${meta.driver_a}`] || tel[`DRS_${meta.driver_b}`];
    const drsRanges = getDrsRanges(tel.Distance, drsValues);
    const shapes = [];
    if (drsRanges && drsRanges.length > 0) {
        for (const r of drsRanges) {
            shapes.push({
                type: 'rect',
                xref: 'x',
                yref: 'paper', // Spans the full height of the speed subplot domain
                x0: r[0],
                x1: r[1],
                y0: 0.4,       // matching layout.yaxis.domain [0.4, 1.0]
                y1: 1.0,
                fillcolor: 'rgba(0, 229, 255, 0.08)', // Translucent neon cyan
                line: { width: 0 },
                layer: 'below'
            });
        }
    }
    layout.shapes = shapes;
    Plotly.newPlot("plot-speed", [traceSpeedA, traceSpeedB, traceDelta, traceDrsLegend], layout, { responsive: true });
}

function renderPedalComparisonChart(tel, meta) {
    const colors = getContrastColors(meta.driver_a, meta.driver_b);
    const colorA = colors[0];
    const colorB = colors[1];

    const traceThrotA = {
        x: tel.Distance, y: tel[`Throttle_${meta.driver_a}`],
        name: `${meta.driver_a} Throttle`, type: 'scatter', mode: 'lines',
        line: { color: colorA, width: 1.8 }
    };
    const traceThrotB = {
        x: tel.Distance, y: tel[`Throttle_${meta.driver_b}`],
        name: `${meta.driver_b} Throttle`, type: 'scatter', mode: 'lines',
        line: { color: colorB, width: 1.8, dash: 'dash' }
    };
    const traceBrakeA = {
        x: tel.Distance, y: tel[`Brake_${meta.driver_a}`],
        name: `${meta.driver_a} Brake`, type: 'scatter', mode: 'lines',
        line: { color: '#EF4444', width: 1.2 }, yaxis: 'y2'
    };
    const traceBrakeB = {
        x: tel.Distance, y: tel[`Brake_${meta.driver_b}`],
        name: `${meta.driver_b} Brake`, type: 'scatter', mode: 'lines',
        line: { color: '#F87171', width: 1.2, dash: 'dash' }, yaxis: 'y2'
    };

    const layout = getBasePlotlyLayout("Throttle & Braking Input Overlays");
    
    // Explicitly anchor the brake subplot to the main distance axis
    layout.xaxis = { title: "Distance (m)", gridcolor: '#222938', color: '#94A3B8' };
    layout.yaxis = { title: "Throttle %", gridcolor: '#222938', color: '#94A3B8', domain: [0.55, 1.0] };
    layout.yaxis2 = { title: "Brake (Active)", gridcolor: '#222938', color: '#94A3B8', domain: [0.0, 0.45], tickvals: [0, 1], anchor: 'x' };

    Plotly.newPlot("plot-pedals", [traceThrotA, traceThrotB, traceBrakeA, traceBrakeB], layout, { responsive: true });
}

function renderGearComparisonChart(tel, meta) {
    const colors = getContrastColors(meta.driver_a, meta.driver_b);
    const colorA = colors[0];
    const colorB = colors[1];

    const traceGearA = {
        x: tel.Distance, y: tel[`Gear_${meta.driver_a}`],
        name: `${meta.driver_a} Gear`, type: 'scatter', mode: 'lines',
        line: { color: colorA, width: 2, shape: 'hv' }
    };
    const traceGearB = {
        x: tel.Distance, y: tel[`Gear_${meta.driver_b}`],
        name: `${meta.driver_b} Gear`, type: 'scatter', mode: 'lines',
        line: { color: colorB, width: 2, dash: 'dash', shape: 'hv' }
    };

    const layout = getBasePlotlyLayout("Gear Change Profile Comparison");
    layout.xaxis = { title: "Distance (m)", gridcolor: '#222938', color: '#94A3B8' };
    layout.yaxis = { title: "Gear", gridcolor: '#222938', color: '#94A3B8', tickvals: [1, 2, 3, 4, 5, 6, 7, 8] };

    Plotly.newPlot("plot-gears", [traceGearA, traceGearB], layout, { responsive: true });
}

function renderDominanceMap(coords, meta) {
    const colors = getContrastColors(meta.driver_a, meta.driver_b);
    const colorA = colors[0];
    const colorB = colors[1];

    const xA = [], yA = [], xB = [], yB = [];
    coords.dominance.forEach((dom, idx) => {
        if (dom === 1) {
            xA.push(coords.x[idx]);
            yA.push(coords.y[idx]);
        } else {
            xB.push(coords.x[idx]);
            yB.push(coords.y[idx]);
        }
    });

    const traceA = {
        x: xA, y: yA, mode: 'markers', name: `${meta.driver_a} Faster`,
        marker: { color: colorA, size: 4 }, type: 'scatter'
    };

    const traceB = {
        x: xB, y: yB, mode: 'markers', name: `${meta.driver_b} Faster`,
        marker: { color: colorB, size: 4 }, type: 'scatter'
    };

    // Global gray centerline track outline
    const traceTrack = {
        x: coords.x, y: coords.y, mode: 'lines', name: 'Track Line',
        line: { color: '#222938', width: 6 }, type: 'scatter', hoverinfo: 'skip', showlegend: false
    };

    const layout = getBasePlotlyLayout("Track Dominance Map (2D coordinates)");
    layout.xaxis = { showgrid: false, zeroline: false, showticklabels: false };
    layout.yaxis = { showgrid: false, zeroline: false, showticklabels: false, scaleanchor: "x", scaleratio: 1 };
    layout.showlegend = true;

    Plotly.newPlot("plot-dominance", [traceTrack, traceA, traceB], layout, { responsive: true });
}

function renderStyleSignatureRadar(tel, meta) {
    const driverA = meta.driver_a;
    const driverB = meta.driver_b;

    const calcScorecard = (driver) => {
        // 1. Max Speed
        const maxSpeed = Math.max(...tel[`Speed_${driver}`]);
        const speedScore = Math.max(50, Math.min(100, (maxSpeed - 260) / (340 - 260) * 40 + 60));
        
        // 2. Throttle
        const avgThrottle = tel[`Throttle_${driver}`].reduce((a, b) => a + b, 0) / tel[`Throttle_${driver}`].length;
        const throttleScore = Math.max(50, Math.min(100, (avgThrottle - 40) / (85 - 40) * 50 + 50));
        
        // 3. Braking Decel
        const brakeActiveIdx = tel[`Brake_${driver}`].map((b, i) => b > 0.5 ? i : -1).filter(i => i !== -1);
        let decelScore = 75.0;
        if (brakeActiveIdx.length > 2) {
            let totalDecel = 0;
            let decelCount = 0;
            for (let idx of brakeActiveIdx) {
                if (idx < tel[`Speed_${driver}`].length - 1) {
                    const diff = tel[`Speed_${driver}`][idx] - tel[`Speed_${driver}`][idx + 1];
                    if (diff > 0) {
                        totalDecel += diff;
                        decelCount++;
                    }
                }
            }
            const avgDecel = decelCount > 0 ? totalDecel / decelCount : 0.5;
            decelScore = Math.max(50, Math.min(100, (avgDecel - 0.1) / (1.5 - 0.1) * 50 + 50));
        }

        // 4. Apex speed (bottom 15% slow points)
        const sortedSpeed = [...tel[`Speed_${driver}`]].sort((a, b) => a - b);
        const index15 = Math.floor(sortedSpeed.length * 0.15);
        const slowPoint = sortedSpeed[index15] || 90;
        const apexScore = Math.max(50, Math.min(100, (slowPoint - 60) / (120 - 60) * 50 + 50));

        // 5. Gear changes
        let gearChanges = 0;
        for (let i = 0; i < tel[`Gear_${driver}`].length - 1; i++) {
            if (tel[`Gear_${driver}`][i] !== tel[`Gear_${driver}`][i+1]) {
                gearChanges++;
            }
        }
        const gearScore = Math.max(50, Math.min(100, 100 - (gearChanges - 35) * 1.1));

        return [speedScore, decelScore, throttleScore, apexScore, gearScore];
    };

    const scoresA = calcScorecard(driverA);
    const scoresB = calcScorecard(driverB);

    const categories = ['Straight-Line Speed', 'Braking Aggression', 'Throttle Application', 'Corner Apex Speed', 'Gear Shift Efficiency'];

    const colors = getContrastColors(driverA, driverB);
    const colorA = colors[0];
    const colorB = colors[1];

    const data = [
        {
            type: 'scatterpolar',
            r: scoresA,
            theta: categories,
            fill: 'toself',
            name: driverA,
            line: { color: colorA }
        },
        {
            type: 'scatterpolar',
            r: scoresB,
            theta: categories,
            fill: 'toself',
            name: driverB,
            line: { color: colorB }
        }
    ];

    const layout = getBasePlotlyLayout(`Driver Style Signature: ${driverA} vs ${driverB}`);
    layout.polar = {
        radialaxis: { visible: true, range: [50, 100], gridcolor: '#222938', color: '#94A3B8' },
        angularaxis: { gridcolor: '#222938', color: '#F1F5F9' },
        bgcolor: 'rgba(0,0,0,0)'
    };
    layout.showlegend = true;

    Plotly.newPlot("plot-scorecard", data, layout, { responsive: true });
}

// --- Strategy Optimizer & Decay Curve Functions ---

async function updateTireDecayPlot() {
    if (!activeSession) return;

    const selectOptDrv = document.getElementById("select-opt-driver");
    const payload = {
        compound: document.getElementById("select-decay-compound").value,
        start_lap: parseInt(document.getElementById("input-decay-start").value) || 1,
        life_range: parseInt(document.getElementById("input-decay-life").value) || 25,
        fuel_correction: document.getElementById("check-fuel-correction").checked,
        driver_offset: parseFloat(selectOptDrv.value) || 0.0
    };

    try {
        const res = await fetch(`${API_BASE}/api/strategy/decay`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        // 1. Draw Tire wear limit warning
        const warningDiv = document.getElementById("stint-cliff-warning");
        const maxSafeLife = payload.compound === "SOFT" ? 15 : (payload.compound === "MEDIUM" ? 26 : 38);
        
        if (payload.life_range > maxSafeLife) {
            const decayGain = data.times[data.times.length - 1] - data.times[0];
            warningDiv.innerHTML = `⚠️ <strong>Tire Cliff Warning:</strong> Running the <strong>${payload.compound}</strong> compound for ${payload.life_range} laps exceeds safe thermal degradation limits. Predicted lap times drop off by up to <strong>+${decayGain.toFixed(2)}s</strong>.`;
            warningDiv.classList.remove("hidden");
        } else {
            warningDiv.classList.add("hidden");
        }

        // 2. Render curve
        renderTireDecayCurve(data.laps, data.times, payload.compound);

    } catch (e) {
        console.error(e);
    }
}

function renderTireDecayCurve(laps, times, compound) {
    const color = TIRE_COLORS[compound] || '#00E5FF';
    
    const trace = {
        x: laps,
        y: times,
        mode: 'lines+markers',
        type: 'scatter',
        name: `${compound} Pace`,
        line: { color: color, width: 2 },
        marker: { size: 6 }
    };

    const layout = getBasePlotlyLayout(`Predicted Pace Decay Curve for ${compound} compound`);
    layout.xaxis = { title: "Tyre Life (Laps)", gridcolor: '#222938', color: '#94A3B8' };
    layout.yaxis = { title: "Predicted Lap Time (s)", gridcolor: '#222938', color: '#94A3B8' };

    Plotly.newPlot("plot-decay", [trace], layout, { responsive: true });
}

async function runStrategyOptimizer() {
    if (!activeSession) return;

    showLoader("CALCULATING STRATEGY COMBINATIONS...");

    const selectOptDrv = document.getElementById("select-opt-driver");
    const payload = {
        total_laps: parseInt(document.getElementById("input-race-laps").value) || 52,
        pit_loss: parseFloat(document.getElementById("input-pit-loss").value) || 20.0,
        driver_offset: parseFloat(selectOptDrv.value) || 0.0
    };

    try {
        const res = await fetch(`${API_BASE}/api/strategy/optimize`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        // 1. Render Expandable ranked strategy items
        const listDiv = document.getElementById("ranked-strategies-list");
        listDiv.innerHTML = "";

        data.strategies.forEach((strat, idx) => {
            const minTime = (strat.total_time_secs / 60.0).toFixed(2);
            
            const expCard = document.createElement("div");
            expCard.className = `strategy-expander ${idx === 0 ? 'open' : ''}`;
            
            expCard.innerHTML = `
                <div class="strategy-expander-header" onclick="toggleExpander(this)">
                    <span>Rank ${idx+1}: ${strat.strategy_name}</span>
                    <span>Pit Lap: ${strat.optimal_pit_lap} | Duration: ${minTime} mins ▾</span>
                </div>
                <div class="strategy-expander-content">
                    <p style="margin-bottom: 1rem; font-size: 13px;">This strategy utilizes ${strat.strategy_name} stints to complete the race in <strong>${minTime} minutes</strong>. The optimal pit window is <strong>Lap ${strat.optimal_pit_lap}</strong>.</p>
                    <div id="chart-strat-${idx}" style="height: 250px;"></div>
                </div>
            `;
            listDiv.appendChild(expCard);

            // Render strategy trace graph inside expander content
            renderStrategyTrace(strat, idx);
        });

        // 2. Populate Traffic planner table rows
        const tableBody = document.querySelector("#traffic-planner-table tbody");
        tableBody.innerHTML = "";

        data.traffic.forEach(row => {
            const tr = document.createElement("tr");
            tr.className = row.status === "Clean Air" ? "clean-air-row" : "traffic-row";
            tr.innerHTML = `
                <td><strong>Lap ${row.pit_lap}</strong></td>
                <td><strong>${row.status.toUpperCase()}</strong></td>
                <td>${row.details}</td>
            `;
            tableBody.appendChild(tr);
        });

    } catch (e) {
        console.error(e);
        alert("Strategy calculations failed.");
    } finally {
        hideLoader();
    }
}

function renderStrategyTrace(strat, idx) {
    const laps = strat.laps.map(l => l.LapNumber);
    const times = strat.laps.map(l => l.LapTime);

    const trace = {
        x: laps,
        y: times,
        mode: 'lines+markers',
        type: 'scatter',
        line: { color: '#FF007F', width: 1.5 },
        marker: { size: 4 }
    };

    const layout = getBasePlotlyLayout(`Race Lap Trace (${strat.strategy_name})`);
    layout.xaxis = { title: "Race Lap", gridcolor: '#222938', color: '#94A3B8' };
    layout.yaxis = { title: "Lap Time (s)", gridcolor: '#222938', color: '#94A3B8' };
    layout.margin = { l: 40, r: 20, t: 40, b: 40 };

    Plotly.newPlot(`chart-strat-${idx}`, [trace], layout, { responsive: true });
}

// Global hook to toggle expander cards
window.toggleExpander = function(header) {
    const expander = header.parentElement;
    expander.classList.toggle("open");
    
    // Relayout the Plotly chart inside it
    const chartDiv = expander.querySelector(".plotly-div, [id^='chart-strat-']");
    if (chartDiv && expander.classList.contains("open")) {
        setTimeout(() => Plotly.Plots.resize(chartDiv), 100);
    }
};

// --- Undercut Threat functions ---

async function runUndercutAnalysis() {
    if (!activeSession) return;

    showLoader("CALCULATING THREAT VECTORS...");

    const payload = {
        gap_seconds: parseFloat(document.getElementById("input-uc-gap").value) || 1.2,
        lap_number: parseInt(document.getElementById("input-uc-lap").value) || 25,
        tyre_age_leader: parseInt(document.getElementById("input-uc-leader-age").value) || 15,
        compound_leader: document.getElementById("select-uc-leader-comp").value,
        compound_chaser_fresh: document.getElementById("select-uc-chaser-comp").value
    };

    try {
        const res = await fetch(`${API_BASE}/api/strategy/undercut`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        // 1. Update Alert Box threat level styles
        const alertBox = document.getElementById("undercut-threat-box");
        alertBox.className = "threat-alert";
        
        const threat = data.threat_level;
        if (threat.includes("CRITICAL")) {
            alertBox.classList.add("status-critical");
        } else if (threat.includes("HIGH")) {
            alertBox.classList.add("status-warning");
        } else if (threat.includes("MEDIUM")) {
            alertBox.classList.add("status-warning");
        } else {
            alertBox.classList.add("status-safe");
        }

        document.getElementById("uc-threat-level").textContent = `THREAT STATUS: ${threat}`;
        document.getElementById("uc-threat-recommendation").textContent = data.recommendation;

        // 2. Metrics values display
        document.getElementById("val-uc-leader-pace").textContent = `${data.leader_lap_time_worn.toFixed(2)}s`;
        document.getElementById("val-uc-chaser-pace").textContent = `${data.chaser_lap_time_fresh.toFixed(2)}s`;
        document.getElementById("val-uc-gain").textContent = `${data.undercut_gain_secs.toFixed(3)}s`;
        
        const newGapVal = document.getElementById("val-uc-new-gap");
        newGapVal.textContent = `${data.predicted_gap_secs.toFixed(3)}s`;
        newGapVal.style.color = data.predicted_gap_secs < 0 ? "#FF3366" : "#00FF88";

    } catch (e) {
        console.error(e);
        alert("Undercut calculation failed.");
    } finally {
        hideLoader();
    }
}

// --- Multi-Agent Simulation functions ---

async function runRaceSimulation() {
    if (!activeSession) {
        alert("Please connect the Timing API first to load and train the strategy optimizer.");
        return;
    }
    // Collect drivers configurations from active cards
    const configCards = document.querySelectorAll(".driver-sim-card");
    if (configCards.length === 0) {
        alert("Please select at least one driver to simulate.");
        return;
    }
    showLoader("SIMULATING STANDINGS TIMELINE...");
    const driversConfigs = {};
    let hasEmptyDriver = false;
    let hasDuplicateDriver = false;
    const selectedDrivers = new Set();
    
    configCards.forEach(card => {
        const drvSelect = card.querySelector(".sim-driver-select");
        const drv = drvSelect.value;
        if (!drv) {
            hasEmptyDriver = true;
            return;
        }
        if (selectedDrivers.has(drv)) {
            hasDuplicateDriver = true;
            return;
        }
        selectedDrivers.add(drv);
        
        const stint1 = card.querySelector(".sim-stint-1").value;
        const pitLapVal = card.querySelector(".sim-pit-lap").value;
        const stint2 = card.querySelector(".sim-stint-2").value;
        
        const compounds = [stint1, stint2];
        const pitLaps = pitLapVal ? [parseInt(pitLapVal)] : [];
        
        driversConfigs[drv] = {
            compounds: compounds,
            pit_laps: pitLaps
        };
    });
    
    if (hasEmptyDriver) {
        alert("Please select a driver for all strategy slots.");
        hideLoader();
        return;
    }
    if (hasDuplicateDriver) {
        alert("Each driver can only have one strategy configuration slot.");
        hideLoader();
        return;
    }
    
    // Event configurations
    const rainActive = document.getElementById("check-sim-rain").checked;
    const scLapsStr = document.getElementById("input-sim-sc").value;
    
    const payload = {
        drivers_configs: driversConfigs,
        sc_laps: scLapsStr.trim() ? scLapsStr.split(",").map(l => parseInt(l.trim())) : [],
        rain_active: rainActive,
        rain_lap: rainActive ? parseInt(document.getElementById("input-sim-rain-lap").value) : null,
        rain_intensity: rainActive ? document.getElementById("select-sim-rain-int").value : null
    };

    try {
        const res = await fetch(`${API_BASE}/api/simulator/run`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        // 1. Populate standing board table
        const finalLapNum = 52;
        const finalLap = data.history.filter(h => h.LapNumber === finalLapNum).sort((a, b) => a.Position - b.Position);

        const tableBody = document.querySelector("#standings-table tbody");
        tableBody.innerHTML = "";

        finalLap.forEach(row => {
            const tr = document.createElement("tr");
            const duration = (row.CumulativeTime / 60.0).toFixed(2);
            const gap = row.Position === 1 ? "Leader" : `+${row.GapToLeader.toFixed(2)}s`;
            const badgeColor = TIRE_COLORS[row.Compound.toUpperCase()] || '#00E5FF';

            tr.innerHTML = `
                <td><strong>${row.Position}</strong></td>
                <td><strong>${row.Driver}</strong></td>
                <td><span style="color: ${badgeColor}; font-weight: 700;">● ${row.Compound}</span></td>
                <td>${duration} mins</td>
                <td style="color: ${row.Position === 1 ? '#00FF88' : '#F1F5F9'}; font-weight: 600;">${gap}</td>
            `;
            tableBody.appendChild(tr);
        });

        // 2. Render charts
        renderSimPositionHistory(data.history, Object.keys(driversConfigs));
        renderSimLapTimesComparison(data.history, Object.keys(driversConfigs));

    } catch (e) {
        console.error(e);
        alert("Race simulation loop crashed.");
    } finally {
        hideLoader();
    }
}

function renderSimPositionHistory(history, drivers) {
    const traces = [];
    drivers.forEach(drv => {
        const drvHistory = history.filter(h => h.Driver === drv).sort((a, b) => a.LapNumber - b.LapNumber);
        traces.push({
            x: drvHistory.map(h => h.LapNumber),
            y: drvHistory.map(h => h.Position),
            name: drv,
            type: 'scatter',
            mode: 'lines+markers',
            line: { color: getTeamColor(drv), width: 2 }
        });
    });

    const layout = getBasePlotlyLayout("Lap-by-Lap Position Tracker");
    layout.xaxis = { title: "Race Lap", gridcolor: '#222938', color: '#94A3B8' };
    layout.yaxis = { title: "Position", gridcolor: '#222938', color: '#94A3B8', autorange: 'reverse', tickvals: [1, 2, 3, 4, 5, 6, 7] };

    Plotly.newPlot("plot-sim-pos", traces, layout, { responsive: true });
}

function renderSimLapTimesComparison(history, drivers) {
    const traces = [];
    drivers.forEach(drv => {
        const drvHistory = history.filter(h => h.Driver === drv).sort((a, b) => a.LapNumber - b.LapNumber);
        traces.push({
            x: drvHistory.map(h => h.LapNumber),
            y: drvHistory.map(h => h.LapTime),
            name: `${drv} Lap Time`,
            type: 'scatter',
            mode: 'lines',
            line: { color: getTeamColor(drv), width: 1.5 }
        });
    });

    const layout = getBasePlotlyLayout("Race Lap Times Comparison");
    layout.xaxis = { title: "Race Lap", gridcolor: '#222938', color: '#94A3B8' };
    layout.yaxis = { title: "Lap Time (s)", gridcolor: '#222938', color: '#94A3B8' };

    Plotly.newPlot("plot-sim-laps", traces, layout, { responsive: true });
}

// --- AI Strategy Assistant Chat Box ---

async function sendChatMessage() {
    const inputEl = document.getElementById("chat-input-text");
    const query = inputEl.value.trim();
    if (!query) return;

    // 1. Append user speech card
    appendChatMessage("user", "[DRIVER] USER", query);
    inputEl.value = "";

    try {
        const res = await fetch(`${API_BASE}/api/chatbot`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: query })
        });
        const data = await res.json();

        // 2. Append assistant response log
        const sender = data.response.match(/\*\*\[(.*?)\]\*\*/);
        const senderName = sender ? `[${sender[1]}]` : "[RADIO COMM] AI ENGINEER";
        const content = data.response.replace(/\*\*\[.*?\]\*\*:\s*/, "");
        
        appendChatMessage("assistant", senderName, content);

    } catch (e) {
        appendChatMessage("assistant", "[RADIO COMM] AI ENGINEER", "Communication breakdown. Check session connection.");
    }
}

function appendChatMessage(role, sender, text) {
    const box = document.getElementById("chat-messages-box");
    const msgDiv = document.createElement("div");
    msgDiv.className = `chat-message ${role}`;
    msgDiv.innerHTML = `
        <div class="message-sender">${sender}</div>
        <div class="message-content">${text}</div>
    `;
    box.appendChild(msgDiv);
    
    // Auto Scroll bottom
    box.scrollTop = box.scrollHeight;
}

// --- General Utility Helpers ---

function getTeamColor(driverCode) {
    // Lookup driver abbreviated maps
    const DRIVER_TEAM = {
        "VER": "red bull", "PER": "red bull",
        "LEC": "ferrari", "SAI": "ferrari",
        "HAM": "mercedes", "RUS": "mercedes",
        "NOR": "mclaren", "PIA": "mclaren",
        "ALO": "aston martin", "STR": "aston martin",
        "GAS": "alpine", "OCO": "alpine",
        "ALB": "williams", "SAR": "williams",
        "TSU": "sauber", "BOT": "sauber", "ZHO": "sauber",
        "MAG": "haas", "HUL": "haas",
        "RIC": "rb", "LAW": "rb"
    };

    const team = DRIVER_TEAM[driverCode.toUpperCase()];
    return TEAM_COLORS[team] || TEAM_COLORS.cyber_cyan;
}

function getBasePlotlyLayout(titleText) {
    return {
        title: {
            text: titleText,
            font: { family: 'Orbitron, Inter, sans-serif', color: '#F1F5F9', size: 14 }
        },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(18, 24, 38, 0.4)',
        font: { family: 'Inter, sans-serif', color: '#F1F5F9' },
        margin: { l: 50, r: 20, t: 50, b: 50 },
        showlegend: true,
        legend: { font: { size: 10 }, bgcolor: 'rgba(11, 14, 20, 0.8)', bordercolor: 'rgba(255,255,255,0.05)' }
    };
}

function showLoader(text) {
    loaderStatusText.textContent = text;
    
    // Pulse start lights during active API fetch loads
    const lightsContainer = document.querySelector(".f1-start-lights");
    if (lightsContainer) {
        lightsContainer.classList.add("loading");
    }
    
    loaderOverlay.classList.remove("fade-out");
    loaderOverlay.classList.remove("hidden");
    loaderOverlay.style.display = "flex";
}

function hideLoader() {
    const lightsContainer = document.querySelector(".f1-start-lights");
    if (lightsContainer) {
        lightsContainer.classList.remove("loading");
    }
    
    // Clean old notices if any
    const oldNotice = document.getElementById("loader-notice");
    if (oldNotice) oldNotice.remove();
    loaderOverlay.classList.add("fade-out");
    setTimeout(() => {
        loaderOverlay.style.display = "none";
    }, 600);
}   

window.launchLiveTiming = function() {
    const tabLink = document.querySelector(".tab-link[data-tab='tab-telemetry']");
    if (tabLink) {
        tabLink.click();
    }
};

// ================= F1 START LIGHTS LOADER SEQUENCE =================
function runStartLightsLoader() {
    const lights = [
        document.getElementById("light-1"),
        document.getElementById("light-2"),
        document.getElementById("light-3"),
        document.getElementById("light-4"),
        document.getElementById("light-5")
    ];
    
    const statusText = document.getElementById("loader-status");

    // Sequence turn-on (500ms intervals)
    lights.forEach((unit, idx) => {
        setTimeout(() => {
            if (unit) unit.classList.add("lit");
            statusText.textContent = `WARMING SECTORS... [${idx + 1}/5]`;
        }, 500 * (idx + 1));
    });

    // Lights out sequence (1.2s after the 5th light turns on)
    setTimeout(() => {
        statusText.textContent = "LIGHTS OUT AND AWAY WE GO!";
        lights.forEach(unit => {
            if (unit) unit.classList.remove("lit");
        });
        
        // Smoothly fade out loading screen
        const overlay = document.getElementById("telemetry-loader");
        if (overlay) {
            overlay.classList.add("fade-out");
            // Remove from DOM structure once transition ends
            setTimeout(() => {
                overlay.style.display = "none";
            }, 600);
        }
    }, 3800);
}

// ================= HERO RACE COUNTDOWN TIMER =================
async function startRaceCountdownTicker() {
    let targetTime = Date.now() + (3 * 24 * 60 * 60 * 1000); // fallback
    let gpName = "Austrian Grand Prix";
    try {
        const res = await fetch(`${API_BASE}/api/next-session`);
        if (res.ok) {
            const data = await res.json();
            gpName = data.gp;
            targetTime = new Date(data.timestamp).getTime();
        }
    } catch (e) {
        console.error("Failed to load live F1 schedule countdown:", e);
    }
    const titleEl = document.getElementById("countdown-title");
    if (titleEl) {
        titleEl.textContent = `${gpName.toUpperCase()} COUNTDOWN`;
    }
    const cdDays = document.getElementById("cd-days");
    const cdHours = document.getElementById("cd-hours");
    const cdMins = document.getElementById("cd-mins");
    const cdSecs = document.getElementById("cd-secs");
    function tick() {
        const diff = targetTime - Date.now();
        if (diff <= 0) {
            if (cdDays) cdDays.textContent = "00";
            if (cdHours) cdHours.textContent = "00";
            if (cdMins) cdMins.textContent = "00";
            if (cdSecs) cdSecs.textContent = "00";
            return;
        }
        const days = Math.floor(diff / (24 * 60 * 60 * 1000));
        const hours = Math.floor((diff % (24 * 60 * 60 * 1000)) / (60 * 60 * 1000));
        const mins = Math.floor((diff % (60 * 60 * 1000)) / (60 * 1000));
        const secs = Math.floor((diff % (60 * 1000)) / 1000);
        if (cdDays) cdDays.textContent = String(days).padStart(2, '0');
        if (cdHours) cdHours.textContent = String(hours).padStart(2, '0');
        if (cdMins) cdMins.textContent = String(mins).padStart(2, '0');
        if (cdSecs) cdSecs.textContent = String(secs).padStart(2, '0');
    }
    tick();
    setInterval(tick, 1000);
}


// ================= HERO CAR CANVAS SPEED TRAILS =================
function initHeroSpeedCanvas() {
    const canvas = document.getElementById("speed-canvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let particles = [];
    let gridOffset = 0;
    
    // Fit canvas dynamically
    function resize() {
        canvas.width = canvas.parentElement.clientWidth;
        canvas.height = canvas.parentElement.clientHeight;
    }
    resize();
    window.addEventListener("resize", resize);
    // 3D Perspective Vanishing Point (centered horizontally, shifted slightly up)
    let V_x = canvas.width * 0.45;
    let V_y = canvas.height * 0.38;
    window.addEventListener("resize", () => {
        V_x = canvas.width * 0.45;
        V_y = canvas.height * 0.38;
    });
    // 3D Speed Line Particle structure
    class SpeedParticle3D {
        constructor() {
            this.reset();
            // Start with some pre-distributed positions
            this.r = Math.random() * Math.max(canvas.width, canvas.height);
        }
        reset() {
            this.theta = Math.random() * Math.PI * 2; // angle in radians
            this.r = 10; // start near vanishing point
            this.speed = 2 + Math.random() * 4;
            // High-contrast cyber colors matching F1 styling
            this.color = Math.random() > 0.5 ? '#00E5FF' : '#FF007F'; 
            this.width = 1 + Math.random() * 2;
        }
        update() {
            // Accelerate outwards to simulate 3D speed warp
            this.r += this.speed * (1 + this.r * 0.018);
            if (this.r > Math.max(canvas.width, canvas.height)) {
                this.reset();
            }
        }
        draw() {
            const cos = Math.cos(this.theta);
            const sin = Math.sin(this.theta);
            
            const xStart = V_x + this.r * cos;
            const yStart = V_y + this.r * sin;
            
            // Length stretches as it gets closer to the viewport edges
            const len = this.r * 0.15;
            const xEnd = V_x + (this.r + len) * cos;
            const yEnd = V_y + (this.r + len) * sin;
            
            // Fade-in effect near vanishing point
            const opacity = Math.min(0.7, this.r / 200);
            ctx.beginPath();
            ctx.strokeStyle = this.color;
            ctx.lineWidth = this.width * (1 + this.r * 0.003);
            ctx.globalAlpha = opacity;
            ctx.moveTo(xStart, yStart);
            ctx.lineTo(xEnd, yEnd);
            ctx.stroke();
        }
    }
    // Populate 30 particles
    for (let i = 0; i < 30; i++) {
        particles.push(new SpeedParticle3D());
    }
    // Interactive Mouse 3D steering tilt listener for the Hero F1 Car
    const heroSection = document.querySelector(".f1-hero-section");
    const carImage = document.querySelector(".f1-car-image");
    
    if (heroSection && carImage) {
        heroSection.addEventListener("mousemove", (e) => {
            const rect = heroSection.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            // Subtle tilt ratios
            const tiltX = ((y / rect.height) - 0.5) * -12; // pitch/tilt up-down
            const tiltY = ((x / rect.width) - 0.5) * 12;   // yaw/steer left-right
            const roll = ((x / rect.width) - 0.5) * -3;    // bank/roll
            
            // Add vibration to the JS transform so it stacks with CSS vibrate
            const vibY = (Math.random() - 0.5) * 0.8;
            carImage.style.transform = `perspective(1000px) rotateX(${tiltX}deg) rotateY(${tiltY}deg) rotateZ(${roll}deg) translateY(${vibY}px) scale(1.02)`;
        });
        
        heroSection.addEventListener("mouseleave", () => {
            carImage.style.transform = "perspective(1000px) rotateX(0deg) rotateY(0deg) rotateZ(0deg) scale(1)";
        });
    }
    // Animation Loop
    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Draw 3D Perspective Grid ground (occupying the lower half of screen)
        ctx.globalCompositeOperation = 'source-over';
        ctx.globalAlpha = 1.0;
        
        // 1. Draw Column Lines shooting out from vanishing point
        ctx.strokeStyle = 'rgba(0, 229, 255, 0.08)';
        ctx.lineWidth = 1.5;
        const numCols = 18;
        for (let i = -2; i <= numCols + 2; i++) {
            const xEnd = (canvas.width / numCols) * i;
            ctx.beginPath();
            ctx.moveTo(V_x, V_y);
            ctx.lineTo(xEnd, canvas.height);
            ctx.stroke();
        }
        // 2. Draw Row Lines scrolling downwards in perspective
        gridOffset = (gridOffset + 1.8) % 40;
        ctx.strokeStyle = 'rgba(0, 229, 255, 0.12)';
        ctx.lineWidth = 1.0;
        const numRows = 10;
        for (let i = 0; i < numRows; i++) {
            const rawProgress = (i + gridOffset / 40) / numRows;
            const progress = Math.pow(rawProgress, 2.5); // exponential spacing for depth
            const y = V_y + (canvas.height - V_y) * progress;
            
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(canvas.width, y);
            ctx.stroke();
        }
        
        // Draw flying speed warp particles
        ctx.globalCompositeOperation = 'lighter';
        particles.forEach(p => {
            p.update();
            p.draw();
        });
        
        requestAnimationFrame(animate);
    }
    animate();
}

// ================= DRIVER UTILITIES & DOTD VOTES =================
window.scrollToDrivers = function() {
    const el = document.getElementById("section-drivers");
    if (el) {
        el.scrollIntoView({ behavior: 'smooth' });
    }
};

window.selectGridDriver = function(driverCode) {
    // 1. Switch to timings tab link
    window.launchLiveTiming();

    // 2. Select matching driver inside selectors
    setTimeout(() => {
        if (selectDriverA) {
            selectDriverA.value = driverCode;
            // Trigger change event to load telemetry
            selectDriverA.dispatchEvent(new Event('change'));
        }
    }, 150);
};

// State variables for DOTD Voting Poll percentages
let votes = { VER: 32, HAM: 28, NOR: 22, LEC: 18 };

window.castVote = function(driver) {
    if (votes[driver] !== undefined) {
        // Increment and adjust remaining to maintain 100% balance
        votes[driver] += 3;
        
        // Re-scale sums to fit 100%
        let sum = Object.values(votes).reduce((a, b) => a + b, 0);
        Object.keys(votes).forEach(k => {
            votes[k] = Math.round((votes[k] / sum) * 100);
        });

        // Update progress bars widths and text meters
        Object.keys(votes).forEach(k => {
            const bar = document.getElementById(`bar-${k}`);
            const text = document.getElementById(`pct-${k}`);
            if (bar) bar.style.width = `${votes[k]}%`;
            if (text) text.textContent = `${votes[k]}%`;
        });
    }
};

// ================= HIGH-CONTRAST TELEMETRY COLORS =================
function getContrastColors(driverA, driverB) {
    const colorA = getTeamColor(driverA);
    const colorB = getTeamColor(driverB);

    // Group F1 colors into similar hues (Blue/Teal/Green vs Red/Orange/Yellow)
    const isBlueish = (hex) => {
        const c = hex.toLowerCase();
        return c === TEAM_COLORS.mercedes || 
               c === TEAM_COLORS['red bull'] || 
               c === TEAM_COLORS.williams || 
               c === TEAM_COLORS.alpine || 
               c === TEAM_COLORS.sauber || 
               c === TEAM_COLORS.rb || 
               c === TEAM_COLORS.cyber_cyan;
    };

    // If both drivers share the same team or fall into the same color hue group,
    // enforce maximum contrast (Cyber Cyan vs Cyber Pink)
    if (colorA === colorB || (isBlueish(colorA) && isBlueish(colorB)) || (!isBlueish(colorA) && !isBlueish(colorB))) {
        return [TEAM_COLORS.cyber_cyan, TEAM_COLORS.cyber_pink];
    }
    return [colorA, colorB];
}

// ================= DYNAMIC FULLSCREEN CHART INJECTION =================
function setupFullscreenCharts() {
    const containers = document.querySelectorAll(".chart-container");
    containers.forEach(container => {
        const plotlyDiv = container.querySelector(".plotly-div");
        if (!plotlyDiv) return;

        const btn = document.createElement("button");
        btn.className = "btn-fullscreen";
        btn.textContent = "⛶ FULLSCREEN";
        btn.addEventListener("click", () => {
            container.classList.toggle("fullscreen");
            // Trigger Plotly layout resize to fit new viewport dimensions
            setTimeout(() => {
                Plotly.Plots.resize(plotlyDiv);
            }, 100);
        });
        container.appendChild(btn);
    });
}

// ================= CHAT GUIDELINE FILL UTILITY =================
window.autoFillChat = function(text) {
    const input = document.getElementById("chat-input-text");
    if (input) {
        input.value = text;
        input.focus();
    }
};