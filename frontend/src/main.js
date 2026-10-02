import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import "./style.css";

gsap.registerPlugin(ScrollTrigger);

// ===================================================================
// 1. Apple-Style Button Physics & Press Animations
//    (Respond on pointerdown, instant tactile feedback, spring release)
// ===================================================================
function initButtonPhysics() {
  const buttons = document.querySelectorAll(".btn, .segment-btn, .bench-tab, .showcase-tab, .btn-console-run, .btn-console-reset, .btn-copy, .btn-terminal-copy");

  buttons.forEach((btn) => {
    btn.addEventListener("pointerdown", () => {
      gsap.to(btn, {
        scale: 0.96,
        duration: 0.08,
        ease: "power2.out",
        overwrite: "auto",
      });
    });

    const release = () => {
      gsap.to(btn, {
        scale: 1,
        duration: 0.25,
        ease: "back.out(2)",
        overwrite: "auto",
      });
    };

    btn.addEventListener("pointerup", release);
    btn.addEventListener("pointerleave", release);
    btn.addEventListener("pointercancel", release);
  });
}

// ===================================================================
// 2. Smooth Hero & Section Entrance Animations
// ===================================================================
function initHeroAnimations() {
  // Use opacity-only (no y/transform) for elements without will-change pre-promotion
  // This runs entirely on the compositor thread — zero layout cost
  const tl = gsap.timeline({
    defaults: { ease: "power2.out" },
    delay: 0.15, // Let FOUC body fade-in complete first
  });

  tl.from(".hero-kicker-badge", { opacity: 0, duration: 0.4 })
    .from(".hero-headline", { opacity: 0, y: 12, duration: 0.5 }, "-=0.2")
    .from(".hero-paragraph", { opacity: 0, y: 10, duration: 0.45 }, "-=0.25")
    .from(".hero-actions", { opacity: 0, y: 8, duration: 0.4 }, "-=0.2")
    .from(".telemetry-strip", { opacity: 0, duration: 0.4 }, "-=0.15");

  // Animate Telemetry numbers counting up
  const telemetryItems = document.querySelectorAll(".telemetry-figure");
  telemetryItems.forEach((item) => {
    const rawVal = item.getAttribute("data-val");
    if (!rawVal) return;
    const target = parseFloat(rawVal);
    const hasPercent = item.innerText.includes("%");
    const hasX = item.innerText.includes("×");

    const counter = { val: 0 };
    gsap.to(counter, {
      val: target,
      duration: 1.0,
      ease: "power2.out",
      delay: 0.5,
      onUpdate: () => {
        let formatted = Math.round(counter.val);
        if (hasPercent) formatted += "%";
        else if (hasX) formatted += "×";
        item.innerText = formatted;
      },
    });
  });



  // ScrollTrigger.batch() � smooth grouped stagger on scroll.
  // Key fixes vs previous version:
  // 1. Use gsap.from (not fromTo) so GSAP auto-manages FROM state and cleans up cleanly
  // 2. Remove clearProps entirely � it was de-promoting the GPU compositor layer
  //    causing the tiny upward snap/jump after animation completion.
  // 3. Disable CSS transitions on cards during animation to prevent hover:translateY(-2px)
  //    from interfering, then restore after.
  ScrollTrigger.batch(
    ".pillar-card, .calc-panel, .bench-card, .showcase-window-frame, .terminal-card",
    {
      start: "top 92%",
      once: true,
      onEnter: (batch) => {
        // Temporarily suppress CSS transitions so they cannot fire mid-animation
        gsap.set(batch, { transition: "none" });
        gsap.from(batch, {
          opacity: 0,
          y: 18,
          duration: 0.65,
          ease: "power4.out",
          stagger: 0.1,
          onComplete() {
            // Restore CSS transitions AFTER the animation fully settles
            gsap.set(batch, { clearProps: "transition" });
          },
        });
      },
    }
  );
}

// ===================================================================
// 3. Interactive CPU Scheduler Simulator
// ===================================================================
let activeSimMode = "starveguard";
let isRunningSim = false;

const simTrack = document.getElementById("gantt-track");
const simStatus = document.getElementById("gantt-status-pill");
const simModeLabel = document.getElementById("gantt-mode-label");

const p1WaitingEl = document.getElementById("val-p1-waiting");
const starvationEl = document.getElementById("val-starvation");
const agingEl = document.getElementById("val-aging");
const fairnessEl = document.getElementById("val-fairness");
const verdictTextEl = document.getElementById("verdict-text");
const verdictDotEl = document.getElementById("verdict-dot");

