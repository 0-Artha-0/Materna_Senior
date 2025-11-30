// analytics_dashboard.js — simple & close to your original

window.addEventListener("load", start, false);

let _charts = {}; // store chart instances for safe re-rendering

async function start() {
    updateRangePreview();
    await loadAndRender(); // initial: all
    document.getElementById('rangeOptions')?.addEventListener('change', updateRangePreview);
    document.getElementById('refresh')?.addEventListener('click', loadAndRender);
}

function updateRangePreview() {
    const sel = document.getElementById('rangeOptions');
    const box = document.getElementById('dateRange');
    if (!sel || !box) return;
    const v = sel.value || 'all';
    if (v === 'all') {
        box.textContent = 'Showing: All time';
    } else {
        const now = new Date();
        const start = new Date(now);
        if (v === 'week') start.setDate(now.getDate() - 7);
        if (v === 'month') start.setDate(now.getDate() - 30);
        if (v === 'threemonths') start.setDate(now.getDate() - 90);
        box.textContent = `Showing: ${start.toISOString().slice(0, 10)} → ${now.toISOString().slice(0, 10)}`;
    }
}

async function loadAndRender() {
    const range = (document.getElementById('rangeOptions')?.value || 'all');
    const res = await fetch(`/dashboard_data?range=${encodeURIComponent(range)}`);
    if (!res.ok) {
        console.error('Dashboard API error:', res.status);
        return;
    }
    const data = await res.json();
    renderSummary(data.summary || {});
    renderAvgPCB(data.avg_pcb_levels);
    renderRiskDist(data.risk_distribution);
    renderConcentrationSeries(data.concentration_series);
    renderDemographics(data.demographics);
    renderEnvironment(data.environment);
    renderResearch(data.research);
}

/* -------- summary metrics -------- */
function renderSummary(s) {
    setText('totalPatients', s.total_patients);
    setText('highRiskCases', s.high_risk);
    setText('topPCB', s.top_pcb);
    setText('topPCBAvg', fix2(s.top_pcb_avg));
    setText('avgFetalPCB', fix2(s.avg_fetal_pcb));
    setText('correlation', fix2(s.correlation));
}

function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = (val ?? '-') + '';
}
function fix2(v) { return (typeof v === 'number') ? v.toFixed(2) : '-'; }

/* -------- charts (minimal) -------- */
function destroyChart(id) {
    if (_charts[id]) { _charts[id].destroy(); _charts[id] = null; }
}

function renderAvgPCB(d) {
    if (!d) return;
    const el = document.getElementById('avgPCBChart'); if (!el) return;
    destroyChart('avgPCBChart');
    _charts.avgPCBChart = new Chart(el.getContext('2d'), {
        type: 'bar',
        data: {
            labels: d.labels,
            datasets: [
                { label: 'Maternal (mPCB)', data: d.maternal, backgroundColor: 'rgba(46,125,150,0.85)' },
                { label: 'Fetal (cPCB)', data: d.fetal, backgroundColor: 'rgba(255,159,64,0.85)' }
            ]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });
}

function renderRiskDist(d) {
    if (!d) return;
    const el = document.getElementById('riskByPCBChart'); if (!el) return;
    destroyChart('riskByPCBChart');
    _charts.riskByPCBChart = new Chart(el.getContext('2d'), {
        type: 'bar',
        data: {
            labels: d.labels,
            datasets: [
                { label: 'Low', data: d.risk_low, backgroundColor: 'rgba(75,192,192,0.7)' },
                { label: 'Medium', data: d.risk_med, backgroundColor: 'rgba(255,205,86,0.8)' },
                { label: 'High', data: d.risk_high, backgroundColor: 'rgba(255,99,132,0.8)' }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true } }
        }
    });
}

