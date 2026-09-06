import { driver, type DriveStep, type Popover } from "driver.js";
import "driver.js/dist/driver.css";
import "./tour.css";
import type { Panel } from "../../types";

const SEEN_KEY = "tourSeen";

export function hasSeenTour(): boolean {
  try {
    return localStorage.getItem(SEEN_KEY) === "1";
  } catch {
    return false;
  }
}

function markSeen() {
  try {
    localStorage.setItem(SEEN_KEY, "1");
  } catch {
    /* private mode — the tour just runs again next time */
  }
}

// After a panel switch React needs a frame or two to mount the target element.
function waitFor(selector: string | undefined, timeout = 1500): Promise<void> {
  return new Promise((resolve) => {
    if (!selector || document.querySelector(selector)) return resolve();
    const started = Date.now();
    const tick = () => {
      if (document.querySelector(selector) || Date.now() - started > timeout) resolve();
      else requestAnimationFrame(tick);
    };
    tick();
  });
}

interface TourStep {
  panel?: Panel;
  element?: string;
  popover: Popover;
}

const STEPS: TourStep[] = [
  {
    popover: {
      title: "Knowledge-Map RAG",
      description:
        "This app answers questions from a knowledge graph it builds from your sources — and shows every step. Quick tour of the panels on the left?",
    },
  },
  {
    panel: "sources",
    element: '[data-tour="nav-sources"]',
    popover: {
      title: "1 · Add knowledge",
      description:
        "Drop in PDF / DOCX / TXT / MD files, or import an article by URL. Each source runs through a 5-stage pipeline that extracts entities, claims, and edges.",
      side: "right",
    },
  },
  {
    panel: "chat_trace",
    element: '[data-tour="chat-input"]',
    popover: {
      title: "2 · Ask a question",
      description:
        'Specific, factual questions work best — "How does A differ from B?", not "tell me everything".',
      side: "bottom",
      align: "center",
    },
  },
  {
    panel: "chat_trace",
    element: '[data-tour="pipeline"]',
    popover: {
      title: "3 · Watch it think",
      description:
        "The retrieval pipeline runs left to right: intent → candidates → selection → context → answer. Each station lights up as it runs. This is the whole point of the app.",
      side: "bottom",
      align: "start",
    },
  },
  {
    panel: "knowledge_map",
    element: '[data-tour="nav-knowledge_map"]',
    popover: {
      title: "4 · The graph",
      description:
        "Every answer is built from claims in this graph. Click any node to see its claims and where they came from.",
      side: "right",
    },
  },
  {
    panel: "lint",
    element: '[data-tour="nav-lint"]',
    popover: {
      title: "5 · Keep it healthy",
      description:
        "Lint checks the wiki for missing provenance, contradictions, orphan nodes, and stale summaries. Run it every few ingests.",
      side: "right",
    },
  },
  {
    panel: "tutorial",
    element: '[data-tour="nav-tutorial"]',
    popover: {
      title: "Go deeper",
      description:
        "The Tutorial explains why naive RAG falls short and how each stage works, with guided walkthroughs. That's the tour — enjoy.",
      side: "right",
    },
  },
];

export function startTour(setPanel: (p: Panel) => void) {
  const steps: DriveStep[] = STEPS.map((s) => ({
    element: s.element,
    popover: s.popover,
  }));

  // Switch to the target step's panel, wait for its element, then move. moveNext /
  // movePrevious must run outside driver's own click handler, hence the timeout.
  const step = (index: number, move: () => void) => async () => {
    const target = STEPS[index];
    if (target?.panel) setPanel(target.panel);
    await waitFor(target?.element);
    setTimeout(move, 40);
  };

  const d = driver({
    showProgress: true,
    overlayColor: "#0b0c0e",
    overlayOpacity: 0.9,
    stagePadding: 6,
    nextBtnText: "Next",
    prevBtnText: "Back",
    doneBtnText: "Done",
    progressText: "{{current}} / {{total}}",
    onDestroyed: markSeen,
    onNextClick: () => {
      const i = d.getActiveIndex() ?? 0;
      if (i >= STEPS.length - 1) d.destroy();
      else step(i + 1, () => d.moveNext())();
    },
    onPrevClick: () => {
      const i = d.getActiveIndex() ?? 0;
      if (i > 0) step(i - 1, () => d.movePrevious())();
    },
    steps,
  });
  d.drive();
}