const simDatasets = {
  starveguard: {
    title: "StarveGuard Adaptive Scheduling Timeline",
    slices: [
      { pid: "P2", start: 0, end: 5, duration: 5, colorClass: "slice-p2" },
      { pid: "P3", start: 5, end: 10, duration: 5, colorClass: "slice-p3" },
      { pid: "P1 (Aged)", start: 10, end: 14, duration: 4, colorClass: "slice-p1" },
      { pid: "P4", start: 14, end: 19, duration: 5, colorClass: "slice-p4" },
      { pid: "P1", start: 19, end: 30, duration: 11, colorClass: "slice-p1" },
    ],
    results: {
      p1Waiting: "10 ticks",
      starvation: "Detected & Resolved",
      starvationClass: "state-good",
      aging: "4 Adjustments",
      agingClass: "state-good",
      fairness: "0.912",
      verdict: `<strong>StarveGuard Success:</strong> Low-priority thread P1 reached starvation threshold θ = 20 at T=10. The aging engine promoted P1 to Priority 3, allowing it to interleave 4 CPU ticks before yielding to P4. <strong>Starvation completely eliminated.</strong>`,
      dotClass: "state-active",
    },
  },
  normal: {
    title: "Standard Preemptive Priority Scheduling Timeline",
    slices: [
      { pid: "P2", start: 0, end: 5, duration: 5, colorClass: "slice-p2" },
      { pid: "P3", start: 5, end: 10, duration: 5, colorClass: "slice-p3" },
      { pid: "P4", start: 10, end: 15, duration: 5, colorClass: "slice-p4" },
      { pid: "P1", start: 15, end: 30, duration: 15, colorClass: "slice-p1" },
    ],
    results: {
      p1Waiting: "15 ticks",
      starvation: "Unmitigated",
      starvationClass: "state-bad",
      aging: "0 (Disabled)",
      agingClass: "",
      fairness: "0.942",
      verdict: `<strong>Starvation Failure:</strong> Standard preemptive priority forced low-priority thread P1 to wait 15 consecutive ticks while P2, P3, and P4 ran. P1 received zero CPU time until all higher-priority threads fully completed.`,
      dotClass: "state-warning",
    },
  },
};

function resetSimulator() {
  if (isRunningSim || !simTrack) return;
  simTrack.innerHTML = "";
  simStatus.textContent = "Ready";
  simStatus.className = "gantt-status-pill";

  p1WaitingEl.textContent = "-";
  starvationEl.textContent = "-";
  starvationEl.className = "data-card-value";
  agingEl.textContent = "-";
  agingEl.className = "data-card-value";
  fairnessEl.textContent = "-";

  verdictTextEl.innerHTML = "Select an algorithm and press <strong>Run Simulation</strong> to observe CPU time-slice distribution.";
  verdictDotEl.className = "verdict-indicator";
}

function runSimulator() {
  if (isRunningSim || !simTrack) return;
  isRunningSim = true;

  simTrack.innerHTML = "";
  simStatus.textContent = "Arbitrating Quantum...";
  simStatus.className = "gantt-status-pill running";

  const config = simDatasets[activeSimMode];
  const totalTicks = 30;

  const tl = gsap.timeline({
    onComplete: () => {
      isRunningSim = false;
      simStatus.textContent = "Execution Complete";
      simStatus.className = "gantt-status-pill done";

      p1WaitingEl.textContent = config.results.p1Waiting;
      starvationEl.textContent = config.results.starvation;
      starvationEl.className = `data-card-value ${config.results.starvationClass}`;

      agingEl.textContent = config.results.aging;
      agingEl.className = `data-card-value ${config.results.agingClass}`;

      fairnessEl.textContent = config.results.fairness;
      verdictTextEl.innerHTML = config.results.verdict;
      verdictDotEl.className = `verdict-indicator ${config.results.dotClass}`;
    },
  });

  config.slices.forEach((slice) => {
    const el = document.createElement("div");
    el.className = `gantt-slice ${slice.colorClass}`;
    el.textContent = `${slice.pid} [${slice.start}\u2013${slice.end}]`;
    const targetWidth = (slice.duration / totalTicks) * 100;
    // Use width directly — set it via scaleX transform for GPU compositing
    el.style.width = `${targetWidth}%`;
    el.style.transformOrigin = 'left center';
    el.style.transform = 'scaleX(0)';
    simTrack.appendChild(el);

    tl.to(el, {
      scaleX: 1,
      duration: 0.32,
      ease: "power2.out",
    });
  });
}