function renderConcentrationSeries(d) {
    if (!d) return;
    const el = document.getElementById('concentrationDistChart'); if (!el) return;
    destroyChart('concentrationDistChart');
    _charts.concentrationDistChart = new Chart(el.getContext('2d'), {
        type: 'line',
        data: {
            labels: d.labels,
            datasets: [
                { label: 'Maternal', data: d.maternal_series, borderColor: 'rgb(54,162,235)', backgroundColor: 'rgb(54,162,235)', tension: 0.3, fill: false },
                { label: 'Fetal', data: d.fetal_series, borderColor: 'rgb(255,99,132)', backgroundColor: 'rgb(255,99,132)', tension: 0.3, fill: false }
            ]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });
}

function renderDemographics(d) {
    if (!d) return;

    // 2.1 by age
    (function () {
        const el = document.getElementById('pcbByAgeChart'); if (!el) return;
        destroyChart('pcbByAgeChart');
        _charts.pcbByAgeChart = new Chart(el.getContext('2d'), {
            type: 'bar',
            data: { labels: d.pcb_by_age.labels, datasets: [{ label: 'Avg PCB', data: d.pcb_by_age.values, backgroundColor: 'rgba(99,132,255,0.8)' }] },
            options: { responsive: true, maintainAspectRatio: false }
        });
    })();

    // 2.2 scatter total vs age
    (function () {
        const el = document.getElementById('pcbAgeScatterChart'); if (!el) return;
        destroyChart('pcbAgeScatterChart');
        _charts.pcbAgeScatterChart = new Chart(el.getContext('2d'), {
            type: 'scatter',
            data: { datasets: [{ label: 'Total PCB vs Age', data: d.scatter_total_vs_age, backgroundColor: 'rgba(75,192,192,0.9)' }] },
            options: { responsive: true, maintainAspectRatio: false }
        });
    })();

    // 2.3 by BMI
    (function () {
        const el = document.getElementById('pcbByBMIChart'); if (!el) return;
        destroyChart('pcbByBMIChart');
        _charts.pcbByBMIChart = new Chart(el.getContext('2d'), {
            type: 'bar',
            data: { labels: d.pcb_by_bmi.labels, datasets: [{ label: 'Avg PCB', data: d.pcb_by_bmi.values, backgroundColor: 'rgba(153,102,255,0.8)' }] },
            options: { responsive: true, maintainAspectRatio: false }
        });
    })();

    // 2.4 smokers vs non-smokers
    (function () {
        const el = document.getElementById('smokingComparisonChart'); if (!el) return;
        destroyChart('smokingComparisonChart');
        _charts.smokingComparisonChart = new Chart(el.getContext('2d'), {
            type: 'bar',
            data: { labels: d.smoking_comparison.labels, datasets: [{ label: 'Avg PCB', data: d.smoking_comparison.values, backgroundColor: ['#2d4b6e', '#ef6a51'] }] },
            options: { responsive: true, maintainAspectRatio: false }
        });
    })();

    // 2.5 correlation heatmap (bubble)
    (function () {
        const el = document.getElementById('correlationHeatmapChart'); if (!el) return;
        destroyChart('correlationHeatmapChart');
        // convert matrix to bubbles
        const labels = d.correlation_heatmap.labels;
        const mat = d.correlation_heatmap.matrix;
        const pts = [];
        for (let i = 0; i < mat.length; i++) {
            for (let j = 0; j < mat[i].length; j++) {
                const v = mat[i][j];
                pts.push({
                    x: j + 1, y: i + 1, r: Math.max(2, Math.abs(v) * 16),
                    backgroundColor: v >= 0 ? 'rgba(54,162,235,0.7)' : 'rgba(235,99,132,0.7)'
                });
            }
        }
        _charts.correlationHeatmapChart = new Chart(el.getContext('2d'), {
            type: 'bubble',
            data: { datasets: [{ data: pts }] },
            options: {
                responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } },
                scales: {
                    x: { min: 0.5, max: labels.length + 0.5, ticks: { stepSize: 1, callback: (v) => labels[Math.round(v) - 1] || '' } },
                    y: { min: 0.5, max: labels.length + 0.5, ticks: { stepSize: 1, callback: (v) => labels[Math.round(v) - 1] || '' } }
                }
            }
        });
    })();
}

function renderEnvironment(env) {
    if (!env) return;

    // 3.1 exposure contribution (bar for simplicity)
    (function () {
        const el = document.getElementById('radarChart'); if (!el) return;
        destroyChart('radarChart');
        _charts.radarChart = new Chart(el.getContext('2d'), {
            type: 'bar',
            data: { labels: env.exposure_contribution.labels, datasets: [{ label: 'Contribution', data: env.exposure_contribution.values, backgroundColor: 'rgba(46,125,150,0.25)', borderColor: 'rgba(46,125,150,0.9)' }] },
            options: { responsive: true, maintainAspectRatio: false }
        });
    })();

    // 3.2 dietary patterns
    (function () {
        const el = document.getElementById('dietaryPatternsChart'); if (!el) return;
        destroyChart('dietaryPatternsChart');
        _charts.dietaryPatternsChart = new Chart(el.getContext('2d'), {
            type: 'bar',
            data: { labels: env.dietary_patterns.labels, datasets: [{ label: 'Avg PCB', data: env.dietary_patterns.values, backgroundColor: 'rgba(255,159,64,0.8)' }] },
            options: { responsive: true, maintainAspectRatio: false }
        });
    })();

    // 3.3 lifestyle clusters
    (function () {
        const el = document.getElementById('clusterChart'); if (!el) return;
        destroyChart('clusterChart');
        _charts.clusterChart = new Chart(el.getContext('2d'), {
            type: 'scatter',
            data: { datasets: [{ label: 'Lifestyle clusters', data: env.lifestyle_clusters, backgroundColor: 'rgba(54,162,235,0.8)' }] },
            options: { responsive: true, maintainAspectRatio: false }
        });
    })();
}

function renderResearch(list) {
    const container = document.getElementById('researchList');
    if (!container) return;
    const ul = container.querySelector('ul') || container;
    ul.innerHTML = '';
    if (!list || !list.length) {
        const li = document.createElement('li');
        li.textContent = 'No research items found.';
        ul.appendChild(li);
        return;
    }
    list.forEach(it => {
        const li = document.createElement('li');
        const a = document.createElement('a');
        a.href = it.link || '#';
        a.target = '_blank';
        a.rel = 'noopener';
        a.textContent = `${it.title} (${it.year}) — ${it.authors}`;
        li.appendChild(a);
        ul.appendChild(li);
    });
}


// window.addEventListener("load", start, false);

// function start() {
//     // populate simple metrics (if present)
//     const totalPatientsEl = document.getElementById('totalPatients');
//     if (totalPatientsEl) totalPatientsEl.textContent = "1,234";

//     // initialize charts
//     initDashboardCharts();
// }

// // --- sample labels & data (kept simple) ---
// const timeLabels = ['9:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00'];
// const PCBsLabels = ['cPCB118', 'cPCB138', 'cPCB153', 'cPCB180', 'cPCB74', 'cPCB99', 'cPCB156', 'cPCB170', 'cPCB183', 'cPCB187'];
// const featureLabels = ['mPCB', 'Age', 'Gender', 'BMI', 'Smoking', 'Maternal Education', 'Chemical exposure', 'Tea', 'Coffee'];

// // maternal / fetal avg per PCB (length matches PCBsLabels)
// const maternalPCBs = [1.1, 1.3, 1.5, 1.0, 0.9, 1.0, 0.8, 0.7, 0.75, 0.55];
// const fetalPCBs = [0.9, 1.1, 1.3, 0.8, 0.6, 0.7, 0.5, 0.4, 0.45, 0.3];

// const sampleRiskLow = [30, 28, 26, 20, 18, 15, 12, 10, 9, 7];
// const sampleRiskMed = [20, 22, 24, 18, 15, 12, 10, 9, 8, 6];
// const sampleRiskHigh = [5, 6, 7, 9, 12, 14, 15, 13, 11, 9];

// const maternalSeries = [1.0, 1.05, 1.1, 1.07, 1.02, 0.98, 1.0];
// const fetalSeries = [0.8, 0.82, 0.85, 0.83, 0.81, 0.79, 0.8];

// const ageGroups = ['<25', '25-30', '31-35', '36-40', '41+'];
// const pcbByAge = [0.6, 1.0, 1.2, 1.05, 0.9];

// const bmiCats = ['Underweight', 'Normal', 'Overweight', 'Obese'];
// const pcbByBMI = [0.5, 1.0, 1.3, 1.6];

// const smokingData = [0.8, 1.3]; // non-smokers, smokers

// // correlation variables and matrix (sample)
// const corrVars = ['mPCB', 'Age', 'BMI', 'Smoking', 'Diet'];
// const corrMatrix = [
//     [1.0, 0.4, 0.2, -0.1, 0.3],
//     [0.4, 1.0, 0.1, -0.2, 0.15],
//     [0.2, 0.1, 1.0, 0.05, 0.25],
//     [-0.1, -0.2, 0.05, 1.0, -0.05],
//     [0.3, 0.15, 0.25, -0.05, 1.0]
// ];

// // helper to map index ticks to variable names
// function indexTickFormatter(labels) {
//     return function (value, index, ticks) {
//         const i = Math.round(value) - 1;
//         return labels[i] || '';
//     };
// }