function initSimulator() {
  const btnStarve = document.getElementById("mode-starveguard");
  const btnNormal = document.getElementById("mode-normal");
  const btnRun = document.getElementById("btn-run-sim");
  const btnReset = document.getElementById("btn-reset-sim");

  if (btnStarve && btnNormal) {
    btnStarve.addEventListener("click", () => {
      if (isRunningSim) return;
      activeSimMode = "starveguard";
      btnStarve.classList.add("active");
      btnNormal.classList.remove("active");
      simModeLabel.textContent = simDatasets.starveguard.title;
      resetSimulator();
    });

    btnNormal.addEventListener("click", () => {
      if (isRunningSim) return;
      activeSimMode = "normal";
      btnNormal.classList.add("active");
      btnStarve.classList.remove("active");
      simModeLabel.textContent = simDatasets.normal.title;
      resetSimulator();
    });
  }

  if (btnRun) btnRun.addEventListener("click", runSimulator);
  if (btnReset) btnReset.addEventListener("click", resetSimulator);

  resetSimulator();
}

// ===================================================================
// 4. Interactive Starvation Score Calculator
// ===================================================================
function initCalculator() {
  const sliderW = document.getElementById("slider-waiting");
  const sliderB = document.getElementById("slider-bypass");
  const sliderA = document.getElementById("slider-alpha");

  const dispW = document.getElementById("val-waiting-display");
  const dispB = document.getElementById("val-bypass-display");
  const dispA = document.getElementById("val-alpha-display");

  const scoreEl = document.getElementById("calc-score-display");
  const progressFill = document.getElementById("calc-progress-fill");
  const badgeEl = document.getElementById("calc-status-badge");
  const descEl = document.getElementById("calc-status-desc");
  const markerEl = document.getElementById("calc-threshold-marker");

  if (!sliderW || !sliderB || !sliderA || !scoreEl) return;

  function updateScore() {
    const W = parseFloat(sliderW.value);
    const B = parseFloat(sliderB.value);
    const A = parseFloat(sliderA.value);

    dispW.textContent = `${W} ticks`;
    dispB.textContent = `${B} times`;
    dispA.textContent = `${A.toFixed(1)}×`;

    const score = W + (B * A);
    scoreEl.textContent = score.toFixed(1);

    // Max visual scale = 30
    const pct = Math.min((score / 30) * 100, 100);
    progressFill.style.width = `${pct}%`;

    if (score >= 20.0) {
      badgeEl.textContent = "AGING INTERVENTION TRIGGERED";
      badgeEl.className = "calc-status-badge status-danger";
      progressFill.className = "calc-progress-fill status-danger";
      if (markerEl) markerEl.classList.add("active");
      descEl.textContent = "Score is ≥ 20. StarveGuard elevates process priority to grant immediate CPU scheduling.";
    } else {
      badgeEl.textContent = "NORMAL SCHEDULING QUEUE";
      badgeEl.className = "calc-status-badge status-safe";
      progressFill.className = "calc-progress-fill status-safe";
      if (markerEl) markerEl.classList.remove("active");
      descEl.textContent = "Score is < 20. Process remains in ready queue awaiting normal preemptive turn.";
    }
  }

  sliderW.addEventListener("input", updateScore);
  sliderB.addEventListener("input", updateScore);
  sliderA.addEventListener("input", updateScore);

  updateScore();
}

// ===================================================================
// 5. Empirical Benchmarks — GSAP Animated Interactive Chart
// ===================================================================
const benchmarkMetrics = {
  waiting: {
    title: "Average Waiting Time Comparison",
    sub: "Lower waiting duration indicates faster queue throughput (clock ticks)",
    category: "Latency Metric",
    headline: "Average Waiting Time Analysis",
    body: "In Workload 1, low-priority tasks receive early execution slices under StarveGuard. While average waiting time increases modestly by +1.33 ticks, maximum waiting drops dramatically, completely preventing thread starvation.",
    yTicks: ["25", "20", "15", "10", "5", "0"],
    unit: "ticks",
    maxScale: 25.0,
    workloads: [
      { normal: 15.0, starveguard: 16.33 },
      { normal: 6.25, starveguard: 6.25 },
      { normal: 23.33, starveguard: 24.67 },
      { normal: 0.0, starveguard: 0.0 },
    ],
    rows: [
      { normal: "15.00", sg: "16.33", delta: "+1.33 · Immune", type: "neutral" },
      { normal: "6.25", sg: "6.25", delta: "0.00 · Par", type: "neutral" },
      { normal: "23.33", sg: "24.67", delta: "+1.34 · Immune", type: "neutral" },
    ],
  },
  response: {
    title: "Average Response Time Comparison",
    sub: "Time elapsed from thread arrival to initial CPU execution tick",
    category: "Dispatch Metric",
    headline: "Initial Response Latency Gain",
    body: "StarveGuard significantly improves initial CPU allocation latency for preempted low-priority tasks. In Workload 1, response latency drops from 15.00 ticks down to 11.67 ticks (-3.33 ticks faster) because P1 touches the CPU at T=10.",
    yTicks: ["25", "20", "15", "10", "5", "0"],
    unit: "ticks",
    maxScale: 25.0,
    workloads: [
      { normal: 15.0, starveguard: 11.67 },
      { normal: 5.25, starveguard: 5.25 },
      { normal: 23.33, starveguard: 16.67 },
      { normal: 0.0, starveguard: 0.0 },
    ],
    rows: [
      { normal: "15.00", sg: "11.67", delta: "-3.33 · 22% Faster", type: "positive" },
      { normal: "5.25", sg: "5.25", delta: "0.00 · Par", type: "neutral" },
      { normal: "23.33", sg: "16.67", delta: "-6.66 · 28% Faster", type: "positive" },
    ],
  },
  fairness: {
    title: "Jain's Fairness Index Comparison",
    sub: "Normalized score from 0.0 to 1.0 (1.0 = absolute scheduling equity)",
    category: "Throughput Distribution",
    headline: "System Fairness & Equity Uplift",
    body: "Jain's Index quantifies scheduling equity across all active processes. StarveGuard elevates fairness in Workload 1 from 0.583 up to 0.630 (+8.0% equity gain), and in Workload 3 from 0.636 to 0.672 without sacrificing system throughput.",
    yTicks: ["1.0", "0.8", "0.6", "0.4", "0.2", "0.0"],
    unit: "score",
    maxScale: 1.0,
    workloads: [
      { normal: 0.583, starveguard: 0.630 },
      { normal: 0.765, starveguard: 0.765 },
      { normal: 0.636, starveguard: 0.672 },
      { normal: 1.000, starveguard: 1.000 },
    ],
    rows: [
      { normal: "0.583", sg: "0.630", delta: "+8.0% · Equity", type: "positive" },
      { normal: "0.765", sg: "0.765", delta: "0.765 · Balanced", type: "neutral" },
      { normal: "0.636", sg: "0.672", delta: "+5.7% · Equity", type: "positive" },
    ],
  },
};

let currentMetric = "waiting";
const liveChartState = [
  { normal: 15.0, sg: 16.33 },
  { normal: 6.25, sg: 6.25 },
  { normal: 23.33, sg: 24.67 },
  { normal: 0.0, sg: 0.0 },
];