// function initDashboardCharts() {
//     // 1.1 Average PCB Levels -> grouped bar (maternal vs fetal)
//     const avgEl = document.getElementById('avgPCBChart');
//     if (avgEl) {
//         new Chart(avgEl.getContext('2d'), {
//             type: 'bar',
//             data: {
//                 labels: PCBsLabels,
//                 datasets: [
//                     { label: 'Maternal (mPCB)', data: maternalPCBs, backgroundColor: 'rgba(46,125,150,0.85)' },
//                     { label: 'Fetal (cPCB)', data: fetalPCBs, backgroundColor: 'rgba(255,159,64,0.85)' }
//                 ]
//             },
//             options: {
//                 responsive: true,
//                 maintainAspectRatio: false,
//                 layout: { padding: { top: 10, bottom: 20 } },
//                 scales: { x: { stacked: false }, y: { beginAtZero: true } }
//             }
//         });
//     }

//     // 1.2 Risk Distribution by PCB (stacked)
//     const riskEl = document.getElementById('riskByPCBChart');
//     if (riskEl) {
//         new Chart(riskEl.getContext('2d'), {
//             type: 'bar',
//             data: {
//                 labels: PCBsLabels,
//                 datasets: [
//                     { label: 'Low', data: sampleRiskLow, backgroundColor: 'rgba(75,192,192,0.7)' },
//                     { label: 'Medium', data: sampleRiskMed, backgroundColor: 'rgba(255,205,86,0.8)' },
//                     { label: 'High', data: sampleRiskHigh, backgroundColor: 'rgba(255,99,132,0.8)' }
//                 ]
//             },
//             options: {
//                 responsive: true,
//                 maintainAspectRatio: false,
//                 layout: { padding: { top: 10, bottom: 20 } },
//                 scales: { x: { stacked: true }, y: { stacked: true } }
//             }
//         });
//     }

//     // 1.3 Maternal vs Fetal Concentration -> line
//     const concEl = document.getElementById('concentrationDistChart');
//     if (concEl) {
//         new Chart(concEl.getContext('2d'), {
//             type: 'line',
//             data: {
//                 labels: timeLabels,
//                 datasets: [
//                     { label: 'Maternal', data: maternalSeries, borderColor: 'rgb(54,162,235)', backgroundColor: 'rgb(54,162,235)', tension: 0.3, fill: false },
//                     { label: 'Fetal', data: fetalSeries, borderColor: 'rgb(255,99,132)', backgroundColor: 'rgb(255,99,132)', tension: 0.3, fill: false }
//                 ]
//             },
//             options: {
//                 responsive: true,
//                 maintainAspectRatio: false,
//                 layout: { padding: { top: 10, bottom: 40 } },
//             }
//         });
//     }

//     // 2.1 PCB by Age Group
//     const ageEl = document.getElementById('pcbByAgeChart');
//     if (ageEl) {
//         new Chart(ageEl.getContext('2d'), {
//             type: 'bar',
//             data: { labels: ageGroups, datasets: [{ label: 'Avg PCB', data: pcbByAge, backgroundColor: 'rgba(99,132,255,0.8)' }] },
//             options: {
//                 responsive: true,
//                 maintainAspectRatio: false,
//                 layout: { padding: { top: 10, bottom: 20 } },
//             }
//         });
//     }

//     // 2.2 PCB Total vs Maternal Age (scatter) - more points
//     const scatterEl = document.getElementById('pcbAgeScatterChart');
//     if (scatterEl) {
//         // synthetic sample: 40 points following a loose trend
//         const scatterData = [];
//         for (let i = 0; i < 40; i++) {
//             const age = 18 + Math.round(Math.random() * 27); // 18-45
//             // create a loose positive trend + noise
//             const value = 0.4 + (age - 18) * 0.02 + (Math.random() - 0.5) * 0.4;
//             scatterData.push({ x: age, y: Math.max(0, Number(value.toFixed(2))) });
//         }
//         new Chart(scatterEl.getContext('2d'), {
//             type: 'scatter',
//             data: { datasets: [{ label: 'Total PCB vs Age', data: scatterData, backgroundColor: 'rgba(75,192,192,0.9)' }] },
//             options: {
//                 responsive: true,
//                 maintainAspectRatio: false,
//                 layout: { padding: { top: 10, bottom: 20 } },
//                 scales: {
//                     x: { title: { display: true, text: 'Maternal age' }, min: 16, max: 50 },
//                     y: { title: { display: true, text: 'Total PCB' } }
//                 }
//             }
//         });
//     }

//     // 2.3 PCB by BMI
//     const bmiEl = document.getElementById('pcbByBMIChart');
//     if (bmiEl) {
//         new Chart(bmiEl.getContext('2d'), {
//             type: 'bar',
//             data: { labels: bmiCats, datasets: [{ label: 'Avg PCB', data: pcbByBMI, backgroundColor: 'rgba(153,102,255,0.8)' }] },
//             options: {
//                 responsive: true,
//                 maintainAspectRatio: false,
//                 layout: { padding: { top: 10, bottom: 20 } },
//             }
//         });
//     }

//     // 2.4 Smokers vs Non-Smokers
//     const smokeEl = document.getElementById('smokingComparisonChart');
//     if (smokeEl) {
//         new Chart(smokeEl.getContext('2d'), {
//             type: 'bar',
//             data: { labels: ['Non-smokers', 'Smokers'], datasets: [{ label: 'Avg PCB', data: smokingData, backgroundColor: ['#2d4b6e', '#ef6a51'] }] },
//             options: {
//                 responsive: true,
//                 maintainAspectRatio: false,
//                 layout: { padding: { top: 10, bottom: 20 } },
//             }
//         });
//     }

//     // 2.5 Variable Correlation Heatmap (approx using bubble + indexed axis labels)
//     const corrElCanvas = document.getElementById('correlationHeatmapChart');
//     if (corrElCanvas) {
//         const heatData = [];
//         for (let i = 0; i < corrMatrix.length; i++) {
//             for (let j = 0; j < corrMatrix[i].length; j++) {
//                 const v = corrMatrix[i][j];
//                 heatData.push({
//                     x: j + 1, // column index (1-based)
//                     y: i + 1, // row index (1-based)
//                     r: Math.abs(v) * 16,
//                     backgroundColor: v >= 0 ? 'rgba(54,162,235,0.7)' : 'rgba(235,92,92,0.7)'
//                 });
//             }
//         }

//         new Chart(corrElCanvas.getContext('2d'), {
//             type: 'bubble',
//             data: { datasets: [{ label: 'Corr (abs=size, color=sign)', data: heatData }] },
//             options: {
//                 responsive: true,
//                 maintainAspectRatio: false,
//                 plugins: { legend: { display: false } },
//                 scales: {
//                     x: {
//                         min: 0.5,
//                         max: corrVars.length + 0.5,
//                         ticks: {
//                             stepSize: 1,
//                             callback: indexTickFormatter(corrVars)
//                         }
//                     },
//                     y: {
//                         min: 0.5,
//                         max: corrVars.length + 0.5,
//                         ticks: {
//                             stepSize: 1,
//                             callback: indexTickFormatter(corrVars)
//                         }
//                     }
//                 }
//             }
//         });
//     }

//     // 3.1 Radar
//     const radarEl = document.getElementById('radarChart');
//     if (radarEl) {
//         new Chart(radarEl.getContext('2d'), {
//             type: 'radar',
//             data: { labels: featureLabels, datasets: [{ label: 'Contribution', data: [0.8, 0.6, 0.2, 0.4, 0.5, 0.3, 0.2, 0.15, 0.1], backgroundColor: 'rgba(46,125,150,0.25)', borderColor: 'rgba(46,125,150,0.9)' }] },
//             options: {
//                 responsive: true,
//                 maintainAspectRatio: false,
//                 layout: { padding: { top: 10, bottom: 20 } },
//             }
//         });
//     }

//     // 3.2 Dietary Patterns
//     const dietEl = document.getElementById('dietaryPatternsChart');
//     if (dietEl) {
//         new Chart(dietEl.getContext('2d'), {
//             type: 'bar',
//             data: { labels: ['Low dairy', 'Medium dairy', 'High dairy'], datasets: [{ label: 'Avg PCB', data: [0.7, 1.0, 1.4], backgroundColor: 'rgba(255,159,64,0.8)' }] },
//             options: {
//                 responsive: true,
//                 maintainAspectRatio: false,
//                 layout: { padding: { top: 10, bottom: 20 } },
//             }
//         });
//     }

//     // 3.3 Lifestyle clusters
//     const clusterEl = document.getElementById('clusterChart');
//     if (clusterEl) {
//         const clusterData = [{ x: 20, y: 0.6 }, { x: 25, y: 0.9 }, { x: 30, y: 1.2 }, { x: 35, y: 1.05 }, { x: 40, y: 1.3 }, { x: 28, y: 0.8 }, { x: 32, y: 1.1 }];
//         new Chart(clusterEl.getContext('2d'), {
//             type: 'scatter',
//             data: { datasets: [{ label: 'Lifestyle clusters', data: clusterData, backgroundColor: 'rgba(54,162,235,0.8)' }] },
//             options: {
//                 responsive: true,
//                 maintainAspectRatio: false,
//                 layout: { padding: { top: 10, bottom: 20 } },
//             }
//         });
//     }
// }