function animateBenchmarkChart(metricKey) {
  const metric = benchmarkMetrics[metricKey];
  if (!metric) return;
  currentMetric = metricKey;
  const isFairness = metricKey === "fairness";

  // 1. Update Titles & Subtitles with smooth fade
  const titleEl = document.getElementById("chart-dynamic-title");
  const subEl = document.getElementById("chart-dynamic-sub");
  if (titleEl && subEl) {
    gsap.to([titleEl, subEl], {
      opacity: 0,
      duration: 0.12,
      onComplete: () => {
        titleEl.textContent = metric.title;
        subEl.textContent = metric.sub;
        gsap.to([titleEl, subEl], { opacity: 1, duration: 0.2 });
      },
    });
  }

  // 2. Update Y-Axis Scale
  const yAxisEl = document.getElementById("chart-y-axis");
  if (yAxisEl) {
    gsap.to(yAxisEl, {
      opacity: 0,
      duration: 0.12,
      onComplete: () => {
        yAxisEl.innerHTML = metric.yTicks.map((t) => `<span>${t}</span>`).join("");
        gsap.to(yAxisEl, { opacity: 1, duration: 0.2 });
      },
    });
  }

  // 3. Smoothly Animate Bars & Labels (Fluid Apple Motion & Counting Numbers)
  metric.workloads.forEach((w, i) => {
    const barNormal = document.getElementById(`bar-normal-${i}`);
    const barSg = document.getElementById(`bar-sg-${i}`);
    const valNormal = document.getElementById(`val-normal-${i}`);
    const valSg = document.getElementById(`val-sg-${i}`);

    const targetHNormal = Math.max((w.normal / metric.maxScale) * 100, 3);
    const targetHSg = Math.max((w.starveguard / metric.maxScale) * 100, 3);

    // Spring animation for bar heights
    if (barNormal) {
      gsap.to(barNormal, {
        height: `${targetHNormal}%`,
        duration: 0.65,
        ease: "power3.out",
        delay: i * 0.04,
      });
      barNormal.title = `Normal Priority: ${isFairness ? w.normal.toFixed(2) : w.normal.toFixed(1)} ${metric.unit}`;
    }

    if (barSg) {
      gsap.to(barSg, {
        height: `${targetHSg}%`,
        duration: 0.65,
        ease: "power3.out",
        delay: i * 0.04 + 0.02,
      });
      barSg.title = `StarveGuard: ${isFairness ? w.starveguard.toFixed(2) : w.starveguard.toFixed(1)} ${metric.unit}`;
    }

    // Number count-up animation
    gsap.to(liveChartState[i], {
      normal: w.normal,
      sg: w.starveguard,
      duration: 0.6,
      ease: "power2.out",
      delay: i * 0.04,
      onUpdate: () => {
        if (valNormal) valNormal.textContent = isFairness ? liveChartState[i].normal.toFixed(2) : liveChartState[i].normal.toFixed(1);
        if (valSg) valSg.textContent = isFairness ? liveChartState[i].sg.toFixed(2) : liveChartState[i].sg.toFixed(1);
      },
    });
  });

  // 4. Update Right-side Narrative & Comparison Matrix Table
  const catEl = document.getElementById("bench-category");
  const headEl = document.getElementById("bench-headline");
  const bodyEl = document.getElementById("bench-body");
  const matrixCard = document.querySelector(".bench-matrix-card");

  const narrativeEls = [catEl, headEl, bodyEl, matrixCard].filter(Boolean);
  gsap.to(narrativeEls, {
    opacity: 0,
    duration: 0.12,
    onComplete: () => {
      if (catEl) catEl.textContent = metric.category;
      if (headEl) headEl.textContent = metric.headline;
      if (bodyEl) bodyEl.textContent = metric.body;

      if (metric.rows) {
        metric.rows.forEach((r, idx) => {
          const normEl = document.getElementById(`row-val-normal-${idx}`);
          const sgEl = document.getElementById(`row-val-sg-${idx}`);
          const deltaEl = document.getElementById(`row-delta-${idx}`);
          if (normEl) normEl.textContent = r.normal;
          if (sgEl) sgEl.textContent = r.sg;
          if (deltaEl) {
            deltaEl.innerHTML = `<span class="delta-tag ${r.type}">${r.delta}</span>`;
          }
        });
      }

      gsap.to(narrativeEls, { opacity: 1, duration: 0.2 });
    },
  });
}

function initBenchmarks() {
  const tabs = document.querySelectorAll(".bench-tab");

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");

      const key = tab.getAttribute("data-chart");
      animateBenchmarkChart(key);
    });
  });

  // Initial render of Waiting Time chart
  animateBenchmarkChart("waiting");
}

// ===================================================================
// 6. Application Showcase Segmented Controller
// ===================================================================
function initShowcase() {
  const tabs = document.querySelectorAll(".showcase-tab");
  const imgEl = document.getElementById("showcase-active-img");
  const capEl = document.getElementById("showcase-caption");

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");

      const newSrc = tab.getAttribute("data-img");
      const newDesc = tab.getAttribute("data-desc");
      if (!newSrc || !imgEl) return;

      gsap.to(imgEl, {
        opacity: 0,
        duration: 0.15,
        ease: "power2.out",
        onComplete: () => {
          imgEl.src = newSrc;
          capEl.textContent = newDesc;
          gsap.to(imgEl, { opacity: 1, duration: 0.25, ease: "power2.out" });
        },
      });
    });
  });
}

// ===================================================================
// 7. Quickstart Copy Button
// ===================================================================
function initCopy() {
  const copyBtn = document.getElementById("btn-copy");
  if (!copyBtn) return;

  const rawCommands = `# 1. Clone repository and navigate to root
git clone https://github.com/ujvall/StarveGuard.git
cd StarveGuard

# 2. Execute comparative simulation CLI
python main.py

# 3. Launch visual Tkinter desktop application
python -m ui.app`;

  copyBtn.addEventListener("click", () => {
    navigator.clipboard.writeText(rawCommands).then(() => {
      copyBtn.innerHTML = `
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
        <span style="color: #FFFFFF; font-weight: 600;">Copied!</span>
      `;
      setTimeout(() => {
        copyBtn.innerHTML = `
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
          </svg>
          <span id="copy-label">Copy Commands</span>
        `;
      }, 2000);
    });
  });
}

// ===================================================================
// Mount Lifecycle
// ===================================================================
window.addEventListener("DOMContentLoaded", () => {
  initButtonPhysics();
  initHeroAnimations();
  initSimulator();
  initCalculator();
  initBenchmarks();
  initShowcase();
  initCopy();
});
